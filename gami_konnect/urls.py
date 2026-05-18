"""
URL configuration for gami_konnect project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.gis import feeds
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Default admin route
    path('admin/', admin.site.urls),
    
    # Custom admin route
    path('management/', include('admin_panel.urls', namespace='admin_panel')),
    
    # Project Routes
    path('', include('core.urls')),
    path('games/', include('games.urls')),
    path('accounts/', include('accounts.urls')),
    path('shops/', include('shops.urls')),
    path('payments/',include('payments.urls')),
    path('competitions/', include('competitions.urls')),
    path('progression/', include('progression.urls')),
    path('feeds/', include('feeds.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


handler400 = 'core.views.error_400'
handler403 = 'core.views.error_403'
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'
