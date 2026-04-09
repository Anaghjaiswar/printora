from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings

# --- 1. USER MANAGEMENT (Custom User) ---

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None  # Remove username field
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)
    profile_pic_id = models.IntegerField(default=1)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


# --- 2. SHOP MANAGEMENT ---

class PrintShop(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('maintenance', 'Under Maintenance'),
    ]

    name = models.CharField(max_length=255)
    address = models.TextField()
    logo = models.ImageField(upload_to='shop_logos/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    working_days = models.CharField(max_length=100, help_text="e.g., Mon-Fri")

    def __str__(self):
        return self.name


# --- 3. SERVICE & PRICING ---

class Service(models.Model):
    shop = models.ForeignKey(PrintShop, on_delete=models.CASCADE, related_name='services')
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=255)
    detailed_info = models.TextField(blank=True)
    icon = models.ImageField(upload_to='service_icons/', null=True, blank=True)
    theme_color = models.CharField(max_length=7, help_text="Hex code e.g. #FF8C00")
    
    base_price_label = models.CharField(max_length=50)
    bw_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    color_price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} - {self.shop.name}"


# --- 4. CUSTOMIZATION & DOCUMENTS ---

class Document(models.Model):
    COLOR_MODE_CHOICES = [('BW', 'B&W'), ('COLOR', 'Color')]
    SIDES_CHOICES = [('SINGLE', 'Single'), ('DOUBLE', 'Double')]
    PAPER_SIZE_CHOICES = [('A4', 'A4'), ('A3', 'A3')]

    # CRITICAL: Use settings.AUTH_USER_MODEL for custom users
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True)
    
    file = models.FileField(upload_to='print_docs/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    page_count = models.PositiveIntegerField(default=1)
    
    color_mode = models.CharField(max_length=10, choices=COLOR_MODE_CHOICES, default='BW')
    sides = models.CharField(max_length=10, choices=SIDES_CHOICES, default='SINGLE')
    paper_size = models.CharField(max_length=5, choices=PAPER_SIZE_CHOICES, default='A4')
    copies = models.PositiveIntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name} ({self.user.email})"


# --- 5. ORDERS & TRACKING ---

class Order(models.Model):
    STATUS_CHOICES = [
        ('PLACED', 'Placed'),
        ('ACCEPTED', 'Accepted'),
        ('PRINTING', 'Printing'),
        ('READY', 'Ready'),
        ('COMPLETED', 'Completed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    shop = models.ForeignKey(PrintShop, on_delete=models.CASCADE)
    documents = models.ManyToManyField(Document)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLACED')
    pickup_token = models.CharField(max_length=10, unique=True)
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    
    ordered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-ordered_at']

    def __str__(self):
        return f"{self.pickup_token} - {self.status}"


# --- 6. RAZORPAY INTEGRATION ---
class Payment(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='payment')
    
    # PhonePe specific fields
    merchant_transaction_id = models.CharField(max_length=100, unique=True)
    phonepe_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, default='UPI')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pay {self.merchant_transaction_id} - {self.status}"