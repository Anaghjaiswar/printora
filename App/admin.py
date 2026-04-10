from django.contrib import admin
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

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'phone', 'profile_pic_id', 'is_staff', 'is_active')
    search_fields = ('email', 'phone')
    ordering = ('email',)

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

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('merchant_transaction_id', 'phonepe_order_id', 'order', 'status', 'payment_method', 'amount', 'created_at', 'updated_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('merchant_transaction_id', 'phonepe_order_id', 'phonepe_transaction_id')
    readonly_fields = ('created_at', 'updated_at')