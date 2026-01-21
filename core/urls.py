"""core URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from django.urls import include, path
from home import views as home_views

urlpatterns = [
    path('', include('home.urls')),
    path('accounts/auth-signin/', home_views.auth_signin, name='auth_signin'),
    path('accounts/auth-signup/', home_views.auth_signup, name='auth_signup'),
    path("admin/", admin.site.urls),
    path("", include('admin_black.urls')),
    path("__reload__/", include("django_browser_reload.urls"))
]
# Error Handlers
handler500 = 'home.views.server_error_500'