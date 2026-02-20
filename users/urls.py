from django.urls import path
from django.contrib.auth import views as auth_views
from users import views as user_views
from dashboard import views as dashboard_views

urlpatterns = [
    path('register/', user_views.register, name='register'),
    path('login/', user_views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('profile/', user_views.profile, name='profile'),
]
