from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import re
def is_strong_password(password):
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$'
    return re.match(pattern, password)
def register(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confirm = request.POST['confirm']

        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        if not is_strong_password(password):
            messages.error(request, "Password must be 8+ chars with upper, lower, number & special")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(request, "Registered successfully. Please login.")
        return redirect('login')

    return render(request, 'register.html')
def user_login(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials")

    return render(request, 'login.html')
def user_logout(request):
    logout(request)
    return redirect('login')
@login_required(login_url='login')
def dashboard(request):
    return render(request, 'dashboard.html')
