from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from functools import wraps
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from .forms import BookingForm, ProductForm, SignUpForm
from .models import Booking, BookingItem, Payment, Product, UserProfile


ACTIVE_BOOKING_STATUSES = (
    Booking.Status.PENDING,
    Booking.Status.PAYMENT_PENDING,
    Booking.Status.CONFIRMED,
)


def user_role(user):
    return UserProfile.objects.filter(user=user).values_list('role', flat=True).first()


def role_required(role):
    def decorator(view_function):
        @wraps(view_function)
        @login_required
        def wrapped(request, *args, **kwargs):
            if user_role(request.user) != role:
                messages.error(request, 'You do not have permission to access that page.')
                return redirect('dashboard')
            return view_function(request, *args, **kwargs)

        return wrapped

    return decorator


def home(request):
    products = Product.objects.filter(is_active=True).select_related('owner')
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()
    if query:
        products = products.filter(name__icontains=query)
    if category_id.isdigit():
        products = products.filter(category_id=int(category_id))
    categories = Product.objects.filter(
        is_active=True,
        category__isnull=False,
    ).values_list('category_id', 'category__name').distinct().order_by('category__name')
    return render(
        request,
        'myapp/home.html',
        {
            'products': products,
            'categories': categories,
            'search_query': query,
            'selected_category': category_id,
        },
    )


