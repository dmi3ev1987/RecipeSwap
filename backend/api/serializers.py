import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from recipes.models import (
    AmountOfIngredient,
    Ingredient,
    IngredientInRecipe,
    Recipe,
    Subscriptions,
    Tag,
    TagInRecipe,
)
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.validators import UniqueValidator

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

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

    # new code
    def get_is_subscribed(self, obj):
        current_user = self.context.get('request').user
        if current_user.is_authenticated:
            return Subscriptions.objects.filter(
                subscriber=current_user,
                author=obj,
            ).exists()
        return False


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


class UserMeSerializer(UserReadSerializer):
    class Meta(UserReadSerializer.Meta):
        pass

    def to_representation(self, instance):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return super().to_representation(instance)
        raise NotAuthenticated


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        help_text='Введите пароль',
        style={'input_type': 'password', 'placeholder': 'Пароль'},
    )
    email = serializers.EmailField(
        required=True,
        help_text='Введите адрес электронной почты',
        style={
            'input_type': 'email',
            'placeholder': 'Адрес электронной почты',
        },
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


class RecipeMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )


class TagsInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=False,
    )

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')
        read_only_fields = ('name', 'slug')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        many=False,
        source='ingredient.id',
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit',
    )

    class Meta:
        model = AmountOfIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeCreateSerializer(RecipeMetaSerializer):
    author = UserMeSerializer(read_only=True)
    image = Base64ImageField(required=True, allow_null=False)
    ingredients = IngredientInRecipeSerializer(many=True, required=True)
    tags = TagsInRecipeSerializer(many=True, required=True)

    def validate_ingredients(self, value):
        if not value:
            error = (
                'Ошибка ввода данных: поле ингредиентов не может быть пустым.'
            )
            raise serializers.ValidationError(error)
        validated_value = []
        for val in value:
            if val in validated_value:
                error = (
                    'Ошибка ввода данных: '
                    'ингредиенты не должны повторяться.'
                )
                raise serializers.ValidationError(error)
            validated_value.append(val)
        return value

    def validate_tags(self, value):
        if not value:
            error = 'Ошибка ввода данных: поле тегов не может быть пустым.'
            raise serializers.ValidationError(error)
        validated_value = []
        for val in value:
            if val in validated_value:
                error = 'Ошибка ввода данных: теги не должны повторяться.'
                raise serializers.ValidationError(error)
            validated_value.append(val)
        return value

    def to_internal_value(self, data):
        tags = data.get('tags', [])
        data['tags'] = [{'id': tag} for tag in tags]
        return super().to_internal_value(data)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        request = self.context.get('request')

        recipe = Recipe.objects.create(author=request.user, **validated_data)

        for tag in tags:
            current_tag, status = Tag.objects.get_or_create(id=tag['id'].pk)
            TagInRecipe.objects.create(
                tag=current_tag,
                recipe=recipe,
            )

        for ingredient in ingredients:
            current_ingredient, status = (
                AmountOfIngredient.objects.get_or_create(
                    ingredient=ingredient['ingredient']['id'],
                    amount=ingredient['amount'],
                )
            )
            IngredientInRecipe.objects.create(
                amount_of_ingredient=current_ingredient,
                recipe=recipe,
            )

        return recipe


class RecipeRetrieveSerializer(RecipeCreateSerializer):
    author = UserReadSerializer(read_only=True)


class RecipeUpdateSerializer(RecipeCreateSerializer):
    def update(self, instance, validated_data):
        instance.image = validated_data.get('image', instance.image)
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get('cooking_time')
        instance.save()

        user = self.context.get('request').user
        if user != instance.author:
            raise PermissionDenied

        ingredients = validated_data.get('ingredients', [])
        if not ingredients:
            error = (
                'Ошибка ввода данных: поле ингредиентов не может быть пустым.'
            )
            raise serializers.ValidationError(error)
        tags = validated_data.pop('tags')

        recipe = get_object_or_404(Recipe, pk=instance.pk)

        for tag in instance.tags.all():
            instance.tags.remove(tag)

        for tag in tags:
            current_tag, status = Tag.objects.get_or_create(id=tag['id'].pk)
            TagInRecipe.objects.update_or_create(
                tag=current_tag,
                recipe=recipe,
            )

        for ingredient in instance.ingredients.all():
            instance.ingredients.remove(ingredient)

        for ingredient in ingredients:
            current_ingredient, status = (
                AmountOfIngredient.objects.get_or_create(
                    ingredient=ingredient['ingredient']['id'],
                    amount=ingredient['amount'],
                )
            )
            IngredientInRecipe.objects.update_or_create(
                amount_of_ingredient=current_ingredient,
                recipe=recipe,
            )

        return instance


# new code from here

class SubscriptionSerializer(serializers.ModelSerializer):
    email = serializers.ReadOnlyField(source='author.email')
    id = serializers.ReadOnlyField(source='author.id')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    avatar = serializers.ReadOnlyField(source='author.avatar')

    def to_representation(self, subscription):
        representation = super().to_representation(subscription)
        avatar = representation.get('avatar', None)
        representation['avatar'] = avatar.url if avatar else None
        return representation


    def validate(self, data):
        if self.context['request'].user == data['author']:
            error = 'Нельзя подписаться на самого себя'
            raise serializers.ValidationError(error)
        return data

    class Meta:
        model = Subscriptions
        fields = (
            'author',
            'subscriber',
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
        )
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Subscriptions.objects.all(),
                fields=('author', 'subscriber'),
                message='Вы уже подписаны на этого пользователя',
            ),
        ]
        extra_kwargs = {
            'author': {'write_only': True},
            'subscriber': {'write_only': True},
        }
