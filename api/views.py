from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from accounts.roles import is_admin
from assistant.models import FAQ, ErrorCode
from inventory.models import Product
from inventory.selectors import inventory_totals
from inventory.views import filter_products
from support.models import Ticket

from .serializers import ErrorCodeSerializer, FAQSerializer, ProductSerializer, TicketSerializer


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and is_admin(request.user))


class ReadPublicWriteAdmin(permissions.BasePermission):
    """Knowledge base: anyone may read, only administrators may write."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and is_admin(request.user))


# ------------------------------------------------------------------- FAQs
class FAQList(generics.ListCreateAPIView):
    serializer_class = FAQSerializer
    permission_classes = [ReadPublicWriteAdmin]

    def get_queryset(self):
        qs = FAQ.objects.all()
        if not (self.request.user.is_authenticated and is_admin(self.request.user)):
            qs = qs.filter(is_active=True)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__iexact=category)
        return qs


class FAQDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FAQSerializer
    permission_classes = [ReadPublicWriteAdmin]
    queryset = FAQ.objects.filter(is_active=True)


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def faq_search(request):
    q = request.query_params.get("q", "").strip()
    qs = FAQ.objects.filter(is_active=True)
    if q:
        qs = qs.filter(Q(question__icontains=q) | Q(answer__icontains=q) | Q(keywords__icontains=q)
                       | Q(category__icontains=q))
    data = FAQSerializer(qs, many=True).data
    return Response({"query": q, "count": len(data), "results": data})


# ------------------------------------------------------------ Error codes
class ErrorList(generics.ListCreateAPIView):
    serializer_class = ErrorCodeSerializer
    permission_classes = [ReadPublicWriteAdmin]
    queryset = ErrorCode.objects.all()


class ErrorDetail(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ErrorCodeSerializer
    permission_classes = [ReadPublicWriteAdmin]
    queryset = ErrorCode.objects.all()

    def get_object(self):
        obj = get_object_or_404(ErrorCode, code=self.kwargs["code"])
        self.check_object_permissions(self.request, obj)
        return obj


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def error_search(request):
    q = request.query_params.get("q", "").strip()
    qs = ErrorCode.objects.all()
    if q:
        filt = Q(title__icontains=q) | Q(description__icontains=q) | Q(possible_causes__icontains=q)
        if q.isdigit():
            filt |= Q(code=int(q))
        qs = qs.filter(filt)
    data = ErrorCodeSerializer(qs, many=True).data
    return Response({"query": q, "count": len(data), "results": data})


# ---------------------------------------------------- Inventory (secured)
class ProductList(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return filter_products(self.request.query_params)


class ProductDetail(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.select_related("category")


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def inventory_summary(request):
    totals = inventory_totals()
    totals["total_value"] = str(totals["total_value"])
    totals["retail_value"] = str(totals["retail_value"])
    return Response(totals)


class TicketList(generics.ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Ticket.objects.select_related("user")
        return qs if is_admin(self.request.user) else qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
