from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm

from .forms import RegistrationForm


def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            form.save()
            return redirect('users:login')

    else:
        form = RegistrationForm()

    return render(
        request,
        'users/register.html',
        {'form': form}
    )


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            return redirect('home')

    else:
        form = AuthenticationForm()

    return render(
        request,
        'users/login.html',
        {'form': form}
    )


def logout_view(request):
    logout(request)
    return redirect('home')