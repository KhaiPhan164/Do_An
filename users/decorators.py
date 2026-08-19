from django.contrib.auth.decorators import user_passes_test, login_required

def non_superuser_required(view_func):
    actual_decorator = user_passes_test(
        lambda u:u.is_authenticated and not u.is_superuser
    )

    return login_required(actual_decorator(view_func))