import json
import logging

from django import forms
from django.contrib import messages
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.forms import StyledFormMixin
from accounts.roles import admin_required
from support.models import Ticket

from . import mongo
from .engine import answer, question_hash
from .models import FAQ, ErrorCode

logger = logging.getLogger("inventory.app")

MAX_MESSAGE_LENGTH = 1000
SESSION_KEY = "assistant_conversation_id"
RATE_LIMIT = 30  # messages per minute per session/IP


def _conversation_id(request):
    cid = request.session.get(SESSION_KEY)
    if not cid:
        cid = mongo.new_conversation_id()
        request.session[SESSION_KEY] = cid
    return cid


def _rate_limited(request):
    ident = request.session.session_key or request.META.get("REMOTE_ADDR", "anon")
    key = f"chat-rate:{ident}"
    count = cache.get(key, 0)
    if count >= RATE_LIMIT:
        return True
    cache.set(key, count + 1, 60)
    return False


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return None


def _create_ticket(request, cid, message):
    qhash = question_hash(message)
    defaults = {
        "user": request.user if request.user.is_authenticated else None,
        "subject": f"Assistant question: {message[:120]}",
        "description": (f"The AI assistant could not answer this question confidently.\n\n"
                        f"Question: {message}\n\nConversation: {cid}"),
        "source": "ASSISTANT",
        "priority": Ticket.MEDIUM,
    }
    try:
        with transaction.atomic():
            ticket, created = Ticket.objects.get_or_create(conversation_id=cid, question_hash=qhash, defaults=defaults)
    except IntegrityError:
        ticket, created = Ticket.objects.get(conversation_id=cid, question_hash=qhash), False
    return ticket, created


@require_POST
def chat(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body.", "code": 400}, status=400)
    message = str(data.get("message", "")).strip()
    if not message:
        return JsonResponse({"error": "Please type a question first.", "code": 400}, status=400)
    if len(message) > MAX_MESSAGE_LENGTH:
        return JsonResponse({"error": f"Messages are limited to {MAX_MESSAGE_LENGTH} characters.", "code": 400},
                            status=400)
    if not request.session.session_key:
        request.session.save()
    if _rate_limited(request):
        return JsonResponse({"error": "You're sending messages too quickly. Please wait a minute.", "code": 429},
                            status=429)

    cid = _conversation_id(request)
    result = answer(message)
    ticket_info = None
    reply = result.answer
    if result.needs_ticket:
        ticket, created = _create_ticket(request, cid, message)
        ticket_info = {"ticket_id": ticket.ticket_id, "created": created, "status": ticket.get_status_display()}
        if created:
            reply += f"\n\nI've created support ticket **{ticket.ticket_id}** with your question."
        else:
            reply += f"\n\nYou already asked this — it's tracked in support ticket **{ticket.ticket_id}**."
        if request.user.is_authenticated:
            reply += " You can follow its progress on the Support Tickets page."

    user_id = request.user.pk if request.user.is_authenticated else None
    message_id = mongo.save_message(cid, message, reply, result.source, user_id=user_id,
                                    session_id=request.session.session_key,
                                    ticket_id=ticket_info and ticket_info["ticket_id"], matched=result.matched)
    return JsonResponse({
        "reply": reply,
        "source": result.source,
        "confidence": result.confidence,
        "matched": result.matched,
        "ticket": ticket_info,
        "conversation_id": cid,
        "message_id": message_id,
        "stored": message_id is not None,
        "used_llm": result.used_llm,
    })


@require_GET
def history(request):
    cid = request.session.get(SESSION_KEY)
    if not cid:
        return JsonResponse({"conversation_id": None, "messages": []})
    return JsonResponse({"conversation_id": cid, "messages": mongo.get_history(cid)})


@require_POST
def feedback(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body."}, status=400)
    cid = request.session.get(SESSION_KEY)
    message_id = str(data.get("message_id", ""))
    rating = data.get("rating")
    text = str(data.get("feedback_text", ""))[:500]
    if rating not in ("up", "down", 1, -1, 1.0, -1.0):
        return JsonResponse({"error": "Rating must be 'up' or 'down'."}, status=400)
    rating = 1 if rating in ("up", 1, 1.0) else -1
    if not cid or not mongo.message_belongs_to(cid, message_id):
        if mongo.ping()["status"] != "connected":
            return JsonResponse({"error": "Feedback storage is temporarily unavailable."}, status=503)
        return JsonResponse({"error": "Unknown message for this conversation."}, status=404)
    feedback_id = mongo.save_feedback(cid, message_id, rating, text)
    if not feedback_id:
        return JsonResponse({"error": "Feedback storage is temporarily unavailable."}, status=503)
    return JsonResponse({"stored": True, "feedback_id": feedback_id})


def faq_page(request):
    """FAQ page shell; the FAQ records are loaded client-side from /api/faqs/."""
    return render(request, "faq.html")


# ------------------------------------------------------ knowledge base admin
class FAQForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ["question", "answer", "category", "keywords", "is_active"]
        widgets = {"answer": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class ErrorCodeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ErrorCode
        fields = ["code", "title", "description", "possible_causes", "recommended_solution"]
        widgets = {f: forms.Textarea(attrs={"rows": 3}) for f in ("description", "possible_causes",
                                                                    "recommended_solution")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_code(self):
        code = self.cleaned_data["code"]
        if not 100 <= code <= 599:
            raise forms.ValidationError("HTTP status codes range from 100 to 599.")
        return code


@admin_required
def knowledge_base(request):
    return render(request, "knowledge_base.html", {
        "faqs": FAQ.objects.all(), "errors": ErrorCode.objects.all(), "tab": request.GET.get("tab", "faqs"),
    })


def _kb_form(request, form_class, model, pk, label, tab):
    obj = get_object_or_404(model, pk=pk) if pk else None
    form = form_class(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{label} saved.")
        return redirect(f"/assistant/knowledge-base/?tab={tab}")
    return render(request, "simple_form.html", {
        "form": form, "title": f"{'Edit' if pk else 'Add'} {label}", "cancel_url": "assistant:knowledge_base",
    })


@admin_required
@require_http_methods(["GET", "POST"])
def faq_form(request, pk=None):
    return _kb_form(request, FAQForm, FAQ, pk, "FAQ", "faqs")


@admin_required
@require_http_methods(["GET", "POST"])
def error_form(request, pk=None):
    return _kb_form(request, ErrorCodeForm, ErrorCode, pk, "error code", "errors")


@admin_required
@require_POST
def kb_delete(request, kind, pk):
    model = {"faq": FAQ, "error": ErrorCode}.get(kind)
    if not model:
        return redirect("assistant:knowledge_base")
    obj = get_object_or_404(model, pk=pk)
    obj.delete()
    messages.success(request, f"{obj} deleted.")
    return redirect(f"/assistant/knowledge-base/?tab={'faqs' if kind == 'faq' else 'errors'}")
