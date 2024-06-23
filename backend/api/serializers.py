import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from recipes.models import Ingredient, IngredientInRecipe, Recipe, Tag
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated
from rest_framework.validators import UniqueValidator

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
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


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UserAvatarSerializer(UserSerializer):
    avatar = Base64ImageField(required=True, allow_null=False)

    class Meta:
        model = User
        fields = ('avatar',)


class UserMeSerializer(UserSerializer):
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

    def to_representation(self, instance):
        request = self.context.get('request')
        if request.user.is_authenticated:
            return super().to_representation(instance)
        raise NotAuthenticated


class CreateUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        help_text='Leave empty if no change needed',
        style={'input_type': 'password', 'placeholder': 'Password'},
    )
    email = serializers.EmailField(
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
        fields = '__all__'
        model = Ingredient


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Tag

####################################
######## new code from here ########
####################################

class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class RecipeMetaSerializer(serializers.ModelSerializer):
    class Meta:
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
        model = Recipe


class RecipeRetrieveSerializer(RecipeMetaSerializer):
    pass


class AuthorSerializer(UserMeSerializer):
    username = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault(),
    )


class RecipeCreateSerializer(RecipeMetaSerializer):
    author = AuthorSerializer(read_only=True)
    image = Base64ImageField(required=True, allow_null=False)
    ingredients = IngredientInRecipeSerializer(many=True, required=True)


    def create(self, validated_data):
        # Уберём список достижений из словаря validated_data и сохраним его
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        # author = validated_data.pop('author')
        request = self.context.get('request')

        # Создадим нового котика пока без достижений, данных нам достаточно
        recipe = Recipe.objects.create(author=request.user, **validated_data)
        # recipe = Recipe.objects.create(**validated_data)
        # recipe.author = self.request.user
        recipe.save()
        # ingredient = Ingredient.objects.filter(pk=ingredients[0].get('id'))

        # Для каждого достижения из списка достижений
        # for ingredient in ingredients:
        #     # Создадим новую запись или получим существующий экземпляр из БД
        #     # current_ingredient, status = IngredientInRecipe.objects.get_or_create(
        #     #     **ingredient,
        #     # )
        #     # Поместим ссылку на каждое достижение во вспомогательную таблицу
        #     # Не забыв указать к какому котику оно относится
        #     IngredientInRecipe.objects.create(
        #         amount=current_ingredient, recipe=recipe,
        #     )
        return recipe


class RecipeUpdateSerializer(RecipeCreateSerializer):
    image = Base64ImageField(required=False, allow_null=False)
