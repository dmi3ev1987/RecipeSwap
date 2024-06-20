from django.conf import settings
from django.urls import include, path
from djoser import views

from .views import IngredientViewSet, TagViewSet, UsersViewSet

if settings.DEBUG:
    from rest_framework.routers import DefaultRouter as Router
else:
    from rest_framework.routers import SimpleRouter as Router

router_v1 = Router()
router_v1.register(r'ingredients', IngredientViewSet)
router_v1.register(r'tags', TagViewSet)
router_v1.register(r'users', UsersViewSet)

urlpatterns = [
    path('', include(router_v1.urls)),
    path('auth/token/login/', views.TokenCreateView.as_view(), name='login'),
    path(
        'auth/token/logout/', views.TokenDestroyView.as_view(), name='logout',
    ),
    # path('', include('djoser.urls')),
]
