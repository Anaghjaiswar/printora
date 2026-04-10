from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('App', '0003_rename_captured_at_payment_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='phonepe_order_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
