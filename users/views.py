from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from .models import UserProfile
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm

def register(request): 
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'Account created for {user.username}! You can now log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    profile_instance, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile_instance)
        
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'There was an error updating your profile.')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile_instance)

    context = {
        'u_form': u_form,
        'p_form': p_form,
        'profile': profile_instance
    }
    return render(request, 'users/profile.html', context)

def login_view(request):
   
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
           
            if not hasattr(user, 'userprofile'):
                UserProfile.objects.create(user=user)
            auth_login(request, user)
            return redirect('dashboard')
        else:
            username = request.POST.get('username')
            if username and not User.objects.filter(username=username).exists():
                messages.error(request, "You are a new user to this, so please register.")
                return redirect('register')
            else:
                messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})
@login_required
def update_reminder(request):
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        enabled = data.get('enabled')
        time_str = data.get('time')
        
        profile = request.user.userprofile
        profile.reminder_enabled = enabled
        if time_str:
            profile.reminder_time = time_str
        profile.save()
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)
