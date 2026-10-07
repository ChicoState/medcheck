from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager["User"]):
    """Create accounts whose email is their login identifier."""

    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra_fields: object) -> "User":
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: object) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Account identified by a unique email address."""

    username = None
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []
    objects = UserManager()


class HealthProfile(models.Model):
    """Optional sensitive information kept separate from account credentials."""

    objects = models.Manager["HealthProfile"]()

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="health_profile",
    )
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(blank=True, max_length=100)


class Medication(models.Model):
    """A medication named by the profile owner without clinical interpretation."""

    objects = models.Manager["Medication"]()

    profile = models.ForeignKey(
        HealthProfile,
        on_delete=models.CASCADE,
        related_name="medications",
    )
    name = models.CharField(max_length=255)
