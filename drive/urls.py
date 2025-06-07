from re import I
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("folder/<str:pk>/", views.folder, name="folder")
]
