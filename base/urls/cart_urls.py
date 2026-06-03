from django.urls import path
from base.views import cart_views as views

urlpatterns = [
    path('', views.getCart, name='cart'),
    path('add/', views.addToCart, name='cart-add'),
    path('totals/', views.getCartTotals, name='cart-totals'),
    path('clear/', views.clearCart, name='cart-clear'),
    path('<str:pk>/update/', views.updateCartItem, name='cart-item-update'),
    path('<str:pk>/remove/', views.removeFromCart, name='cart-item-remove'),
]
