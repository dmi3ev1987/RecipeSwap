import csv

from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import baseconv
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import (
    AmountOfIngredientInRecipe,
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Subscription,
    Tag,
)
from .filter import IngredientNameFilter, RecipeFilterBackend
from .permissions import IsAuthorOrReadOnlyPermission
from .serializers import (
    FavoriteSerializer,
    IngredientSerializer,
    RecipeCreateUpdateSerializer,
    RecipeRetrieveSerializer,
    ShoppingCartSerializer,
    SubscriptionCreateSerializer,
    SubscriptionListSerializer,
    TagSerializer,
    UserAvatarSerializer,
)

User = get_user_model()


class UserMeAvatarAPIView(APIView):
    def put(self, request):
        serializer = UserAvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        user = request.user
        if user:
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class IngredientViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    serializer_class = IngredientSerializer
    queryset = Ingredient.objects.all()
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = IngredientNameFilter
    search_fields = ('^name',)
    pagination_class = None


class TagViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', 'post', 'patch', 'delete')
    queryset = Recipe.objects.all()
    filter_backends = (
        DjangoFilterBackend,
        RecipeFilterBackend,
        filters.OrderingFilter,
    )
    filterset_fields = ('author',)
    permission_classes = (IsAuthorOrReadOnlyPermission,)
    ordering_fields = ('id',)
    ordering = ('-id',)

    def get_serializer_class(self):
        if self.action == 'shopping_cart':
            return ShoppingCartSerializer
        if self.action == 'favorite':
            return FavoriteSerializer
        if self.request.method == 'GET':
            return RecipeRetrieveSerializer
        return RecipeCreateUpdateSerializer

    def get_response_for_create(self, request, pk):
        customer = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        data = {'customer': customer.id, 'recipe': recipe.id}
        serialazer = self.get_serializer(data=data)
        serialazer.is_valid(raise_exception=True)
        serialazer.save()
        return Response(serialazer.data, status=status.HTTP_201_CREATED)

    def get_response_for_delete(self, request, pk, model):
        customer = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        obj = model.objects.filter(
            customer=customer,
            recipe=recipe,
        )
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=['post'],
        detail=True,
        url_path='shopping_cart',
        url_name='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        return self.get_response_for_create(request, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        return self.get_response_for_delete(request, pk, ShoppingCart)

    @action(
        methods=['post'],
        detail=True,
        url_path='favorite',
        url_name='favorite',
    )
    def favorite(self, request, pk=None):
        return self.get_response_for_create(request, pk)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        return self.get_response_for_delete(request, pk, Favorite)

    @action(
        methods=['get'],
        detail=True,
        url_path='get-link',
        url_name='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        encoded_link = baseconv.base64.encode(recipe.id)
        short_link = request.build_absolute_uri(
            reverse('shortlink', kwargs={'encoded_id': encoded_link}),
        )
        return Response({'short-link': short_link}, status=status.HTTP_200_OK)

    @action(
        methods=['get'],
        detail=False,
        url_path='download_shopping_cart',
        url_name='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        customer = request.user
        ingredients = (
            AmountOfIngredientInRecipe.objects.filter(
                recipe__shopping_carts__customer=customer,
            )
            .values(
                name=F('ingredient__name'),
                measurement_unit=F('ingredient__measurement_unit'),
            )
            .annotate(total_amount=Sum('amount'))
            .order_by('name')
        )

        csv_response = HttpResponse(content_type='text/csv')
        csv_response['Content-Disposition'] = (
            'attachment; filename="shopping_cart.csv"'
        )

        writer = csv.writer(csv_response)
        writer.writerow(['Название', 'Количество', 'Единицы измерения'])
        for ingredient in ingredients:
            writer.writerow(
                [
                    ingredient['name'],
                    ingredient['total_amount'],
                    ingredient['measurement_unit'],
                ],
            )

        return csv_response


class ShortLinkView(APIView):
    def get(self, request, encoded_id):
        if not set(encoded_id).issubset(set(baseconv.BASE64_ALPHABET)):
            return Response(status=status.HTTP_400_BAD_REQUEST)
        recipe_id = baseconv.base64.decode(encoded_id)
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        recipe_url = request.build_absolute_uri(
            reverse('recipe-detail', kwargs={'pk': recipe.id}).replace(
                '/api', '',
            ),
        )
        return redirect(recipe_url)


class UserViewSet(UserViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        if self.action == 'me':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    @action(
        methods=['post'],
        detail=True,
        url_path='subscribe',
        url_name='subscribe',
        serializer_class=SubscriptionCreateSerializer,
    )
    def subscribe(self, request, id=None):
        subsciber = request.user
        author = get_object_or_404(User, id=id)
        data = {'subscriber': subsciber.id, 'author': author.id}
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        subsciber = request.user
        author = get_object_or_404(User, id=id)
        subsciption = Subscription.objects.filter(
            subscriber=subsciber,
            author=author,
        )
        if subsciption.exists():
            subsciption.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=['get'],
        detail=False,
        url_path='subscriptions',
        url_name='subscriptions',
        serializer_class=SubscriptionListSerializer,
    )
    def subscriptions(self, request):
        pagintated_queryset = self.paginate_queryset(
            Subscription.objects.filter(subscriber=request.user),
        )
        serializer = self.get_serializer(pagintated_queryset, many=True)
        return self.get_paginated_response(serializer.data)
