from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    #path('admin/', admin.site.urls),
    #path('accounts/', include('accounts.urls')),

    path('admin/', admin.site.urls),
    path('', include('accounts.urls')), # Incluye las URLs de tu aplicación principal
    path('accounts/', include('accounts.urls')), # Si tienes una aplicación de cuentas separada
    
]