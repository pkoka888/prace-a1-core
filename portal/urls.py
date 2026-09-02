from django.contrib.auth import views as auth_views
from django.urls import include, path

from portal.release1a.views import reviewer_activate

urlpatterns = [
    path("accounts/", include("allauth.urls")),
    path("accounts/activate/<str:token>/", reviewer_activate, name="reviewer_activate"),
    path("", include("portal.release1a.urls")),
    path("login/", auth_views.LoginView.as_view(template_name="portal/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]