from django.urls import path
from . import views

urlpatterns = [
    path('models/available', views.available_models, name='available-models'),
] 