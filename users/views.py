from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm

from .decorators import non_superuser_required
from .forms import AccountUpdateForm, RegistrationForm


def register_view(request):

    if request.method == 'POST':

        form = RegistrationForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            form.save()

            return redirect(
                'users:login'
            )

    else:

        form = RegistrationForm()


    return render(
        request,
        'register.html',
        {
            'form': form
        }
    )


def login_view(request):

    if request.method == 'POST':

        form = AuthenticationForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            user = form.get_user()

            login(
                request,
                user
            )

            return redirect(
                'product:home'
            )

    else:

        form = AuthenticationForm()


    return render(
        request,
        'login.html',
        {
            'form': form
        }
    )


def logout_view(request):

    logout(request)

    return redirect(
        'users:login'
    )


@non_superuser_required
def account_update(request):

    user = request.user


    if request.method == 'POST':

        form = AccountUpdateForm(
            request.POST,
            request.FILES,
            instance=user
        )


        if form.is_valid():

            user = form.save(
                commit=False
            )


            password1 = form.cleaned_data.get(
                'password1'
            )


            if password1:

                user.set_password(
                    password1
                )


            user.save()


            if password1:

                login(
                    request,
                    user
                )


            return redirect(
                'users:account:update'
            )

    else:

        form = AccountUpdateForm(
            instance=user
        )


    return render(
        request,
        'update.html',
        {
            'form': form
        }
    )