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
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'captured_at')

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

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('pickup_token', 'user', 'shop', 'status', 'total_amount', 'is_paid', 'ordered_at')
    list_filter = ('status', 'is_paid', 'shop', 'ordered_at')
    search_fields = ('pickup_token', 'user__email')
    readonly_fields = ('pickup_token', 'ordered_at')
    inlines = [PaymentInline]
    
    # Custom actions to update status quickly
    actions = ['mark_as_printing', 'mark_as_ready', 'mark_as_completed']

    def mark_as_printing(self, request, queryset):
        queryset.update(status='PRINTING')
    mark_as_printing.short_description = "Change status to Printing"

    def mark_as_ready(self, request, queryset):
        queryset.update(status='READY')
    mark_as_ready.short_description = "Change status to Ready"

    def mark_as_completed(self, request, queryset):
        queryset.update(status='COMPLETED')
    mark_as_completed.short_description = "Change status to Completed"

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('razorpay_order_id', 'order', 'status', 'payment_method', 'captured_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('captured_at',)