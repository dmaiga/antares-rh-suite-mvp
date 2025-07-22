"""
URL configuration for antares_rh project.

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
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static

import authentication.views
import documents.views
import notes.views
import todo.views
import statics.views
import site_web.views
urlpatterns = [
    path('admin/', admin.site.urls),
    path('',site_web.views.home,name='home'),
    path('auth/login', authentication.views.login_page, name='login'),
    path('auth/', include('authentication.urls')),
    path('documents/', include('documents.urls')),
    path('logs/', include('logs.urls')),
    path('notes/', include('notes.urls')),
    path('todo/', include('todo.urls')),
    path('statics/', include('statics.urls')),
    path('antares-rh/', include('site_web.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)