from django.contrib import admin
from .models import (
    Category, Item, Order, OrderItem, Address, Coupon, Refund, Payment, ProductReview, UserList, ListItem
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_sub', 'slug']
    list_filter = ['is_sub']
    search_fields = ['name', 'slug']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['title', 'price', 'discount_price', 'category', 'slug', 'stock_no', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'description', 'slug', 'stock_no']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['user', 'paid', 'created', 'updated', 'discount']
    list_filter = ['paid', 'created', 'updated']
    search_fields = ['user__email']
    inlines = [OrderItemInline]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['user', 'street_address', 'apartment_address', 'country', 'zip', 'address_type', 'default']
    list_filter = ['address_type', 'default', 'country']
    search_fields = ['user__email', 'street_address', 'apartment_address', 'zip']


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'valid_from', 'valid_to', 'discount', 'active']
    list_filter = ['active', 'valid_from', 'valid_to']
    search_fields = ['code']


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['order', 'accepted', 'email']
    list_filter = ['accepted']
    search_fields = ['order__id', 'email']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'zarinpal_authority', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['user__email', 'zarinpal_authority']


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__email', 'product__title', 'review_text']


admin.site.register(UserList)
admin.site.register(ListItem)
