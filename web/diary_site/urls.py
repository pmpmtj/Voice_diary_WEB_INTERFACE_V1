from django.urls import path
from diary.views import home

urlpatterns = [
    path("", home, name="home"),
]


