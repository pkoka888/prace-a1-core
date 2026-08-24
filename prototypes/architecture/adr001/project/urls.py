from django.http import HttpResponse
from django.urls import path

def health(_request): return HttpResponse("synthetic-proof-ok", content_type="text/plain")
urlpatterns = [path("health/", health)]

