from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DeleteView, View, CreateView, UpdateView

from . import tasks
from .forms import RefundForm, CartAddForm, CouponApplyForm, ProductReviewForm, SearchForm, ListItemForm, UserListForm, \
    CheckoutForm
from .models import Item, OrderItem, Order, Address, Payment, Coupon, Refund, Category, ProductReview, UserList, \
    ListItem
import datetime
import json
import requests
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.postgres.search import SearchVector, TrigramSimilarity

from utils import IsAdminUserMixin

CART_SESSION_ID = 'cart'


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if not cart:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def __iter__(self):
        product_ids = self.cart.keys()
        products = Item.objects.filter(id__in=product_ids)
        cart = self.cart.copy()
        for product in products:
            cart[str(product.id)]['product'] = product

        for item in cart.values():
            item['total_price'] = float(item['price']) * item['quantity']
            yield item

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def add(self, product, quantity):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {'quantity': 0, 'price': float(product.price)}
        self.cart[product_id]['quantity'] += quantity
        self.save()

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def save(self):
        self.session.modified = True

    def get_total_price(self):
        return sum(float(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        del self.session[CART_SESSION_ID]
        self.save()


class CartView(View):
    def get(self, request):
        cart = Cart(request)
        return render(request, 'products/cart.html', {'cart': cart})


class CartAddView(PermissionRequiredMixin, View):
    permission_required = 'products.add_order'

    def post(self, request, product_id):
        cart = Cart(request)
        product = get_object_or_404(Item, id=product_id)
        form = CartAddForm(request.POST)
        if form.is_valid():
            cart.add(product, form.cleaned_data['quantity'])
        return redirect('products:cart')


class CartRemoveView(View):
    def get(self, request, product_id):
        cart = Cart(request)
        product = get_object_or_404(Item, id=product_id)
        cart.remove(product)
        return redirect('products:cart')


class OrderDetailView(LoginRequiredMixin, View):
    form_class = CouponApplyForm

    def get(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        return render(request, 'products/order.html', {'order': order, 'form': self.form_class})


class OrderCreateView(LoginRequiredMixin, View):
    def get(self, request):
        cart = Cart(request)
        order = Order.objects.create(user=request.user)
        for item in cart:
            OrderItem.objects.create(order=order, product=item['product'], price=item['price'],
                                     quantity=item['quantity'])
        cart.clear()
        return redirect('products:order_detail', order.id)


MERCHANT = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXX'
ZP_API_REQUEST = "https://api.zarinpal.com/pg/v4/payment/request.json"
ZP_API_VERIFY = "https://api.zarinpal.com/pg/v4/payment/verify.json"
ZP_API_STARTPAY = "https://www.zarinpal.com/pg/StartPay/{authority}"
description = "توضیحات مربوط به تراکنش را در این قسمت وارد کنید"
CallbackURL = 'http://127.0.0.1:8000/orders/verify/'


class OrderPayView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = Order.objects.get(id=order_id)
        request.session['order_pay'] = {
            'order_id': order.id,
        }
        req_data = {
            "merchant_id": MERCHANT,
            "amount": order.get_total_price(),
            "callback_url": CallbackURL,
            "description": description,
            "metadata": {
                "mobile": getattr(request.user, 'phone_number', ''),  # استفاده از getattr برای اجتناب از خطا
                "email": request.user.email
            }
        }
        req_header = {
            "accept": "application/json",
            "content-type": "application/json"
        }
        req = requests.post(url=ZP_API_REQUEST, data=json.dumps(req_data), headers=req_header)
        resp_json = req.json()

        if 'errors' not in resp_json or len(resp_json['errors']) == 0:
            authority = resp_json['data']['authority']
            Payment.objects.create(
                user=request.user,
                amount=order.get_total_price(),
                authority=authority,
            )
            return redirect(ZP_API_STARTPAY.format(authority=authority))
        else:
            e_code = resp_json['errors']['code']
            e_message = resp_json['errors']['message']
            return HttpResponse(f"Error code: {e_code}, Error Message: {e_message}")


class OrderVerifyView(LoginRequiredMixin, View):
    def get(self, request):
        order_id = request.session['order_pay']['order_id']
        order = Order.objects.get(id=int(order_id))
        t_status = request.GET.get('Status')
        t_authority = request.GET.get('Authority')
        payment = Payment.objects.get(authority=t_authority)

        if t_status == 'OK':
            req_header = {
                "accept": "application/json",
                "content-type": "application/json"
            }
            req_data = {
                "merchant_id": MERCHANT,
                "amount": order.get_total_price(),
                "authority": t_authority
            }
            req = requests.post(url=ZP_API_VERIFY, data=json.dumps(req_data), headers=req_header)
            resp_json = req.json()

            if 'errors' not in resp_json or len(resp_json['errors']) == 0:
                t_status = resp_json['data']['code']
                if t_status == 100:
                    payment.paid = True
                    payment.ref_id = resp_json['data']['ref_id']
                    payment.save()
                    order.paid = True
                    order.save()
                    return HttpResponse('Transaction success.\nRefID: ' + str(resp_json['data']['ref_id']))
                elif t_status == 101:
                    return HttpResponse('Transaction submitted : ' + str(resp_json['data']['message']))
                else:
                    return HttpResponse('Transaction failed.\nStatus: ' + str(resp_json['data']['message']))
            else:
                e_code = resp_json['errors']['code']
                e_message = resp_json['errors']['message']
                return HttpResponse(f"Error code: {e_code}, Error Message: {e_message}")
        else:
            return HttpResponse('Transaction failed or canceled by user')


class CouponApplyView(LoginRequiredMixin, View):
    form_class = CouponApplyForm

    def post(self, request, order_id):
        now = datetime.datetime.now()
        form = self.form_class(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            try:
                coupon = Coupon.objects.get(code__exact=code, valid_from__lte=now, valid_to__gte=now, active=True)
            except Coupon.DoesNotExist:
                messages.error(request, 'this coupon does not exists', 'danger')
                return redirect('orders:order_detail', order_id)
            order = Order.objects.get(id=order_id)
            order.discount = coupon.discount
            order.save()
        return redirect('orders:order_detail')


class HomePageView(View):
    def get(self, request):
        categories = Category.objects.filter(is_sub=False)
        return render(request, 'products/index.html', {'categories': categories})


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received")
                return redirect("products:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist")
                return redirect("products:request-refund")


class CategoryDetailView(View):
    def get(self, request, category_slug):
        category = get_object_or_404(Category, slug=category_slug)
        items = Item.objects.filter(category=category, is_active=True)

        paginator = Paginator(items, 10)
        page = request.GET.get('page')
        try:
            items = paginator.page(page)
        except PageNotAnInteger:
            items = paginator.page(1)
        except EmptyPage:
            items = paginator.page(paginator.num_pages)

        return render(request, 'products/category_detail.html', {'category': category, 'items': items})


class ProductDetailView(View):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.product = get_object_or_404(Item, slug=kwargs['slug'])
        self.reviews = self.product.reviews.filter(parent=None)
        self.cart_form = CartAddForm(request.POST or None)
        self.review_form = ProductReviewForm(request.POST or None)

        self.user_lists = UserList.objects.filter(user=request.user)

    def get(self, request, slug):
        return render(request, 'products/product_detail.html', {
            'product': self.product,
            'reviews': self.reviews,
            'cart_form': self.cart_form,
            'review_form': self.review_form,
            'user_lists': self.user_lists
        })

    def post(self, request, slug):
        if 'add_to_cart' in request.POST and self.cart_form.is_valid():
            cart, created = Cart.objects.get_or_create(user=request.user, active=True)
            cart.add_product(self.product, quantity=self.cart_form.cleaned_data['quantity'])
            messages.success(request, 'Product added to cart.')
            return redirect('products:product', slug=slug)

        if 'add_to_list' in request.POST:
            list_type = request.POST.get('list_type')

            user_list, created = UserList.objects.get_or_create(user=request.user, list_type=list_type)
            if ListItem.objects.filter(user_list=user_list, product_name=self.product.title).exists():
                messages.info(request, "This item is already in your list.")
            else:
                ListItem.objects.create(user_list=user_list, product_name=self.product.title)
                messages.success(request, "Item added to your list.")
            return redirect('products:product', slug=slug)

        if 'submit_review' in request.POST and self.review_form.is_valid():
            review = self.review_form.save(commit=False)
            review.user = request.user
            review.product = self.product

            parent_id = request.POST.get('parent')
            if parent_id:
                parent_review = ProductReview.objects.get(id=parent_id)
                review.parent = parent_review

            review.save()
            messages.success(request, 'Review submitted successfully.')
            return redirect('products:product', slug=slug)

        return render(request, 'products/product_detail.html', {
            'product': self.product,
            'reviews': self.reviews,
            'cart_form': self.cart_form,
            'review_form': self.review_form,
            'user_lists': self.user_lists
        })


class SearchResultsView(View):
    def get(self, request):
        form = SearchForm()
        query = request.GET.get('query')
        results = []
        if query:
            search_vector = SearchVector('title', 'description')
            search_similarity = TrigramSimilarity('title', query)
            results = Item.objects.annotate(
                search=search_vector,
                similarity=search_similarity
            ).filter(Q(search=query) | Q(similarity__gte=0.3)).order_by('-similarity')

            paginator = Paginator(results, 10)
            page = request.GET.get('page')
            try:
                results = paginator.page(page)
            except PageNotAnInteger:
                results = paginator.page(1)
            except EmptyPage:
                results = paginator.page(paginator.num_pages)

        return render(request, 'products/search_results.html', {
            'form': form,
            'query': query,
            'results': results
        })


class ReviewUpdateView(UpdateView):
    model = ProductReview
    form_class = ProductReviewForm
    template_name = 'review_form.html'

    def get_queryset(self):
        return ProductReview.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('product_detail', kwargs={'slug': self.object.product.slug})


class ReviewDeleteView(DeleteView):
    model = ProductReview
    template_name = 'review_confirm_delete.html'

    def get_queryset(self):
        return ProductReview.objects.filter(user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('product_detail', kwargs={'slug': self.object.product.slug})


class UserListsAndItemsView(LoginRequiredMixin, ListView):
    model = UserList
    template_name = 'products/list.html'
    context_object_name = 'user_lists'

    def get_queryset(self):
        return UserList.objects.filter(user=self.request.user).prefetch_related('items')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lists_with_items'] = [
            {
                'user_list': user_list,
                'items': user_list.items.all(),
            } for user_list in context['user_lists']
        ]
        return context


class UserListCreateView(LoginRequiredMixin, CreateView):
    model = UserList
    form_class = UserListForm
    template_name = 'products/user_list_form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class UserListUpdateView(LoginRequiredMixin, UpdateView):
    model = UserList
    form_class = UserListForm
    template_name = 'products/user_list_form.html'
    success_url = reverse_lazy('user_list')

    def get_queryset(self):
        return UserList.objects.filter(user=self.request.user)


class UserListDeleteView(LoginRequiredMixin, DeleteView):
    model = UserList
    template_name = 'products/user_list_confirm_delete.html'
    success_url = reverse_lazy('user_list')

    def get_queryset(self):
        return UserList.objects.filter(user=self.request.user)


class ListItemListView(LoginRequiredMixin, ListView):
    model = ListItem
    template_name = 'products/list_item_list.html'

    def get_queryset(self):
        user_list_id = self.kwargs.get('user_list_id')
        return ListItem.objects.filter(user_list__id=user_list_id, user_list__user=self.request.user)


class ListItemCreateView(LoginRequiredMixin, CreateView):
    model = ListItem
    form_class = ListItemForm
    template_name = 'products/list_item_form.html'
    success_url = reverse_lazy('list_item_list')

    def form_valid(self, form):
        user_list_id = self.kwargs.get('user_list_id')
        form.instance.user_list_id = user_list_id
        return super().form_valid(form)


class ListItemUpdateView(LoginRequiredMixin, UpdateView):
    model = ListItem
    form_class = ListItemForm
    template_name = 'products/list_item_form.html'
    success_url = reverse_lazy('list_item_list')

    def get_queryset(self):
        user_list_id = self.kwargs.get('user_list_id')
        return ListItem.objects.filter(user_list__id=user_list_id, user_list__user=self.request.user)


class ListItemDeleteView(LoginRequiredMixin, DeleteView):
    model = ListItem
    template_name = 'products/list_item_confirm_delete.html'
    success_url = reverse_lazy('list_item_list')

    def get_queryset(self):
        user_list_id = self.kwargs.get('user_list_id')
        return ListItem.objects.filter(user_list__id=user_list_id, user_list__user=self.request.user)


class AddReviewView(LoginRequiredMixin, View):
    def post(self, request, slug):
        product = get_object_or_404(Item, slug=slug)
        form = ProductReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.user = request.user
            review.save()
            return redirect('products:product', slug=slug)
        return redirect('products:product', slug=slug)


class AddProductToListView(View):
    def get(self, request, slug, list_type):
        product = get_object_or_404(Item, slug=slug)
        user_list, created = UserList.objects.get_or_create(user=request.user, list_type=list_type)
        if ListItem.objects.filter(user_list=user_list, product_name=product.title).exists():
            messages.info(request, "This item is already in your list.")
        else:
            ListItem.objects.create(user_list=user_list, product_name=product.title)
            messages.success(request, "Item added to your list.")
        return redirect('products:product', slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item qty was updated.")
            return redirect("products:cart")
        else:
            # add a message saying the user dosent have an order
            messages.info(request, "Item was not in your cart.")
            return redirect("products:product", slug=slug)
    else:
        # add a message saying the user doesn't have an order
        messages.info(request, "u don't have an active order.")
        return redirect("products:product", slug=slug)
    return redirect("products:product", slug=slug)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,

                'order': order
            }
            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                address_type='S',
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})

            return render(self.request, "order.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("products:order_detail")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the defualt shipping address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        address_type='S',
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('products:order_detail')

            else:
                print("User is entering a new shipping address")
                shipping_address1 = form.cleaned_data.get(
                    'shipping_address')
                shipping_address2 = form.cleaned_data.get(
                    'shipping_address2')
                shipping_country = form.cleaned_data.get(
                    'shipping_country')
                shipping_zip = form.cleaned_data.get('shipping_zip')

                if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                    shipping_address = Address(
                        user=self.request.user,
                        street_address=shipping_address1,
                        apartment_address=shipping_address2,
                        country=shipping_country,
                        zip=shipping_zip,
                        address_type='S'
                    )
                    shipping_address.save()

                    order.shipping_address = shipping_address
                    order.save()

                    set_default_shipping = form.cleaned_data.get(
                        'set_default_shipping')
                    if set_default_shipping:
                        shipping_address.default = True
                        shipping_address.save()

                else:
                    messages.info(
                        self.request, "Please fill in the required shipping address fields")

        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("products:cart")


def account_view(request):
    return render(request, 'products/account.html')


def deals_in_pcs(request):
    category = Category.objects.get(name="Deals in PCs")  # دریافت دسته‌بندی با نام خاص
    items = Item.objects.filter(category=category)  # فیلتر کردن محصولات مرتبط با این دسته‌بندی

    return render(request, 'products/deals_in_pcs.html', {'items': items})


def fashion(request):
    category = Category.objects.get(name="Shop deals in Fashion")  # دریافت دسته‌بندی با نام خاص
    items = Item.objects.filter(category=category)  # فیلتر کردن محصولات مرتبط با این دسته‌بندی

    return render(request, 'products/fashion.html', {'items': items})


def cars(request):
    category = Category.objects.get(name="Cars")  # دریافت دسته‌بندی با نام خاص
    items = Item.objects.filter(category=category)  # فیلتر کردن محصولات مرتبط با این دسته‌بندی

    return render(request, 'products/cars.html', {'items': items})


class BucketHome(IsAdminUserMixin, View):
    template_name = 'products/bucket.html'

    def get(self, request):
        objects = tasks.all_bucket_objects_task()
        return render(request, self.template_name, {'objects': objects})


class DeleteBucketObject(IsAdminUserMixin, View):
    def get(self, request, key):
        tasks.delete_object_task.delay(key)
        messages.success(request, 'your object will be delete soon.', 'info')
        return redirect('products:bucket')


class DownloadBucketObject(IsAdminUserMixin, View):
    def get(self, request, key):
        tasks.download_object_task.delay(key)
        messages.success(request, 'your download will start soon.', 'info')
        return redirect('products:bucket')
