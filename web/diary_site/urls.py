from django.urls import path, include
from diary.views import home, execute, execute_script, delete_item_view

urlpatterns = [
    path("", home, name="home"),
    path("execute/", execute, name="execute"),
    path("api/execute/", execute_script, name="execute_script"),
    path("api/delete/<uuid:item_id>/", delete_item_view, name="delete_item"),
    path("accounts/", include("accounts.urls")),
]


