from django.urls import path
from . import views


urlpatterns = [
    path('winstonlutztest', views.winstonlutztest, name='winstonlutztest'),
    path('bb_report/download_file/<fname>', views.download_file),
]