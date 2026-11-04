from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from accounts.forms import StyledFormMixin
from accounts.roles import is_admin

from .models import Ticket


class TicketForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["subject", "description", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_subject(self):
        subject = self.cleaned_data["subject"].strip()
        if len(subject) < 5:
            raise forms.ValidationError("Please give the ticket a descriptive subject (5+ characters).")
        return subject


class TicketAdminForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["status", "priority", "admin_response"]
        widgets = {"admin_response": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


def _get_ticket_for(request, ticket_id):
    ticket = get_object_or_404(Ticket.objects.select_related("user"), ticket_id=ticket_id)
    if not is_admin(request.user) and ticket.user_id != request.user.id:
        raise PermissionDenied("You can only view your own tickets.")
    return ticket


@login_required
def ticket_list(request):
    admin = is_admin(request.user)
    qs = Ticket.objects.select_related("user")
    if not admin:
        qs = qs.filter(user=request.user)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(ticket_id__icontains=q) | Q(subject__icontains=q) | Q(description__icontains=q)
                       | Q(user__username__icontains=q))
    status = request.GET.get("status", "")
    if status in dict(Ticket.STATUS_CHOICES):
        qs = qs.filter(status=status)
    priority = request.GET.get("priority", "")
    if priority in dict(Ticket.PRIORITY_CHOICES):
        qs = qs.filter(priority=priority)
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "tickets.html", {
        "page_obj": page, "filters": request.GET, "querystring": query.urlencode(),
        "statuses": Ticket.STATUS_CHOICES, "priorities": Ticket.PRIORITY_CHOICES, "admin_view": admin,
    })


@login_required
@require_http_methods(["GET", "POST"])
def ticket_create(request):
    form = TicketForm(request.POST or None, initial={"subject": request.GET.get("subject", "")[:160]})
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.user = request.user
        ticket.save()
        messages.success(request, f"Ticket {ticket.ticket_id} created. Our team will respond soon.")
        return redirect(ticket)
    return render(request, "ticket_form.html", {"form": form, "title": "New support ticket"})


@login_required
@require_http_methods(["GET", "POST"])
def ticket_detail(request, ticket_id):
    ticket = _get_ticket_for(request, ticket_id)
    admin_form = None
    if is_admin(request.user):
        admin_form = TicketAdminForm(request.POST or None, instance=ticket)
        if request.method == "POST" and admin_form.is_valid():
            admin_form.save()
            messages.success(request, f"Ticket {ticket.ticket_id} updated.")
            return redirect(ticket)
    elif request.method == "POST":
        raise PermissionDenied
    return render(request, "ticket_detail.html", {"ticket": ticket, "admin_form": admin_form})


@login_required
@require_http_methods(["GET", "POST"])
def ticket_update(request, ticket_id):
    ticket = _get_ticket_for(request, ticket_id)
    if not is_admin(request.user) and not ticket.user_can_edit:
        messages.error(request, "This ticket can no longer be edited.")
        return redirect(ticket)
    form = TicketForm(request.POST or None, instance=ticket)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Ticket updated.")
        return redirect(ticket)
    return render(request, "ticket_form.html", {"form": form, "title": f"Edit {ticket.ticket_id}", "ticket": ticket})


@login_required
@require_http_methods(["POST"])
def ticket_close(request, ticket_id):
    ticket = _get_ticket_for(request, ticket_id)
    if not is_admin(request.user):
        raise PermissionDenied
    ticket.status = Ticket.CLOSED
    ticket.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Ticket {ticket.ticket_id} closed.")
    return redirect(ticket)


@login_required
@require_http_methods(["GET", "POST"])
def ticket_delete(request, ticket_id):
    ticket = _get_ticket_for(request, ticket_id)
    if not is_admin(request.user) and not ticket.user_can_cancel:
        messages.error(request, "Only open tickets can be cancelled.")
        return redirect(ticket)
    if request.method == "POST":
        tid = ticket.ticket_id
        ticket.delete()
        messages.success(request, f"Ticket {tid} cancelled and removed.")
        return redirect("support:list")
    return render(request, "confirm_delete.html", {
        "object": ticket, "kind": "ticket", "cancel_url": ticket.get_absolute_url(),
        "warning": "Cancelling removes the ticket permanently.", "confirm_label": "Cancel ticket",
    })
