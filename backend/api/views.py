from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import baseconv
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import Ingredient, Recipe, Tag
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    IngredientSerializer,
    RecipeCreateSerializer,
    RecipeRetrieveSerializer,
    RecipeUpdateSerializer,
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
    filterset_fields = ('name',)
    search_fields = ('^name',)
    pagination_class = None


class TagViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    pagination_class = None


class RecepiViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', 'post', 'patch', 'delete')
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('author', 'is_favorited', 'is_in_shopping_cart')

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeRetrieveSerializer
        if self.request.method == 'POST':
            return RecipeCreateSerializer
        return RecipeUpdateSerializer

    def get_queryset(self):
        queryset = Recipe.objects.all()
        tags_slugs = self.request.query_params.getlist('tags')
        if tags_slugs:
            queryset = queryset.filter(tags__slug__in=tags_slugs).distinct()
        return queryset

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


class ShortLinkView(APIView):
    def get(self, request, encoded_id):
        if not set(encoded_id).issubset(set(baseconv.BASE64_ALPHABET)):
            return Response(
                {'error': 'Link is not valid.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        recipe_id = baseconv.base64.decode(encoded_id)
        recipe = get_object_or_404(Recipe, pk=recipe_id)
        return HttpResponse(
            request.build_absolute_uri(f'../../api/recipes/{recipe.id}'),
        )
