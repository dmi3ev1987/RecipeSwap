from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    first_name = models.CharField('Имя', max_length=150, blank=False)
    last_name = models.CharField('Фамилия', max_length=150, blank=False)
    email = models.EmailField('Адрес электронной почты', blank=False)
    is_subscribed = models.BooleanField('Подписка', default=False)
    avatar = models.URLField('Аватар', blank=True)
    REQUIRED_FIELDS = ('email', 'first_name', 'last_name', 'password')
