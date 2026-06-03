from django.urls import path
from base.views import order_views as views

urlpatterns = [
    path('', views.getOrders, name='orders'),
    path('add/', views.addOrderItems, name='orders-add'),
    path('user-orders/', views.getUserOrders, name='user-orders'),
    path('<str:pk>/', views.getOrderById, name='user-order'),
    path('<str:pk>/pay/', views.updateOrderToPaid, name='order-pay'),
    path('<str:pk>/deliver/', views.updateOrderToDelivered, name='order-deliver'),
    path('<str:pk>/ship/', views.updateOrderToShipped, name='order-ship'),
    path('<str:pk>/cancel/', views.updateOrderToCancelled, name='order-cancel'),
    path('<str:pk>/refund/', views.updateOrderToRefunded, name='order-refund'),
]
