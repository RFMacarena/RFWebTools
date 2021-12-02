from django.urls import path
from . import views


urlpatterns = [
    path('winstonlutztest', views.winstonlutztest, name='winstonlutztest'),
]