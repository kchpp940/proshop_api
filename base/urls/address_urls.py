from django.urls import path
from base.views import address_views as views

urlpatterns = [
    path('user/', views.getUserAddresses, name='user-addresses'),
    path('add/', views.addAddress, name='address-add'),
    path('<str:pk>/', views.getUserAddressById, name='user-address'),
    path('<str:pk>/update/', views.updateAddress, name='address-update'),
    path('<str:pk>/delete/', views.deleteAddress, name='address-delete')
]
