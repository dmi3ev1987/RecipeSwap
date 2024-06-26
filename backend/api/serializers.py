import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from recipes.models import (
    AmountOfIngredient,
    Ingredient,
    IngredientInRecipe,
    Recipe,
    Tag,
    TagInRecipe,
)
from rest_framework import serializers
from rest_framework.exceptions import NotAuthenticated
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


#####################################
# ####### new code from here ########
#####################################


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
    tags = TagsInRecipeSerializer(many=True)

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError
        return value

    def to_internal_value(self, data):
        tags = data.pop('tags')
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

        ingredients = validated_data.pop('ingredients')
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
