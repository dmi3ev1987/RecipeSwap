from django.contrib.auth import get_user_model
from recipes.models import Ingredient, Tag
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


class UserMeSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = ('email', 'first_name', 'last_name')

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
