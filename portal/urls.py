from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from portal.release1a.views import reviewer_activate

urlpatterns = [
    path("accounts/", include("allauth.urls")),
    path("accounts/activate/<str:token>/", reviewer_activate, name="reviewer_activate"),
    path("", include("portal.release1a.urls")),
    path("login/", RedirectView.as_view(url="/accounts/login/", permanent=False), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]