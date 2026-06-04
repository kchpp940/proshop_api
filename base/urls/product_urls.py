from django.urls import path
from base.views import product_views as views

urlpatterns = [
    path('', views.getProducts, name='products'),
    path('create/', views.createProduct, name='product-create'),
    path('upload/', views.uploadImage, name='upload-image'),
    path('top/', views.getTopRatedProducts, name='top-products'),
    path('user/reviews/', views.getUserReviews, name='user-reviews'),
    path('category/<str:slug>/', views.getProductsByCategory,
         name='category-products'),
    path('subcategory/<str:slug>/', views.getProductsBySubCategory,
         name='subcategory-products'),
    path('<str:pk>/', views.getProduct, name='product'),
    path('<str:pk>/incClicks/', views.incrementClickCount,
         name='product-inc-clicks'),
    path('<str:pk>/reviews/', views.createProductReview, name='create-review'),
    path('<str:pk>/update/', views.updateProduct, name='product-update'),
    path('<str:pk>/delete/', views.deleteProduct, name='product-delete'),
]
