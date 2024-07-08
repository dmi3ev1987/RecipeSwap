import csv

from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import baseconv
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Subscriptions,
    Tag,
)
from .filter import IngredientNameFilter, RecipeFilterBackend
from .permissions import IsAuthorOrReadOnlyPermission
from .serializers import (
    FavoriteSerializer,
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeRetrieveSerializer,
    RecipeUpdateSerializer,
    ShoppingCartSerializer,
    SubscriptionCreateSerializer,
    SubscriptionListSerializer,
    TagSerializer,
    UserAvatarSerializer,
)

User = get_user_model()


class UserMeAvatarAPIView(APIView):
    def put(self, request):
        user = get_object_or_404(User, username=request.user)
        serializer = UserAvatarSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        user = get_object_or_404(User, username=request.user)
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


class RecepiViewSet(viewsets.ModelViewSet):
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
        if self.request.method == 'GET':
            return RecipeRetrieveSerializer
        if self.request.method == 'POST':
            return RecipeCreateSerializer
        return RecipeUpdateSerializer

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
        methods=['post'],
        detail=True,
        url_path='shopping_cart',
        url_name='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        customer = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        data = {'customer': customer.id, 'recipe': recipe.id}
        serialazer = ShoppingCartSerializer(data=data)
        if serialazer.is_valid():
            ShoppingCart.objects.create(
                customer=customer,
                recipe=recipe,
            )
            return Response(serialazer.data, status=status.HTTP_201_CREATED)
        return Response(serialazer.errors, status=status.HTTP_400_BAD_REQUEST)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk=None):
        customer = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        shopping_cart = ShoppingCart.objects.filter(
            customer=customer,
            recipe=recipe,
        )
        if shopping_cart.exists():
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(
        methods=['get'],
        detail=False,
        url_path='download_shopping_cart',
        url_name='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        customer = request.user
        ingredients = (
            ShoppingCart.objects.filter(customer=customer)
            .values(
                'recipe__ingredients__ingredient__name',
                'recipe__ingredients__ingredient__measurement_unit',
            )
            .annotate(amount=Sum('recipe__ingredients__amount'))
            .order_by('recipe__ingredients__ingredient__name')
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
                    ingredient['recipe__ingredients__ingredient__name'],
                    ingredient['amount'],
                    ingredient[
                        'recipe__ingredients__ingredient__measurement_unit'
                    ],
                ],
            )

        return csv_response

    @action(
        methods=['post'],
        detail=True,
        url_path='favorite',
        url_name='favorite',
    )
    def favorite(self, request, pk=None):
        customer = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        data = {'customer': customer.id, 'recipe': recipe.id}
        serialazer = FavoriteSerializer(data=data)
        if serialazer.is_valid():
            Favorite.objects.create(
                customer=customer,
                recipe=recipe,
            )
            return Response(serialazer.data, status=status.HTTP_201_CREATED)
        return Response(serialazer.errors, status=status.HTTP_400_BAD_REQUEST)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk=None):
        customer = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        favorite = Favorite.objects.filter(
            customer=customer,
            recipe=recipe,
        )
        if favorite.exists():
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)


class ShortLinkView(APIView):
    def get(self, request, encoded_id):
        if not set(encoded_id).issubset(set(baseconv.BASE64_ALPHABET)):
            return Response(
                {'error': 'Link is not valid.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe_id = baseconv.base64.decode(encoded_id)
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        return HttpResponseRedirect(
            request.build_absolute_uri(f'../../recipes/{recipe.id}'),
        )


class UserViewSet(UserViewSet):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

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
        if serializer.is_valid():
            Subscriptions.objects.get_or_create(
                subscriber=subsciber,
                author=author,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        subsciber = request.user
        author = get_object_or_404(User, id=id)
        subsciption = Subscriptions.objects.filter(
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
            Subscriptions.objects.filter(subscriber=request.user),
        )
        serializer = self.get_serializer(pagintated_queryset, many=True)
        return self.get_paginated_response(serializer.data)
