from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from .models import ProductReview, UserList, ListItem

class CartAddForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=9)

class CouponApplyForm(forms.Form):
    code = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Promo code'
    }))

class RefundForm(forms.Form):
    ref_code = forms.CharField()
    message = forms.CharField(widget=forms.Textarea(attrs={
        'rows': 4
    }))
    email = forms.EmailField()

class SearchForm(forms.Form):
    query = forms.CharField()

class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['name', 'rating', 'review_text']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your name'}),
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'review_text': forms.Textarea(attrs={'rows': 3}),
            'parent': forms.HiddenInput(),
        }


class UserListForm(forms.ModelForm):
    class Meta:
        model = UserList
        fields = ['name', 'list_type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'list_type': forms.Select(attrs={'class': 'form-control'}),
        }

class ListItemForm(forms.ModelForm):
    class Meta:
        model = ListItem
        fields = ['product_name', 'quantity']
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class CheckoutForm(forms.Form):
    shipping_address = forms.CharField(required=False)
    shipping_country = CountryField(blank_label='(select country)').formfield(
        required=False,
        widget=CountrySelectWidget(attrs={
            'class': 'custom-select d-block w-100',
        }))
    shipping_zip = forms.CharField(required=False)
