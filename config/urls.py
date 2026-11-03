
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Login page
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='inventory/login.html',
            redirect_authenticated_user=True
        ),
        name='login'
    ),

    # Logout
    path(
        'logout/',
        auth_views.LogoutView.as_view(),
        name='logout'
    ),

    # Inventory application
    path('', include('inventory.urls')),
]
