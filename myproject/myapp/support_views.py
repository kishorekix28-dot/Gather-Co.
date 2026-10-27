import json
import logging
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import DatabaseError, connections
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from pymongo.errors import PyMongoError

from .models import Category, ErrorCode, FAQ, Product, SupportTicket
from .mongo_store import get_mongo_database, save_chat_log, save_feedback


logger = logging.getLogger(__name__)
STOP_WORDS = {
    'a', 'about', 'all', 'am', 'an', 'and', 'are', 'can', 'do', 'for', 'gather',
    'have', 'how', 'i', 'in', 'is', 'it', 'me', 'my', 'of', 'on', 'or', 'our',
    'please', 'site', 'the', 'there', 'this', 'to', 'website', 'what', 'when',
    'where', 'which', 'with', 'you', 'your',
}
TERM_GROUPS = (
    frozenset({'reserve', 'reservation', 'reservations', 'booking', 'bookings', 'book', 'rent', 'rental', 'rentals'}),
    frozenset({'item', 'items', 'product', 'products', 'inventory', 'equipment', 'catalog', 'catalogue'}),
    frozenset({'cancel', 'cancellation', 'canceled', 'cancelled'}),
    frozenset({'pay', 'payment', 'payments', 'charge', 'charges', 'price', 'prices', 'cost', 'costs'}),
    frozenset({'account', 'accounts', 'signup', 'register', 'registration', 'login', 'signin', 'sign'}),
    frozenset({'owner', 'owners', 'list', 'listing', 'listings', 'add', 'upload'}),
    frozenset({'status', 'track', 'tracking', 'dashboard', 'confirmed', 'confirmation'}),
    frozenset({'available', 'availability', 'stock', 'unavailable'}),
)


def faq_page(request):
    return render(request, 'myapp/faqs.html', {'faqs': FAQ.objects.filter(is_active=True)})


def error_codes_page(request):
    return render(
        request,
        'myapp/error_codes.html',
        {'error_codes': ErrorCode.objects.filter(is_active=True)},
    )


@login_required
@require_GET
def tickets_page(request):
    tickets = SupportTicket.objects.filter(user=request.user)
    return render(request, 'myapp/tickets.html', {'tickets': tickets})


@require_GET
def health_page(request):
    checks = {'sql': 'ok', 'mongodb': 'not configured' if not settings.MONGODB_URI else 'unavailable'}
    status_code = 200
    try:
        connections['default'].ensure_connection()
    except DatabaseError:
        logger.exception('Health check could not connect to SQL database.')
        checks['sql'] = 'unavailable'
        status_code = 503

    if settings.MONGODB_URI:
        try:
            get_mongo_database().command('ping')
            checks['mongodb'] = 'ok'
        except (PyMongoError, RuntimeError):
            logger.exception('Health check could not connect to MongoDB.')
            checks['mongodb'] = 'unavailable'

    return render(request, 'myapp/health.html', {'checks': checks}, status=status_code)


def _error_code_answer(message):
    for error in ErrorCode.objects.filter(is_active=True):
        if error.code.isdigit():
            if re.search(rf'\b{re.escape(error.code)}\b', message):
                return error
        elif error.code.lower() in message.lower():
            return error
    return None


def _normalized_terms(text):
    terms = {
        word for word in re.findall(r'[a-z0-9]+', text.lower())
        if len(word) > 1 and word not in STOP_WORDS
    }
    return {
        next((group for group in TERM_GROUPS if word in group), word)
        for word in terms
    }


def _inventory_answer(message):
    raw_terms = set(re.findall(r'[a-z0-9]+', message.lower()))
    inventory_terms = TERM_GROUPS[1]
    request_terms = {'what', 'which', 'show', 'list', 'offer', 'available', 'have'}
    if not raw_terms.intersection(inventory_terms):
        return None
    if not raw_terms.intersection(request_terms) and not raw_terms.intersection({'all', 'catalog', 'catalogue'}):
        return None

    products = Product.objects.filter(is_active=True).select_related('category')
    categories = {
        category.name.lower(): category.name
        for category in Category.objects.filter(products__is_active=True).distinct()
    }
    requested_category = next(
        (name for normalized, name in categories.items() if normalized in message.lower()),
        None,
    )
    if requested_category:
        products = products.filter(category__name=requested_category)

    if not products.exists():
        return (
            'There are no active rental items listed right now. Browse Explore rentals '
            'again later, or sign up as an owner to add inventory.'
        )

    grouped_products = {}
    for product in products[:60]:
        category = product.category.name if product.category else 'Other'
        grouped_products.setdefault(category, []).append(product.name)

    item_list = '; '.join(
        f'{category}: {", ".join(names)}'
        for category, names in grouped_products.items()
    )
    total = Product.objects.filter(is_active=True).count()
    response = f'Here are the currently listed rental items: {item_list}. Browse Explore rentals to see details and availability.'
    if total > 60:
        response += f' Showing 60 of {total} items.'
    return response


