from django.conf import settings
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from .views import (
    IngredientViewSet,
    TagViewSet,
    UserMeAvatarAPIView,
)

if settings.DEBUG:
    from rest_framework.routers import DefaultRouter as Router
else:
    from rest_framework.routers import SimpleRouter as Router

router_v1 = Router()
router_v1.register(r'ingredients', IngredientViewSet)
router_v1.register(r'tags', TagViewSet)


urlpatterns = [
    path('', include(router_v1.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path(
        'users/me/avatar/',
        csrf_exempt(UserMeAvatarAPIView.as_view()),
        name='avatar',
    ),
]
