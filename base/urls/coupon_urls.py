from django.urls import path
from base.views import coupon_views as views

urlpatterns = [
    path('', views.getCoupons, name='coupons'),
    path('validate/', views.validateCoupon, name='coupon-validate'),
    path('<str:pk>/', views.getCouponById, name='coupon'),
    path('create/', views.createCoupon, name='coupon-create'),
    path('<str:pk>/update/', views.updateCoupon, name='coupon-update'),
    path('<str:pk>/delete/', views.deleteCoupon, name='coupon-delete'),
]
