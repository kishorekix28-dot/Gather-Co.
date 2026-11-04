from rest_framework import serializers

from assistant.models import FAQ, ErrorCode
from inventory.models import Category, Product
from support.models import Ticket


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer", "category", "is_active", "created_at", "updated_at"]


class ErrorCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorCode
        fields = ["id", "code", "title", "description", "possible_causes", "recommended_solution", "created_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "description"]


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    stock_status = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = ["id", "name", "sku", "category", "price", "cost", "quantity", "min_stock_level", "stock_status",
                  "updated_at"]


class TicketSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Ticket
        fields = ["ticket_id", "user", "subject", "description", "status", "priority", "source", "admin_response",
                  "created_at", "updated_at"]
        read_only_fields = ["ticket_id", "user", "status", "source", "admin_response", "created_at", "updated_at"]
