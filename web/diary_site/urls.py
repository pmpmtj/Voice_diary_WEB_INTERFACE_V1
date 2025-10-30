from django.urls import path, include
from diary.views import home, dashboard, manage, execute, execute_script, delete_item_view

urlpatterns = [
    path("", home, name="home"),
    path("dashboard/", dashboard, name="dashboard"),
    path("manage/", manage, name="manage"),
    path("execute/", execute, name="execute"),
    path("api/execute/", execute_script, name="execute_script"),
    path("api/delete/<uuid:item_id>/", delete_item_view, name="delete_item"),
    path("accounts/", include("accounts.urls")),
]


