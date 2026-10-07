from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import HealthProfile, Medication
from accounts.serializers import MedicationSerializer, ProfileSerializer, RegistrationSerializer


def error_response(code: str, message: str, status_code: int) -> Response:
    return Response({"error": {"code": code, "message": message}}, status=status_code)


@ensure_csrf_cookie
def csrf(_: HttpRequest) -> HttpResponse:
    return HttpResponse(status=204)


def profile_for(request: Request) -> HealthProfile:
    profile, _ = HealthProfile.objects.get_or_create(user=request.user)
    return profile


class RegisterView(APIView):
    def post(self, request: Request) -> Response:
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("VALIDATION_ERROR", "Please correct the highlighted fields.", 400)
        user = serializer.save()
        login(request, user)
        return Response(
            ProfileSerializer(profile_for(request)).data, status=status.HTTP_201_CREATED
        )


class LoginView(APIView):
    def post(self, request: Request) -> Response:
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=email, password=password)
        if user is None:
            return error_response("INVALID_CREDENTIALS", "Email or password is incorrect.", 400)
        login(request, user)
        return Response(ProfileSerializer(profile_for(request)).data)


class PrivateAPIView(APIView):
    def handle_exception(self, exc: Exception) -> Response:
        if isinstance(exc, NotAuthenticated):
            return error_response("NOT_AUTHENTICATED", "Sign in to continue.", 401)
        return super().handle_exception(exc)


class LogoutView(PrivateAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(PrivateAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        return Response(ProfileSerializer(profile_for(request)).data)

    def patch(self, request: Request) -> Response:
        serializer = ProfileSerializer(profile_for(request), data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("VALIDATION_ERROR", "Please correct the highlighted fields.", 400)
        serializer.save()
        return Response(serializer.data)


class MedicationsView(PrivateAPIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request) -> Response:
        medications = Medication.objects.filter(profile=profile_for(request)).order_by("name", "pk")
        return Response(MedicationSerializer(medications, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = MedicationSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("VALIDATION_ERROR", "Enter a medication name.", 400)
        medication = serializer.save(profile=profile_for(request))
        return Response(MedicationSerializer(medication).data, status=status.HTTP_201_CREATED)


class MedicationDetailView(PrivateAPIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request: Request, medication_id: int) -> Response:
        deleted, _ = Medication.objects.filter(
            pk=medication_id, profile=profile_for(request)
        ).delete()
        if not deleted:
            return error_response("NOT_FOUND", "Medication not found.", 404)
        return Response(status=status.HTTP_204_NO_CONTENT)
