from django.urls import path
from . import views

app_name = 'product'

urlpatterns = [
    path('', views.home, name='home'),

    path('account/my-product/', views.my_product, name='my_product'),
    path('account/add-product/', views.add_product, name='add_product'),
    path('account/edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('account/delete-product/<int:product_id>/', views.delete_product, name='delete_product'),

    path('product/<int:id>/', views.product_detail, name='product_detail'),

    path('search/', views.search_product, name='search_product'),
    path('search-advanced/', views.search_advanced, name='search_advanced'),
    path('search-price/', views.search_price, name='search_price'),

    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/delete/', views.delete_cart_item, name='delete_cart_item'),

    path('checkout/', views.checkout, name='checkout'),
]
