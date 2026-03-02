"""pms URL Configuration"""
from django.urls import path, include
from pmsapp import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('captcha/', views.captcha_view, name='captcha'),
    path('', include('pmsapp.urls')),
]
