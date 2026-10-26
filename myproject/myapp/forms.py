from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Category, Product, UserProfile


class SignUpForm(UserCreationForm):
    email = forms.EmailField()
    role = forms.ChoiceField(choices=UserProfile.Role.choices)

    class Meta:
        model = User
        fields = ('username', 'email', 'role')


class ProductForm(forms.ModelForm):
    new_category = forms.CharField(
        required=False,
        max_length=80,
        help_text='Optional: enter a new category instead of selecting one.',
    )

    class Meta:
        model = Product
        fields = (
            'name',
            'category',
            'description',
            'image_url',
            'price_per_day',
            'security_deposit',
            'stock',
        )
        widgets = {
            'category': forms.Select(attrs={'required': False}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'price_per_day': forms.NumberInput(attrs={'min': '0.01', 'step': '0.01'}),
            'security_deposit': forms.NumberInput(attrs={'min': '0', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'min': 1, 'step': 1}),
            'image_url': forms.URLInput(attrs={'placeholder': 'https://example.com/item.jpg'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].required = False

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('new_category', '').strip()
        if name and cleaned_data.get('category'):
            self.add_error('new_category', 'Select a category or enter a new one, not both.')
        return cleaned_data

    def save(self, commit=True):
        product = super().save(commit=False)
        name = self.cleaned_data.get('new_category', '').strip()
        if name:
            product.category, _ = Category.objects.get_or_create(name=name)
        if commit:
            product.save()
            self.save_m2m()
        return product


class BookingForm(forms.Form):
    event_name = forms.CharField(max_length=120)
    event_type = forms.CharField(max_length=80, required=False)
    event_location = forms.CharField(max_length=200, required=False)
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'min': 1, 'step': 1}),
    )

    def clean_start_date(self):
        start_date = self.cleaned_data['start_date']
        if start_date < timezone.localdate():
            raise forms.ValidationError('Choose today or a future date.')
        return start_date

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', 'The end date must be on or after the start date.')
        return cleaned_data
