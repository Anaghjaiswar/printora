from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import UserSerializer

class SignupView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        user = authenticate(email=email, password=password)
        
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "user_id": user.pk,
                "email": user.email
            })
        else:
            return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    # Sirf login kiye hue users hi logout kar sakte hain
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # User ka current token delete kar rahe hain
            request.user.auth_token.delete()
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Something went wrong"}, status=status.HTTP_400_BAD_REQUEST)
        

from django.db import models

class PrintShop(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed')
    ]

    name = models.CharField(max_length=255)
    address = models.TextField()
    logo = models.ImageField(upload_to='shop_logos/')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='open'
    )
    
    # Timing fields
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    working_days = models.CharField(
        max_length=100, 
        help_text="Example: Mon-Fri"
    )

    def __str__(self):
        return self.name
    

class Service(models.Model):
    # Relate each service to a specific shop
    shop = models.ForeignKey('PrintShop', on_delete=models.CASCADE, related_name='services')
    
    title = models.CharField(max_length=100)  # e.g., "A4 Printing"
    description = models.CharField(max_length=255)  # e.g., "Assignments, resumes, notes"
    detailed_info = models.TextField(blank=True)  # e.g., "Single or double-sided"
    
    # Visuals
    icon = models.ImageField(upload_to='service_icons/')

    # Pricing
    base_price_label = models.CharField(
        max_length=50, 
        help_text="e.g., 'From ₹2/pages'"
    )
    bw_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    color_price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.title} - {self.shop.name}"
    

from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    COLOR_MODE_CHOICES = [('BW', 'B&W'), ('COLOR', 'Color')]
    SIDES_CHOICES = [('SINGLE', 'Single'), ('DOUBLE', 'Double')]
    PAPER_SIZE_CHOICES = [('A4', 'A4'), ('A3', 'A3')]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='print_docs/%Y/%m/%d/')
    file_name = models.CharField(max_length=255) # e.g., "screenshot 2024-12-21.png"
    page_count = models.PositiveIntegerField(default=1)
    
    # Print Settings from UI
    color_mode = models.CharField(max_length=10, choices=COLOR_MODE_CHOICES, default='BW')
    sides = models.CharField(max_length=10, choices=SIDES_CHOICES, default='SINGLE')
    paper_size = models.CharField(max_length=5, choices=PAPER_SIZE_CHOICES, default='A4')
    copies = models.PositiveIntegerField(default=1)
    
    service = models.ForeignKey('Service', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name
    

class Order(models.Model):
    STATUS_CHOICES = [
        ('PLACED', 'Placed'),
        ('ACCEPTED', 'Accepted'),
        ('PRINTING', 'Printing'),
        ('READY', 'Ready'),
        ('COMPLETED', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey('PrintShop', on_delete=models.CASCADE)
    documents = models.ManyToManyField(Document) # Order can have multiple files
    
    # Order Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLACED')
    pickup_token = models.CharField(max_length=10, unique=True) # e.g., "P-402"
    
    # Payment Info (from the Order Detail UI)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, default='UPI')
    transaction_id = models.CharField(max_length=100, blank=True, null=True) # Ref Number
    
    ordered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-ordered_at']

    def __str__(self):
        return f"Order {self.pickup_token} - {self.status}"
    

# --- 4. ORDERS & TRACKING ---

class Order(models.Model):
    STATUS_CHOICES = [
        ('PLACED', 'Placed'),
        ('ACCEPTED', 'Accepted'),
        ('PRINTING', 'Printing'),
        ('READY', 'Ready'),
        ('COMPLETED', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(PrintShop, on_delete=models.CASCADE)
    documents = models.ManyToManyField(Document) # One order can have multiple files
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLACED')
    pickup_token = models.CharField(max_length=10, unique=True) # e.g., "P-402"
    
    # Financials
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    
    ordered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-ordered_at']

    def __str__(self):
        return f"{self.pickup_token} - {self.status}"


# --- 5. RAZORPAY INTEGRATION ---

class Payment(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    
    # Razorpay IDs
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True) # Ref Number
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='PENDING')
    payment_method = models.CharField(max_length=50, default='UPI') # Display purpose
    
    captured_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for {self.order.pickup_token} - {self.status}"