def _faq_answer(message):
    query_words = {
        word for word in re.findall(r'[a-z0-9]+', message.lower())
        if len(word) > 1 and word not in STOP_WORDS
    }
    query_terms = _normalized_terms(message)
    if not query_words:
        return None

    best_faq = None
    best_score = 0
    for faq in FAQ.objects.filter(is_active=True):
        faq_text = f'{faq.question} {faq.keywords}'
        faq_words = set(re.findall(r'[a-z0-9]+', faq_text.lower()))
        faq_terms = _normalized_terms(faq_text)
        exact_matches = len(query_words & faq_words)
        normalized_matches = len(query_terms & faq_terms)
        score = (2 * exact_matches + normalized_matches) / (3 * len(query_words))
        if score > best_score:
            best_faq, best_score = faq, score
    return best_faq if best_score >= 0.5 else None


def _save_chat_log(document):
    try:
        return str(save_chat_log(document).inserted_id), None
    except (PyMongoError, RuntimeError):
        logger.exception('Chat interaction could not be saved to MongoDB.')
        return None, 'Chat history could not be saved because MongoDB is unavailable.'


@require_POST
def chat_api(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Send a valid JSON request.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'error': 'Send a JSON object.'}, status=400)

    message = payload.get('message', '')
    if not isinstance(message, str) or not message.strip() or len(message) > 1000:
        return JsonResponse(
            {'error': 'Enter a message of 1 to 1000 characters.'},
            status=400,
        )
    message = message.strip()

    email = payload.get('email', '')
    if not isinstance(email, str):
        return JsonResponse({'error': 'Email address must be text.'}, status=400)
    email = email.strip()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'error': 'Enter a valid email address.'}, status=400)

    conversation_id = payload.get('conversation_id', '')
    if not isinstance(conversation_id, str) or len(conversation_id) > 100:
        return JsonResponse({'error': 'Invalid conversation identifier.'}, status=400)
    conversation_id = conversation_id or str(uuid4())

    error = _error_code_answer(message)
    inventory_answer = None if error else _inventory_answer(message)
    faq = None if error or inventory_answer else _faq_answer(message)
    ticket = None
    if error:
        answer = f'Error {error.code} — {error.title}. {error.description} {error.resolution}'
    elif inventory_answer:
        answer = inventory_answer
    elif faq:
        answer = faq.answer
    else:
        ticket = SupportTicket.objects.create(
            subject=message[:120],
            message=message,
            email=email,
            user=request.user if request.user.is_authenticated else None,
        )
        follow_up = f' at {email}' if email else ' after you share an email address'
        answer = (
            f'I could not find a confident answer in the help articles, so I created '
            f'support ticket #{ticket.pk}. The team can follow up'
            f'{follow_up}.'
        )

    log_id, log_warning = _save_chat_log({
        'conversation_id': conversation_id,
        'question': message,
        'answer': answer,
        'faq_id': faq.pk if faq else None,
        'error_code': error.code if error else None,
        'ticket_id': ticket.pk if ticket else None,
        'user_id': request.user.pk if request.user.is_authenticated else None,
        'created_at': datetime.now(timezone.utc),
    })
    return JsonResponse({
        'answer': answer,
        'conversation_id': conversation_id,
        'ticket_id': ticket.pk if ticket else None,
        'log_id': log_id,
        'warning': log_warning,
    })


@require_POST
def feedback_api(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Send a valid JSON request.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'error': 'Send a JSON object.'}, status=400)

    rating = payload.get('rating')
    if isinstance(rating, bool) or rating not in (1, 5):
        return JsonResponse({'error': 'Rating must be 1 or 5.'}, status=400)
    comment = payload.get('comment', '')
    if not isinstance(comment, str) or len(comment) > 500:
        return JsonResponse({'error': 'Feedback must be 500 characters or fewer.'}, status=400)

    document = {
        'rating': rating,
        'comment': comment.strip(),
        'conversation_id': str(payload.get('conversation_id', ''))[:100],
        'chat_log_id': str(payload.get('log_id', ''))[:100],
        'user_id': request.user.pk if request.user.is_authenticated else None,
        'created_at': datetime.now(timezone.utc),
    }
    try:
        save_feedback(document)
    except (PyMongoError, RuntimeError):
        logger.exception('User feedback could not be saved to MongoDB.')
        return JsonResponse({'error': 'Feedback could not be saved because MongoDB is unavailable.'}, status=503)
    return JsonResponse({'saved': True})


@require_GET
def weather_api(request):
    url = (
        'https://api.open-meteo.com/v1/forecast'
        '?latitude=12.9716&longitude=77.5946&current=temperature_2m,weather_code'
        '&timezone=Asia%2FKolkata'
    )
    api_request = urllib.request.Request(url, headers={'User-Agent': 'GatherSupport/1.0'})
    try:
        with urllib.request.urlopen(api_request, timeout=2.5) as response:
            result = json.loads(response.read().decode('utf-8'))
        current = result['current']
        return JsonResponse({
            'temperature_c': current['temperature_2m'],
            'weather_code': current['weather_code'],
            'location': 'Bengaluru',
            'fallback': False,
        })
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError, urllib.error.URLError, TimeoutError, OSError):
        logger.warning('Weather API unavailable; using the built-in fallback.', exc_info=True)
        return JsonResponse({
            'temperature_c': None,
            'weather_code': None,
            'location': 'Bengaluru',
            'message': 'Live weather is temporarily unavailable. Please check a local forecast before your event.',
            'fallback': True,
        })


def page_not_found(request, exception):
    return render(request, 'myapp/404.html', status=404)


def server_error(request):
    return render(request, 'myapp/500.html', status=500)
