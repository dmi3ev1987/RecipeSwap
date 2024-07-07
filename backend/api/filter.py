import django_filters
from recipes.models import Ingredient
from rest_framework.filters import BaseFilterBackend


class RecipeFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        tags_slugs = request.query_params.getlist('tags')
        is_in_shopping_cart = request.query_params.get('is_in_shopping_cart')
        is_favorited = request.query_params.get('is_favorited')
        customer = request.user
        if tags_slugs:
            queryset = queryset.filter(tags__slug__in=tags_slugs).distinct()
        if is_in_shopping_cart == '1' and customer.is_authenticated:
            queryset = queryset.filter(shopping_carts__customer=customer)
        if is_favorited == '1' and customer.is_authenticated:
            queryset = queryset.filter(favorites__customer=customer)
        return queryset


class IngredientNameFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='startswith')

    class Meta:
        model = Ingredient
        fields = [
            'name',
        ]
