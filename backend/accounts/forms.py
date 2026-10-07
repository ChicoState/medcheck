"""Account input validation and registration using Django's model constraints."""

from django import forms
from django.contrib.auth.forms import UsernameField
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction


class CredentialsForm(forms.Form):
    username = UsernameField(max_length=150)
    password = forms.CharField(max_length=1024, strip=False)


class RegistrationForm(CredentialsForm):
    def clean_username(self):
        username = self.cleaned_data["username"]
        user = User(username=username)
        try:
            user.full_clean(exclude=["password", "email"])
        except ValidationError as error:
            raise ValidationError(error.messages) from error
        return user.username

    def clean(self):
        data = super().clean()
        if data and "username" in data and "password" in data:
            try:
                validate_password(data["password"], User(username=data["username"]))
            except ValidationError as error:
                self.add_error("password", error)
        return data

    def save(self):
        try:
            # Django exposes atomic as both decorator and context manager.
            with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
                return User.objects.create_user(
                    username=self.cleaned_data["username"], password=self.cleaned_data["password"]
                )
        except IntegrityError:
            # A competing registration may have claimed the username after validation.
            if not User.objects.filter(username=self.cleaned_data["username"]).exists():
                raise
            self.add_error("username", "A user with that username already exists.")
            return None
