from datetime import date, timedelta

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.forms import StyledFormMixin
from accounts.roles import customer_required, is_staff_member, staff_required
from inventory.models import Category, Product

from . import services
from .models import Booking


def _parse(value, default):
    try:
        return date.fromisoformat(value) if value else default
    except ValueError:
        return default


def default_range():
    today = timezone.localdate()
    return today + timedelta(days=1), today + timedelta(days=3)


class BookingForm(StyledFormMixin, forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.filter(quantity__gt=0).order_by("name"))
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    quantity = forms.IntegerField(min_value=1, max_value=10000, initial=1)
    note = forms.CharField(max_length=255, required=False, label="Note for staff (optional)",
                           widget=forms.TextInput(attrs={"placeholder": "Event name, delivery details…"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        today = timezone.localdate().isoformat()
        self.fields["start_date"].widget.attrs["min"] = today
        self.fields["end_date"].widget.attrs["min"] = today

    def clean(self):
        data = super().clean()
        start, end = data.get("start_date"), data.get("end_date")
        if start and end:
            try:
                services.validate_dates(start, end)
            except ValidationError as exc:
                self.add_error("end_date" if end < start else "start_date", exc.messages[0])
        return data


class ReviewForm(StyledFormMixin, forms.Form):
    note = forms.CharField(max_length=255, required=False, label="Message to customer (optional)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


# ------------------------------------------------------------------ customer
@customer_required
def customer_dashboard(request):
    start = _parse(request.GET.get("start"), default_range()[0])
    end = _parse(request.GET.get("end"), default_range()[1])
    if end < start:
        end = start
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    products = Product.objects.select_related("category").order_by("name")
    if q:
        products = products.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q))
    if category.isdigit():
        products = products.filter(category_id=int(category))
    page = Paginator(products, 12).get_page(request.GET.get("page"))
    free = services.availability_for_products(page.object_list, start, end)
    catalogue = [{"product": p, "available": free[p.pk]} for p in page.object_list]

    mine = Booking.objects.filter(customer=request.user).select_related("product")
    stats = mine.aggregate(
        pending=Count("id", filter=Q(status=Booking.PENDING)),
        approved=Count("id", filter=Q(status=Booking.APPROVED, end_date__gte=timezone.localdate())),
        total=Count("id"),
        units=Sum("quantity", filter=Q(status=Booking.APPROVED, end_date__gte=timezone.localdate())),
    )
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "bookings/customer_dashboard.html", {
        "catalogue": catalogue, "page_obj": page, "start": start, "end": end, "q": q, "category": category,
        "categories": Category.objects.all(), "bookings": mine[:10], "stats": stats,
        "querystring": query.urlencode(), "days": (end - start).days + 1,
        "today": timezone.localdate().isoformat(),
    })


@customer_required
@require_http_methods(["GET", "POST"])
def booking_create(request):
    initial = {"start_date": request.GET.get("start") or default_range()[0],
               "end_date": request.GET.get("end") or default_range()[1], "quantity": 1}
    if request.GET.get("product", "").isdigit():
        initial["product"] = int(request.GET["product"])
    form = BookingForm(request.POST or None, initial=initial)
    selected = None
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            booking = services.create_booking(customer=request.user, product=d["product"], quantity=d["quantity"],
                                              start=d["start_date"], end=d["end_date"], note=d["note"])
        except ValidationError as exc:
            form.add_error("quantity", exc.messages[0])
        else:
            messages.success(request, f"Booking {booking.booking_id} sent for approval. "
                                      "Staff will confirm it shortly.")
            return redirect(booking)
    product_id = form["product"].value()
    if product_id and str(product_id).isdigit():
        selected = Product.objects.filter(pk=int(product_id)).first()
    availability = None
    if selected:
        s = _parse(str(form["start_date"].value() or ""), default_range()[0])
        e = _parse(str(form["end_date"].value() or ""), default_range()[1])
        if e >= s:
            availability = {"start": s, "end": e, "free": services.available_quantity(selected, s, e)}
    return render(request, "bookings/booking_form.html", {"form": form, "selected": selected,
                                                          "availability": availability})


@customer_required
def my_bookings(request):
    qs = Booking.objects.filter(customer=request.user).select_related("product")
    status = request.GET.get("status", "")
    if status in dict(Booking.STATUS_CHOICES):
        qs = qs.filter(status=status)
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    return render(request, "bookings/my_bookings.html", {"page_obj": page, "status": status,
                                                         "statuses": Booking.STATUS_CHOICES})


def _get_booking(request, booking_id):
    booking = get_object_or_404(Booking.objects.select_related("product", "customer", "reviewed_by"),
                                booking_id=booking_id)
    if not is_staff_member(request.user) and booking.customer_id != request.user.id:
        raise PermissionDenied("You can only view your own bookings.")
    return booking


def booking_detail(request, booking_id):
    if not request.user.is_authenticated:
        return redirect(f"/accounts/login/?next={request.path}")
    booking = _get_booking(request, booking_id)
    free = services.available_quantity(booking.product, booking.start_date, booking.end_date,
                                       exclude_pk=booking.pk)
    return render(request, "bookings/booking_detail.html", {
        "booking": booking, "free_excluding": free, "review_form": ReviewForm(),
        "is_staff_view": is_staff_member(request.user),
    })


@require_POST
def booking_cancel(request, booking_id):
    if not request.user.is_authenticated:
        return redirect("accounts:login")
    booking = _get_booking(request, booking_id)
    if booking.customer_id != request.user.id and not is_staff_member(request.user):
        raise PermissionDenied
    try:
        services.cancel_booking(booking, request.user)
        messages.success(request, f"Booking {booking.booking_id} cancelled.")
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect(booking)


# --------------------------------------------------------------------- staff
@staff_required
def manage(request):
    qs = Booking.objects.select_related("product", "customer", "reviewed_by")
    status = request.GET.get("status", Booking.PENDING)
    if status in dict(Booking.STATUS_CHOICES):
        qs = qs.filter(status=status)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(booking_id__icontains=q) | Q(product__name__icontains=q) | Q(product__sku__icontains=q)
                       | Q(customer__username__icontains=q))
    qs = qs.order_by("start_date", "created_at") if status == Booking.PENDING else qs
    page = Paginator(qs, 15).get_page(request.GET.get("page"))
    counts = dict(Booking.objects.values_list("status").annotate(n=Count("id")))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "bookings/manage.html", {
        "page_obj": page, "status": status, "q": q, "statuses": Booking.STATUS_CHOICES, "counts": counts,
        "querystring": query.urlencode(), "review_form": ReviewForm(),
    })


@staff_required
@require_POST
def review(request, booking_id, action):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    form = ReviewForm(request.POST)
    note = form.cleaned_data["note"] if form.is_valid() else ""
    try:
        if action == "approve":
            services.approve_booking(booking, request.user, note)
            messages.success(request, f"Booking {booking.booking_id} approved – "
                                      f"{booking.quantity} unit(s) blocked from {booking.start_date:%d %b} "
                                      f"to {booking.end_date:%d %b}.")
        elif action == "reject":
            services.reject_booking(booking, request.user, note)
            messages.success(request, f"Booking {booking.booking_id} rejected.")
        else:
            raise PermissionDenied
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect(request.POST.get("next") or "bookings:manage")


@staff_required
def calendar_view(request):
    today = timezone.localdate()
    month = request.GET.get("month", "")
    try:
        year, mon = (int(x) for x in month.split("-"))
        date(year, mon, 1)
    except (ValueError, TypeError):
        year, mon = today.year, today.month
    cal = services.month_calendar(year, mon)
    upcoming = (Booking.objects.filter(status=Booking.APPROVED, end_date__gte=today)
                .select_related("product", "customer").order_by("start_date")[:10])
    return render(request, "bookings/calendar.html", {"cal": cal, "upcoming": upcoming})
