from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.html import format_html
from .models import User, PrintShop, Service, Document, Order, Payment

# --- INLINES ---

class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    fields = ('title', 'bw_price', 'color_price', 'is_active')

class DocumentInline(admin.StackedInline):
    model = Order.documents.through
    extra = 0
    verbose_name = "Order Document"
    verbose_name_plural = "Order Documents"

class PaymentInline(admin.StackedInline):
    model = Payment
    can_delete = False
    readonly_fields = ('merchant_transaction_id', 'phonepe_order_id', 'phonepe_transaction_id', 'status', 'amount', 'payment_method', 'created_at', 'updated_at')

# --- MODEL ADMINS ---

class UserCreationAdminForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('email', 'phone', 'profile_pic_id', 'is_staff', 'is_active')

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserChangeAdminForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        help_text='Raw passwords are not stored, so there is no way to see this user\'s password.'
    )

    class Meta:
        model = User
        fields = ('email', 'phone', 'profile_pic_id', 'password', 'is_active', 'is_staff', 'is_superuser')

    def clean_password(self):
        return self.initial['password']

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationAdminForm
    form = UserChangeAdminForm
    model = User

    list_display = ('email', 'phone', 'profile_pic_id', 'is_staff', 'is_active', 'is_superuser')
    search_fields = ('email', 'phone')
    ordering = ('email',)
    list_filter = ('is_staff', 'is_active', 'is_superuser')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('phone', 'profile_pic_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'phone', 'profile_pic_id', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )

@admin.register(PrintShop)
class PrintShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'opening_time', 'closing_time', 'show_logo')
    list_filter = ('status', 'working_days')
    search_fields = ('name', 'address')
    inlines = [ServiceInline]

    def show_logo(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="width: 45px; height:45px; border-radius:5px;" />', obj.logo.url)
        return "No Logo"
    show_logo.short_description = 'Logo Preview'

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'shop', 'bw_price', 'color_price', 'is_active', 'color_tag')
    list_filter = ('shop', 'is_active')
    search_fields = ('title', 'description')

    def color_tag(self, obj):
        return format_html(
            '<div style="width:20px; height:20px; background-color:{}; border-radius:3px; border:1px solid #ddd;"></div>',
            obj.theme_color
        )
    color_tag.short_description = 'Theme'

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'user', 'color_mode', 'sides', 'page_count', 'copies', 'created_at')
    list_filter = ('color_mode', 'sides', 'paper_size')
    readonly_fields = ('created_at',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('pickup_token', 'user', 'shop', 'status', 'is_paid', 'total_amount', 'ordered_at')
    list_filter = ('status', 'is_paid', 'shop', 'ordered_at')
    search_fields = ('pickup_token', 'user__email', 'shop__name', 'payment__merchant_transaction_id')
    readonly_fields = ('pickup_token', 'ordered_at', 'completed_at')
    inlines = [DocumentInline, PaymentInline]
    filter_horizontal = ('documents',)
    list_select_related = ('user', 'shop')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('merchant_transaction_id', 'phonepe_order_id', 'order', 'status', 'payment_method', 'amount', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('merchant_transaction_id', 'phonepe_order_id', 'phonepe_transaction_id')
    readonly_fields = ('created_at', 'updated_at')