from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

User = get_user_model()


class Tag(models.Model):
    name = models.CharField('Название', max_length=32)
    slug = models.SlugField('Слаг', max_length=32, unique=True)

    class Meta:
        default_related_name = 'tags'
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField('Название', max_length=128)
    measurement_unit = models.CharField('Единицы измерения', max_length=64)

    class Meta:
        default_related_name = 'ingredients'
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    recipe = models.ManyToManyField('Recipe', verbose_name='Рецепт')
    ingredient = models.ManyToManyField(Ingredient, verbose_name='Ингредиент')
    amount = models.PositiveSmallIntegerField('Количество')

    class Meta:
        default_related_name = 'ingredients_in_recipe'
        verbose_name = 'ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'

    def __str__(self):
        return self.ingredient


class Recipe(models.Model):
    tags = models.ManyToManyField(Tag, verbose_name='Теги')
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
    )
    ingredients = models.ManyToManyField(
        IngredientInRecipe,
        verbose_name='Ингредиенты в рецепте',
    )
    is_favorited = models.BooleanField()
    is_in_shopping_cart = models.BooleanField()
    name = models.CharField('Название', max_length=256)
    image = models.ImageField()
    text = models.TextField('Рецепт')
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[
            MinValueValidator(limit_value=1),
        ],
    )

    class Meta:
        default_related_name = 'recipes'
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class Subscribtion(models.Model):
    author = models.ManyToManyField(User, verbose_name='Автор')
    recipe = models.ManyToManyField(Recipe, verbose_name='Рецепт')

    class Meta:
        default_related_name = 'subscribtions'
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'

    def __str__(self):
        return self.author
