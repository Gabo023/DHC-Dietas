from django.urls import path
from .views import user_login, user_logout, dashboard, lista_pacientes, crear_paciente, actualizar_paciente, eliminar_paciente, buscar_pacientes, lista_dietas, crear_dieta, editar_dieta
from django.contrib.auth.views import PasswordChangeView
from .views import obtener_opciones_dieta
from .views import crear_dieta, detalle_dieta, editar_detalle_dieta
from . import views
from .views import editar_dieta
from django.contrib import admin
from django.urls import path


urlpatterns = [
    # Autenticación
    path('login/', user_login, name='login'),
    path('logout/', user_logout, name='logout'),
    path('cambiar-clave/', views.cambiar_clave, name='cambiar_clave'),
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),

    # Dashboard
    #path('dashboard/', dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Pacientes
    path('', views.lista_pacientes, name='lista_pacientes'),
    path('crear/', views.crear_paciente, name='crear_paciente'),
    path('editar/<int:pk>/', actualizar_paciente, name='actualizar_paciente'),
    path('eliminar/<int:pk>/', eliminar_paciente, name='eliminar_paciente'),
    path('buscar_pacientes/', views.buscar_pacientes, name='buscar_pacientes'),

    # Dietas y Detalle dietas
    path('dietas/', views.lista_dietas, name='lista_dietas'),
    path('dietas/crear/<int:paciente_id>/', views.crear_dieta, name='crear_dieta'),
    path('dietas/editar/<int:pk>/', views.editar_dieta, name='editar_dieta'),
    path('dietas/eliminar/<int:pk>/', views.eliminar_dieta, name='eliminar_dieta'), # Nueva URL para eliminar
    path('dietas/detalle/<int:dieta_id>/', views.detalle_dieta, name='detalle_dieta'),
    path('dietas/detalle/editar/<int:detalle_id>/', views.editar_detalle_dieta, name='editar_detalle_dieta'),
    path('dietas/detalle/eliminar/<int:detalle_id>/', views.eliminar_detalle_dieta, name='eliminar_detalle_dieta'),
    path('obtener_opciones_dieta/', views.obtener_opciones_dieta, name='obtener_opciones_dieta'),

    #Reporteria
    path('reporte-excel/', views.generar_reporte_excel, name='generar_reporte_excel'),


    # Otras URLs...
]
