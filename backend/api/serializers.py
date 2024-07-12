from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from recipes.models import (
    AmountOfIngredientInRecipe,
    Favorite,
    Ingredient,
    Recipe,
    ShoppingCart,
    Subscription,
    Tag,
    TagInRecipe,
)
from .fields import Base64ImageField

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return Subscription.objects.filter(
                subscriber=user.id,
                author=obj.id,
            ).exists()
        return False

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def validate_username(self, value):
        if value == 'me':
            raise serializers.ValidationError(
                settings.ERROR_MESSAGES.get('me'),
            )
        return value


class UserAvatarSerializer(UserSerializer):
    avatar = Base64ImageField(required=True, allow_null=False)

    class Meta(UserSerializer.Meta):
        fields = ('avatar',)


class UserReadSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        help_text='Введите пароль',
    )
    email = serializers.EmailField(
        required=True,
        help_text='Введите адрес электронной почты',
        validators=[UniqueValidator(queryset=User.objects.all())],
    )

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class TagsInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=False,
    )

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('name', 'slug')


class AmountOfIngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        many=False,
    )

    class Meta:
        model = AmountOfIngredientInRecipe
        fields = ('id', 'amount')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit',
    )

    class Meta:
        model = AmountOfIngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')
        read_only_fields = ('amount',)


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    author = UserReadSerializer(read_only=True)
    image = Base64ImageField(required=True, allow_null=False)
    ingredients = AmountOfIngredientInRecipeSerializer(
        many=True,
        write_only=True,
    )
    tags = TagsInRecipeSerializer(many=True, required=True)

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                settings.ERROR_MESSAGES.get('empty_ingredients'),
            )
        validated_value = []
        for val in value:
            if val in validated_value:
                raise serializers.ValidationError(
                    settings.ERROR_MESSAGES.get('repeat_ingredients'),
                )
            validated_value.append(val)
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError(
                settings.ERROR_MESSAGES.get('empty_tags'),
            )
        validated_value = []
        for val in value:
            if val in validated_value:
                raise serializers.ValidationError(
                    settings.ERROR_MESSAGES.get('repeat_tags'),
                )
            validated_value.append(val)
        return value

    def validate(self, data):
        if 'ingredients' not in data:
            raise serializers.ValidationError(
                settings.ERROR_MESSAGES.get('no_ingredients'),
            )
        return data

    def to_internal_value(self, data):
        tags = data.get('tags', [])
        data['tags'] = [{'id': tag} for tag in tags]
        return super().to_internal_value(data)

    def tags_ingredients_bulk_create(self, tags, ingredients, recipe):
        tags_list = [
            TagInRecipe(tag_id=tag['id'].pk, recipe=recipe) for tag in tags
        ]
        TagInRecipe.objects.bulk_create(tags_list)

        ingredients_list = [
            AmountOfIngredientInRecipe(
                ingredient_id=ingredient['id'].pk,
                amount=ingredient['amount'],
                recipe=recipe,
            )
            for ingredient in ingredients
        ]
        AmountOfIngredientInRecipe.objects.bulk_create(ingredients_list)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        request = self.context.get('request')

        recipe = Recipe.objects.create(author=request.user, **validated_data)
        self.tags_ingredients_bulk_create(tags, ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance = super().update(instance, validated_data)
        instance.save()
        instance.tags.clear()
        instance.ingredients.clear()

        recipe = get_object_or_404(Recipe, pk=instance.pk)
        self.tags_ingredients_bulk_create(tags, ingredients, recipe)
        return recipe

    def to_representation(self, instance):
        recipe_data = super().to_representation(instance)
        recipe_data['ingredients'] = IngredientInRecipeSerializer(
            instance.amount_of_ingredient.all(),
            many=True,
        ).data
        return recipe_data

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
        )


class RecipeRetrieveSerializer(RecipeCreateUpdateSerializer):
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    def get_is_favorited(self, obj):
        customer = self.context.get('request').user
        if customer.is_authenticated:
            return Favorite.objects.filter(
                customer=customer,
                recipe=obj,
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        customer = self.context.get('request').user
        if customer.is_authenticated:
            return ShoppingCart.objects.filter(
                customer=customer,
                recipe=obj,
            ).exists()
        return False

    class Meta(RecipeCreateUpdateSerializer.Meta):
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time',
            'is_favorited',
            'is_in_shopping_cart',
        )


class RecipeMiniFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class BaseSubscriptionSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source='author.email')
    id = serializers.ReadOnlyField(source='author.id')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    avatar = serializers.ReadOnlyField(source='author.avatar')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    def to_representation(self, subscription):
        representation = super().to_representation(subscription)
        avatar = representation.get('avatar', None)
        representation['avatar'] = avatar.url if avatar else None
        return representation

    def get_is_subscribed(self, obj):
        author = self.get_author(obj)
        subscriber = self.context.get('request').user
        if subscriber.is_authenticated:
            return Subscription.objects.filter(
                subscriber=subscriber.id,
                author=author.id,
            ).exists()
        return False

    def get_recipes(self, obj):
        author = self.get_author(obj)
        queryset = Recipe.objects.filter(author=author.id)
        recipes_limit = self.context['request'].query_params.get(
            'recipes_limit',
        )
        if recipes_limit:
            queryset = queryset[: int(recipes_limit)]
        serializer = RecipeMiniFieldSerializer(queryset, many=True)
        return serializer.data

    def get_recipes_count(self, obj):
        author = self.get_author(obj)
        return Recipe.objects.filter(author=author.id).count()

    def get_author(self, obj):
        try:
            author = obj.get('author')
        except AttributeError:
            author = obj.author
        return author

    class Meta:
        model = Subscription
        fields = '__all__'


class SubscriptionCreateSerializer(BaseSubscriptionSerializer):
    def validate(self, data):
        if self.context.get('request').user == data.get('author'):
            raise serializers.ValidationError(
                settings.ERROR_MESSAGES.get('self_subscribe'),
            )
        return data

    class Meta(BaseSubscriptionSerializer.Meta):
        fields = (
            'author',
            'subscriber',
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('author', 'subscriber'),
                message='Вы уже подписаны на этого пользователя',
            ),
        ]
        extra_kwargs = {
            'author': {'write_only': True},
            'subscriber': {'write_only': True},
        }


class SubscriptionListSerializer(BaseSubscriptionSerializer):
    class Meta(BaseSubscriptionSerializer.Meta):
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar',
        )
        read_only_fields = ('author', 'subscriber')


class ShoppingCartSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='recipe.id')
    name = serializers.ReadOnlyField(source='recipe.name')
    image = serializers.ReadOnlyField(source='recipe.image')
    cooking_time = serializers.ReadOnlyField(source='recipe.cooking_time')

    def to_representation(self, subscription):
        representation = super().to_representation(subscription)
        image = representation.get('image', None)
        representation['image'] = image.url if image else None
        return representation

    class Meta:
        model = ShoppingCart
        fields = (
            'customer',
            'recipe',
            'id',
            'name',
            'image',
            'cooking_time',
        )
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('customer', 'recipe'),
                message='Рецепт уже добавлен в список покупок',
            ),
        ]
        extra_kwargs = {
            'customer': {'write_only': True},
            'recipe': {'write_only': True},
        }


class FavoriteSerializer(ShoppingCartSerializer):
    class Meta(ShoppingCartSerializer.Meta):
        model = Favorite
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Favorite.objects.all(),
                fields=('customer', 'recipe'),
                message='Рецепт уже добавлен в избранное',
            ),
        ]
