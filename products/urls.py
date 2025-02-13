from django.urls import path, include

from .views import (
    CartView, CartAddView,
    OrderDetailView, OrderCreateView, OrderPayView,
    OrderVerifyView, CouponApplyView,
    CategoryDetailView,
    HomePageView, RequestRefundView,
    ProductDetailView, SearchResultsView, ReviewUpdateView,
    ReviewDeleteView, UserListsAndItemsView, UserListCreateView,
    UserListUpdateView, UserListDeleteView, account_view, BucketHome,
    ListItemCreateView, ListItemUpdateView, ListItemDeleteView, AddReviewView,
    CartRemoveView, deals_in_pcs, fashion, cars, DeleteBucketObject, DownloadBucketObject, cantact_view
)

app_name = 'products'

bucket_urls = [
    path('', BucketHome.as_view(), name='bucket'),
    path('delete_obj/<str:key>/', DeleteBucketObject.as_view(), name='delete_obj_bucket'),
    path('download_obj/<str:key>/', DownloadBucketObject.as_view(), name='download_obj_bucket'),
]

urlpatterns = [
    path('', HomePageView.as_view(), name='products'),
    path('category/<slug:category_slug>/', CategoryDetailView.as_view(), name='category_filter'),
    path('product/<slug:slug>/', ProductDetailView.as_view(), name='product'),
    path('search/', SearchResultsView.as_view(), name='search_results'),

    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/<int:product_id>/', CartAddView.as_view(), name='cart_add'),
    path('cart/remove/<int:product_id>/', CartRemoveView.as_view(), name='cart_remove'),

    path('order/<int:order_id>/', OrderDetailView.as_view(), name='order_detail'),
    path('order/create/', OrderCreateView.as_view(), name='order_create'),
    path('order/pay/<int:order_id>/', OrderPayView.as_view(), name='order_pay'),
    path('orders/verify/', OrderVerifyView.as_view(), name='order_verify'),
    path('order/<int:order_id>/apply_coupon/', CouponApplyView.as_view(), name='apply_coupon'),

    path('refund/', RequestRefundView.as_view(), name='request_refund'),

    path('user-lists/', UserListsAndItemsView.as_view(), name='user_lists'),
    path('user-lists/create/', UserListCreateView.as_view(), name='user_list_create'),
    path('user-lists/<int:pk>/update/', UserListUpdateView.as_view(), name='user_list_update'),
    path('user-lists/<int:pk>/delete/', UserListDeleteView.as_view(), name='user_list_delete'),
    path('user-lists/<int:user_list_id>/items/create/', ListItemCreateView.as_view(), name='list_item_create'),
    path('user-lists/items/<int:pk>/update/', ListItemUpdateView.as_view(), name='list_item_update'),
    path('user-lists/items/<int:pk>/delete/', ListItemDeleteView.as_view(), name='list_item_delete'),

    path('review/<int:pk>/update/', ReviewUpdateView.as_view(), name='review_update'),
    path('review/<int:pk>/delete/', ReviewDeleteView.as_view(), name='review_delete'),
    path('product/<slug:slug>/add_review/', AddReviewView.as_view(), name='add_review'),

    path('cart/remove_one/<int:product_id>/', CartRemoveView.as_view(), name='cart_remove_one'),

    path('account/', account_view, name='account_view'),
    path('deals-in-pcs/', deals_in_pcs, name='deals_in_pcs'),
    path('account/contact/', cantact_view, name='contact_view'),

    path('fashion/', fashion, name='fashion'),
    path('cars/', cars, name='cars'),
    path('bucket/', include(bucket_urls)),

]
