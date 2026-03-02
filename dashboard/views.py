from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def index(request):
    from users.models import UserProfile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'dashboard/index.html', {'profile': profile})
