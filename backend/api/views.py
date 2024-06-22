from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import Ingredient, Tag
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny

from .serializers import (
    IngredientSerializer,
    TagSerializer,
)

User = get_user_model()


class IngredientViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_fields = ('name',)
    search_fields = ('^name',)
    pagination_class = None


class TagViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    permission_classes = (AllowAny,)
    pagination_class = None
