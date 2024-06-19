from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    is_subscribed = models.BooleanField('Подписка', default=False)
    avatar = models.URLField('Аватар')
