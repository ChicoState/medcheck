from django.urls import path

from . import views

medication_patterns = [
    path("", views.search, name="medication-search"),
    path("interactions/check/", views.interaction_check, name="medication-interaction-check"),
    path("<str:provider>/<uuid:external_id>/", views.detail, name="medication-detail"),
]

saved_patterns = [
    path("", views.saved_collection, name="saved-medication-collection"),
    path("<int:saved_id>/", views.saved_item, name="saved-medication-item"),
]
