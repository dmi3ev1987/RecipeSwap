from django.conf import settings
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

if settings.DEBUG:
    from rest_framework.routers import DefaultRouter as Router
else:
    from rest_framework.routers import SimpleRouter as Router

from .views import (
    IngredientViewSet,
    RecepiViewSet,
    TagViewSet,
    UserMeAvatarAPIView,
    UserViewSet,
)

router_v1 = Router()
router_v1.register(r'ingredients', IngredientViewSet)
router_v1.register(r'tags', TagViewSet)
router_v1.register(r'recipes', RecepiViewSet)
router_v1.register(r'users', UserViewSet)

urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path(
        'users/me/avatar/',
        csrf_exempt(UserMeAvatarAPIView.as_view()),
        name='avatar',
    ),
]
