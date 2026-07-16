from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard_estagiario, name='dashboard_estagiario'),
    path('supervisor/', views.dashboard_supervisor, name='dashboard_supervisor'),
    path('presencial/entrada/', views.presencial_entrada, name='presencial_entrada'),
    path('presencial/saida/<int:pk>/', views.presencial_saida, name='presencial_saida'),
    path('home-office/', views.home_office_registro, name='home_office_registro'),
    path('aprovar/<int:pk>/', views.aprovar_registro, name='aprovar_registro'),
    path('rejeitar/<int:pk>/', views.rejeitar_registro, name='rejeitar_registro'),
    path('historico/', views.historico, name='historico'),
    path('relatorios/', views.relatorios, name='relatorios'),
]
