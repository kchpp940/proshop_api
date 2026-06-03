from django.urls import path
from base.views import wishlist_views as views

urlpatterns = [
    path('', views.get_user_wishlist, name='user-wishlist'),
    path('<str:pk>/add/', views.add_to_wishlist, name='add-to-wishlist'),
    path('<str:pk>/remove/', views.remove_from_wishlist, name='remove-from-wishlist'),
]
