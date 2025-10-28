"""
URL configuration for button_server project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('app.urls')),
]
