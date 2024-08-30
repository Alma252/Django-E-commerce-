from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.shortcuts import reverse
from django.utils import timezone
from django_countries.fields import CountryField


ADDRESS_CHOICES = (
    ('B', 'Billing'),
    ('S', 'Shipping'),
)


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100)
    apartment_address = models.CharField(max_length=100)
    country = CountryField(multiple=False)
    zip = models.CharField(max_length=100)
    address_type = models.CharField(max_length=1, choices=ADDRESS_CHOICES)
    default = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = 'Addresses'


class Category(models.Model):
    sub_category = models.ForeignKey('self', on_delete=models.CASCADE, related_name='scategory', null=True, blank=True)
    is_sub = models.BooleanField(default=False, blank=True, null=True)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='categories/', default='path/to/placeholder/image.jpg')  # اضافه کردن مقدار پیش‌فرض

    class Meta:
        ordering = ('name',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:category_filter', args=[self.slug, ])


class Item(models.Model):
    title = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    slug = models.SlugField(unique=True)
    stock_no = models.CharField(max_length=10)
    description = models.TextField()
    image = models.ImageField(null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("products:product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self):
        return reverse("products:add-to-cart", kwargs={
            'slug': self.slug
        })

    def get_remove_from_cart_url(self):
        return reverse("products:remove-from-cart", kwargs={
            'slug': self.slug
        })

    def get_add_to_list_url(self, list_type):
        return reverse("products:add_product_to_list", kwargs={
            'slug': self.slug,
            'list_type': list_type
        })

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    paid = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True)
    updated = models.DateTimeField(auto_now=True)
    discount = models.IntegerField(blank=True, null=True, default=None)

    class Meta:
        ordering = ('paid', '-updated')

    def __str__(self):
        return f'{self.user} - {str(self.id)}'

    def get_total_price(self):
        total = sum(item.get_cost() for item in self.items.all())
        if self.discount:
            discount_price = (self.discount / 100) * total
            return int(total - discount_price)
        return total


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Item, on_delete=models.CASCADE)
    price = models.IntegerField()
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    discount = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(90)])
    active = models.BooleanField(default=False)

    def __str__(self):
        return self.code


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    accepted = models.BooleanField(default=False)
    email = models.EmailField()

    def __str__(self):
        return f"{self.pk}"


class Payment(models.Model):
    zarinpal_authority = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    amount = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.name

class ProductReview(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='reviews')
    name = models.CharField(max_length=255, blank=True, null=True)  # فیلد جدید برای نام دلخواه
    rating = models.PositiveIntegerField()
    review_text = models.TextField(blank=True)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.name or self.user.email} - {self.product.title}'

    class Meta:
        ordering = ['-created_at']


class ListType(models.TextChoices):
    WISHLIST = 'WL', 'Wishlist'
    GIFT_LIST = 'GL', 'Gift List'
    SHOPPING_LIST = 'SL', 'Shopping List'
    CUSTOM = 'CL', 'Custom List'

class UserList(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lists')
    name = models.CharField('list name', max_length=255)
    list_type = models.CharField(
        'list type',
        max_length=2,
        choices=ListType.choices,
        default=ListType.CUSTOM
    )
    created_at = models.DateTimeField('created at', auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_list_type_display()}) - {self.user.email}"

class ListItem(models.Model):
    user_list = models.ForeignKey(UserList, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField('product name', max_length=255)
    quantity = models.PositiveIntegerField('quantity', default=1)
    added_at = models.DateTimeField('added at', auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} - {self.user_list.name}"


