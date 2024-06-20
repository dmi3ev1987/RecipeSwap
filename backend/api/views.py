from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import Ingredient, Tag
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (
    AllowAny,
)

from .permissions import IsAuthorPermission
from .serializers import IngredientSerializer, TagSerializer, UserSerializer

User = get_user_model()


class UsersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ('get', 'post')
    permission_classes = [IsAuthorPermission]
    pagination_class = LimitOffsetPagination

    def get_instance(self):
        return self.request.user

    @action(
        ['get'],
        detail=False,
        permission_classes=[IsAuthorPermission],
        serializer_class=UserSerializer,
    )
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        return self.retrieve(request, *args, **kwargs)


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
