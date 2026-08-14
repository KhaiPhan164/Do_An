from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
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

]