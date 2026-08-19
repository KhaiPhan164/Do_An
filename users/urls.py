from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


app_name = 'users'


urlpatterns = [

    path(
        '',
        views.home,
        name='home'
    ),

    path(
        'register/',
        views.register_view,
        name='register'
    ),

    path(
        'login/',
        views.login_view,
        name='login'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),


    path(
        'account/update/',
        views.account_update,
        name='account_update'
    ),

    path(
        'account/my-product/',
        views.my_product,
        name='my_product'
    ),

    path(
        'account/add-product/',
        views.add_product,
        name='add_product'
    ),

    path(
        'account/edit-product/<int:product_id>/',
        views.edit_product,
        name='edit_product'
    ),

    path(
        'account/delete-product/<int:product_id>/',
        views.delete_product,
        name='delete_product'
    ),


    path(
        'product/<int:id>/',
        views.product_detail,
        name='product_detail'
    ),


    path(
        'search/',
        views.search_product,
        name='search_product'
    ),

    path(
        'search-advanced/',
        views.search_advanced,
        name='search_advanced'
    ),

    path(
        'search-price/',
        views.search_price,
        name='search_price'
    ),


    path(
        'forgot-password/',
        auth_views.PasswordResetView.as_view(
            template_name='users/password_reset_form.html',
            email_template_name='users/password_reset_email.html',
            subject_template_name='users/password_reset_subject.txt',
            success_url='/users/password-reset-done/'
        ),
        name='password_reset'
    ),

    path(
        'password-reset-done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='users/password_reset_done.html'
        ),
        name='password_reset_done'
    ),

    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='users/password_reset_confirm.html',
            success_url='/users/password-reset-complete/'
        ),
        name='password_reset_confirm'
    ),

    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='users/password_reset_complete.html'
        ),
        name='password_reset_complete'
    ),


    path(
        'cart/',
        views.cart_view,
        name='cart'
    ),

    path(
        'cart/add/',
        views.add_to_cart,
        name='add_to_cart'
    ),

    path(
        'cart/update/',
        views.update_cart,
        name='update_cart'
    ),

    path(
        'cart/delete/',
        views.delete_cart_item,
        name='delete_cart_item'
    ),


    path(
        'checkout/',
        views.checkout,
        name='checkout'
    ),

]