@require_http_methods(['GET', 'POST'])
def sign_up(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = SignUpForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            user = form.save()
            UserProfile.objects.create(user=user, role=form.cleaned_data['role'])
        login(request, user)
        messages.success(request, 'Your account is ready.')
        return redirect('dashboard')
    return render(request, 'myapp/signup.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def sign_in(request):
    next_url = request.POST.get('next', request.GET.get('next', ''))
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect('dashboard')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('dashboard')
        error = 'The username or password was not recognized.'
    return render(
        request,
        'myapp/login.html',
        {'error': error, 'next_url': next_url},
    )


@require_POST
def sign_out(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def dashboard(request):
    role = user_role(request.user)
    if role == UserProfile.Role.OWNER:
        products = Product.objects.filter(owner=request.user)
        bookings = Booking.objects.filter(owner=request.user).select_related(
            'customer', 'product'
        )
        booking_filter = request.GET.get('status', '')
        if booking_filter in Booking.Status.values:
            bookings = bookings.filter(status=booking_filter)
        today = timezone.localdate()
        date_filter = request.GET.get('period', '')
        if date_filter == 'today':
            bookings = bookings.filter(start_date=today)
        elif date_filter == 'upcoming':
            bookings = bookings.filter(start_date__gt=today)
        elif date_filter == 'completed':
            bookings = bookings.filter(end_date__lt=today)
        payment_totals = Payment.objects.filter(
            booking__owner=request.user,
        ).aggregate(
            advances=Sum('amount', filter=Q(
                payment_type=Payment.PaymentType.ADVANCE,
                status=Payment.Status.SUCCESS,
            )),
            balances=Sum('amount', filter=Q(
                payment_type=Payment.PaymentType.BALANCE,
                status=Payment.Status.SUCCESS,
            )),
            refunds=Sum('amount', filter=Q(
                payment_type=Payment.PaymentType.REFUND,
                status=Payment.Status.SUCCESS,
            )),
        )
        advances = payment_totals['advances'] or Decimal('0.00')
        balances = payment_totals['balances'] or Decimal('0.00')
        refunds = payment_totals['refunds'] or Decimal('0.00')
        pending_payment_bookings = Booking.objects.filter(
            owner=request.user,
            status=Booking.Status.PAYMENT_PENDING,
        )
        metrics = {
            'inventory_count': products.count(),
            'available_inventory_count': products.filter(is_active=True).count(),
            'active_bookings': Booking.objects.filter(
                owner=request.user,
                status=Booking.Status.CONFIRMED,
            ).count(),
            'pending_bookings': Booking.objects.filter(
                owner=request.user,
                status__in=(Booking.Status.PENDING, Booking.Status.PAYMENT_PENDING),
            ).count(),
            'revenue': advances + balances - refunds,
            'advance_revenue': advances,
            'balance_revenue': balances,
            'refunds': refunds,
            'pending_payments': sum(
                (booking.advance_due for booking in pending_payment_bookings),
                Decimal('0.00'),
            ),
            'upcoming_events': Booking.objects.filter(
                owner=request.user,
                status=Booking.Status.CONFIRMED,
                start_date__gte=today,
            ).count(),
        }
    elif role == UserProfile.Role.CUSTOMER:
        products = Product.objects.filter(is_active=True).exclude(
            owner=request.user
        ).select_related('owner')
        bookings = Booking.objects.filter(customer=request.user).select_related(
            'owner', 'product'
        )
    else:
        messages.error(request, 'Your account needs an owner or customer role.')
        return redirect('home')

    return render(
        request,
        'myapp/dashboard.html',
        {
            'role': role,
            'products': products,
            'bookings': bookings,
            'metrics': metrics if role == UserProfile.Role.OWNER else {},
            'status_filter': request.GET.get('status', ''),
            'status_choices': Booking.Status.choices,
            'period_filter': request.GET.get('period', ''),
        },
    )


@role_required(UserProfile.Role.OWNER)
def owner_portal(request):
    return dashboard(request)


@role_required(UserProfile.Role.CUSTOMER)
def customer_bookings(request):
    return dashboard(request)


@role_required(UserProfile.Role.OWNER)
def owner_calendar(request):
    products = Product.objects.filter(owner=request.user).order_by('name')
    selected_id = request.GET.get('item', '')
    if selected_id.isdigit():
        product = get_object_or_404(products, pk=int(selected_id))
    else:
        product = products.first()
    if product is None:
        return render(request, 'myapp/calendar.html', {'products': products})

    raw_start = request.GET.get('start', '')
    try:
        start = date.fromisoformat(raw_start) if raw_start else timezone.localdate()
    except ValueError:
        messages.error(request, 'Enter a valid start date.')
        start = timezone.localdate()
    days = []
    for offset in range(30):
        current_day = start + timedelta(days=offset)
        reserved = peak_reserved_quantity(product, current_day, current_day)
        days.append({
            'date': current_day,
            'available': max(product.stock - reserved, 0),
            'stock': product.stock,
        })
    return render(
        request,
        'myapp/calendar.html',
        {'products': products, 'product': product, 'days': days, 'start': start},
    )


@role_required(UserProfile.Role.OWNER)
def add_product(request):
    form = ProductForm(request.POST or None)
    if form.is_valid():
        product = form.save(commit=False)
        product.owner = request.user
        product.save()
        messages.success(request, f'{product.name} was added to your stock.')
        return redirect('dashboard')
    return render(request, 'myapp/product_form.html', {'form': form})


@role_required(UserProfile.Role.OWNER)
def edit_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id, owner=request.user)
    form = ProductForm(request.POST or None, instance=product)
    if form.is_valid():
        form.save()
        messages.success(request, f'{product.name} was updated.')
        return redirect('dashboard')
    return render(
        request,
        'myapp/product_form.html',
        {'form': form, 'product': product},
    )


@role_required(UserProfile.Role.OWNER)
@require_POST
def deactivate_product(request, product_id):
    product = get_object_or_404(Product, pk=product_id, owner=request.user)
    product.is_active = False
    product.save(update_fields=['is_active'])
    messages.success(request, f'{product.name} is no longer listed.')
    return redirect('dashboard')


def peak_reserved_quantity(product, start_date, end_date):
    reservations = Booking.objects.filter(
        product=product,
        status__in=(Booking.Status.PENDING, Booking.Status.CONFIRMED),
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).values_list('start_date', 'end_date', 'quantity')
    payment_holds = Booking.objects.filter(
        product=product,
        status=Booking.Status.PAYMENT_PENDING,
        hold_expires_at__gt=timezone.now(),
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).values_list('start_date', 'end_date', 'quantity')
    reservations = list(reservations) + list(payment_holds)
    changes = defaultdict(int)
    for reserved_start, reserved_end, quantity in reservations:
        changes[max(start_date, reserved_start)] += quantity
        changes[min(end_date, reserved_end) + timedelta(days=1)] -= quantity

    reserved = peak = 0
    for day in sorted(changes):
        reserved += changes[day]
        peak = max(peak, reserved)
    return peak


@role_required(UserProfile.Role.CUSTOMER)
def book_product(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related('owner'),
        pk=product_id,
        is_active=True,
    )
    if product.owner_id == request.user.id:
        messages.error(request, 'You cannot reserve your own stock.')
        return redirect('dashboard')

    form = BookingForm(request.POST or None)
    if form.is_valid():
        booking = None
        with transaction.atomic():
            locked_product = get_object_or_404(
                Product.objects.select_for_update(),
                pk=product.pk,
                is_active=True,
            )
            locked_product.save(update_fields=['updated_at'])
            available = locked_product.stock - peak_reserved_quantity(
                locked_product,
                form.cleaned_data['start_date'],
                form.cleaned_data['end_date'],
            )
            if form.cleaned_data['quantity'] > available:
                form.add_error(
                    'quantity',
                    f'Only {max(available, 0)} item(s) are available for those dates.',
                )
            else:
                booking = Booking.objects.create(
                    customer=request.user,
                    owner=locked_product.owner,
                    product=locked_product,
                    event_name=form.cleaned_data['event_name'],
                    event_type=form.cleaned_data['event_type'],
                    event_location=form.cleaned_data['event_location'],
                    start_date=form.cleaned_data['start_date'],
                    end_date=form.cleaned_data['end_date'],
                    quantity=form.cleaned_data['quantity'],
                    price_per_day=locked_product.price_per_day,
                    advance_percent=20,
                )
                BookingItem.objects.create(
                    booking=booking,
                    product=locked_product,
                    quantity=booking.quantity,
                    price_per_day=booking.price_per_day,
                    number_of_days=booking.duration_days,
                    subtotal=booking.total_amount,
                )

        if booking:
            messages.success(
                request,
                f'Reservation request sent. Advance required: ₹{booking.advance_due:.2f}. '
                'The owner must approve it before the mock payment step.',
            )
            return redirect('dashboard')

    return render(
        request,
        'myapp/booking_form.html',
        {'form': form, 'product': product, 'advance_percent': 20},
    )


@role_required(UserProfile.Role.OWNER)
@require_POST
@transaction.atomic
def reservation_action(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_for_update(),
        pk=booking_id,
        owner=request.user,
    )
    action = request.POST.get('action')
    if booking.status != Booking.Status.PENDING:
        messages.error(request, 'Only pending reservations can be reviewed.')
    elif action == 'confirm':
        booking.status = Booking.Status.PAYMENT_PENDING
        booking.hold_expires_at = timezone.now() + timedelta(minutes=15)
        booking.save(update_fields=['status', 'hold_expires_at'])
        messages.success(request, 'Request approved. The customer has 15 minutes to pay the advance.')
    elif action == 'reject':
        booking.status = Booking.Status.REJECTED
        booking.save(update_fields=['status'])
        messages.success(request, 'Reservation declined; its stock is available again.')
    else:
        messages.error(request, 'Choose a valid reservation action.')
    return redirect('dashboard')


@role_required(UserProfile.Role.CUSTOMER)
@require_POST
def cancel_booking(request, booking_id):
    booking = get_object_or_404(
        Booking,
        pk=booking_id,
        customer=request.user,
    )
    if booking.status not in ACTIVE_BOOKING_STATUSES:
        messages.error(request, 'This reservation can no longer be cancelled.')
    else:
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=['status'])
        messages.success(request, 'Reservation cancelled; its stock is available again.')
    return redirect('dashboard')


@role_required(UserProfile.Role.CUSTOMER)
def payment_checkout(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('product', 'customer', 'owner'),
        pk=booking_id,
        customer=request.user,
    )
    if booking.status == Booking.Status.PAYMENT_PENDING and booking.hold_expires_at:
        if booking.hold_expires_at <= timezone.now():
            booking.status = Booking.Status.PAYMENT_FAILED
            booking.save(update_fields=['status'])
            messages.error(request, 'The payment hold expired. Please request a new booking.')
            return redirect('dashboard')
    elif booking.status != Booking.Status.CONFIRMED:
        messages.error(request, 'This booking is not ready for advance payment.')
        return redirect('dashboard')

    if booking.status == Booking.Status.CONFIRMED:
        messages.info(request, 'The advance payment for this booking has already been recorded.')
        return redirect('receipt', booking_id=booking.pk)

    return render(request, 'myapp/payment_checkout.html', {'booking': booking})


@role_required(UserProfile.Role.CUSTOMER)
@require_POST
@transaction.atomic
def mock_advance_payment(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_for_update(),
        pk=booking_id,
        customer=request.user,
    )
    if booking.status != Booking.Status.PAYMENT_PENDING:
        messages.error(request, 'This booking is not awaiting payment.')
        return redirect('dashboard')
    if not booking.hold_expires_at or booking.hold_expires_at <= timezone.now():
        booking.status = Booking.Status.PAYMENT_FAILED
        booking.save(update_fields=['status'])
        Payment.objects.create(
            booking=booking,
            amount=booking.advance_due,
            payment_type=Payment.PaymentType.ADVANCE,
            status=Payment.Status.FAILED,
            reference_id=f'DEMO-FAILED-{uuid4().hex[:12].upper()}',
        )
        messages.error(request, 'The payment hold expired. No payment was collected.')
        return redirect('dashboard')

    Payment.objects.create(
        booking=booking,
        amount=booking.advance_due,
        payment_type=Payment.PaymentType.ADVANCE,
        status=Payment.Status.SUCCESS,
        reference_id=f'DEMO-{uuid4().hex[:12].upper()}',
        paid_at=timezone.now(),
    )
    booking.status = Booking.Status.CONFIRMED
    booking.save(update_fields=['status'])
    messages.success(request, 'Mock advance payment recorded. No real money was collected.')
    return redirect('receipt', booking_id=booking.pk)


@login_required
def receipt(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('customer', 'owner', 'product').prefetch_related('payments'),
        pk=booking_id,
    )
    if request.user.pk not in (booking.customer_id, booking.owner_id) and not request.user.is_staff:
        messages.error(request, 'You cannot view this booking receipt.')
        return redirect('dashboard')
    return render(request, 'myapp/receipt.html', {'booking': booking})
