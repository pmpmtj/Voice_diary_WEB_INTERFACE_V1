from django.urls import path, include
from diary.views import home, execute, execute_script

urlpatterns = [
    path("", home, name="home"),
    path("execute/", execute, name="execute"),
    path("api/execute/", execute_script, name="execute_script"),
    path("accounts/", include("accounts.urls")),
]


