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


class TagInRecipe(models.Model):
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, verbose_name=' Тег')
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        default_related_name = 'tags_in_recipe'
        verbose_name = 'тег в рецепте'
        verbose_name_plural = 'Теги в рецепте'

    def __str__(self):
        return f'{self.tag} {self.recipe}'


class Ingredient(models.Model):
    name = models.CharField('Название', max_length=128)
    measurement_unit = models.CharField('Единицы измерения', max_length=64)

    class Meta:
        default_related_name = 'ingredients'
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'

    def __str__(self):
        return self.name


class AmountOfIngredient(models.Model):
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        validators=[
            MinValueValidator(limit_value=1),
        ],
    )

    class Meta:
        default_related_name = 'amount_of_ingredient'
        verbose_name = 'количество ингредента'
        verbose_name_plural = 'Количество ингредиентов'

    def __str__(self):
        return f'{self.ingredient} {self.amount}'


class IngredientInRecipe(models.Model):
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )
    amount_of_ingredient = models.ForeignKey(
        AmountOfIngredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент',
    )

    class Meta:
        default_related_name = 'ingredient_in_recipe'
        verbose_name = 'ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецепте'

    def __str__(self):
        return f'{self.amount_of_ingredient} {self.recipe}'


class Recipe(models.Model):
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
        through=TagInRecipe,
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
    )
    ingredients = models.ManyToManyField(
        AmountOfIngredient,
        verbose_name='Ингредиенты в рецепте',
        through=IngredientInRecipe,
    )
    is_favorited = models.BooleanField('Избранное', default=False)
    is_in_shopping_cart = models.BooleanField('Корзина', default=False)
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


class Subscriptions(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='authors',
    )
    subscriber = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Подписчик',
        related_name='subscribers',
    )

    class Meta:
        default_related_name = 'subscriptions'
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['author', 'subscriber'],
                name='unique_author_subscriber',
            ),
        ]

    def __str__(self):
        return f'{self.subscriber} подписан на {self.author}'
