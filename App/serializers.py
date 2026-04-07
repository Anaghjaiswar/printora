from rest_framework import serializers
from django.contrib.auth import get_user_model

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
    
