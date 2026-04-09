from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PrintShop, Service, Document
from pypdf import PdfReader
import io

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'profile_pic_id', 'password']

    def create(self, validated_data):
        # Uses the custom manager we built earlier to hash the password
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            phone=validated_data.get('phone', ''),
            profile_pic_id=validated_data.get('profile_pic_id', 1)
        )
        return user
    
class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'id', 'title', 'description', 'detailed_info', 
            'icon', 'theme_color', 'base_price_label', 
            'bw_price', 'color_price', 'is_active'
        ]

class PrintShopSerializer(serializers.ModelSerializer):
    # FIXED: Changed read_all to read_only
    services = ServiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = PrintShop
        fields = [
            'id', 'name', 'address', 'logo', 'status', 
            'opening_time', 'closing_time', 'working_days', 
            'services'
        ]



class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            'id', 'service', 'file', 'file_name', 'page_count', 
            'color_mode', 'sides', 'paper_size', 'copies', 'created_at'
        ]
        read_only_fields = ['file_name', 'page_count', 'created_at']

    def create(self, validated_data):
        file_obj = validated_data['file']
        user = self.context['request'].user
        
        # 1. Capture original filename
        file_name = file_obj.name
        page_count = 1  # Default for images
        
        # 2. Efficiently count PDF pages
        if file_name.lower().endswith('.pdf'):
            try:
                # PdfReader doesn't load the whole file; it just reads the trailer
                reader = PdfReader(file_obj)
                page_count = len(reader.pages)
            except Exception as e:
                # Fallback or error handling if PDF is corrupt
                raise serializers.ValidationError({"file": "Could not read PDF page count."})

        # 3. Create the document
        return Document.objects.create(
            user=user,
            file_name=file_name,
            page_count=page_count,
            **validated_data
        )