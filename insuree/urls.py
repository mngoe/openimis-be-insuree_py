from django.urls import path
from . import views


urlpatterns = [
    path("register/answer", views.register_answer , name="register_answer")
]