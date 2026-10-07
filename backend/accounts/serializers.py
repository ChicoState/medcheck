from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from accounts.models import HealthProfile, Medication, User


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return User.objects.normalize_email(value)

    def validate_password(self, value: str) -> str:
        try:
            validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error
        return value

    def create(self, validated_data: dict[str, str]) -> User:
        return User.objects.create_user(**validated_data)


class ProfileSerializer(serializers.ModelSerializer[HealthProfile]):
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = HealthProfile
        fields = ("email", "date_of_birth", "gender")


class MedicationSerializer(serializers.ModelSerializer[Medication]):
    class Meta:
        model = Medication
        fields = ("id", "name")
        read_only_fields = ("id",)

    def validate_name(self, value: str) -> str:
        name = value.strip()
        if not name:
            raise serializers.ValidationError("Enter a medication name.")
        return name
