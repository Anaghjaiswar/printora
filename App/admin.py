from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    # Specify how users are listed in the admin panel
    list_display = ('email', 'phone', 'profile_pic_id', 'is_staff')
    ordering = ('email',)
    
    # These fields are required for the "Add User" and "Change User" screens
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('phone', 'profile_pic_id')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # This is for the "Add User" form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'phone', 'profile_pic_id'),
        }),
    )

admin.site.register(User, CustomUserAdmin)