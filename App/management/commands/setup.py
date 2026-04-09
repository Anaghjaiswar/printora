from django.core.management.base import BaseCommand
from App.models import PrintShop, Service
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Injects initial print shop and service data from UI designs'

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding data...")

        # 1. Create Shops
        shops_data = [
            {
                "name": "CSIT Block Print Shop",
                "address": "CS & IT Block, Ground Floor",
                "status": "open",
                "opening_time": datetime.time(9, 0),
                "closing_time": datetime.time(18, 0),
                "working_days": "Mon-Sat"
            },
            {
                "name": "Library Print Shop",
                "address": "Central Library, Near Entrance",
                "status": "open",
                "opening_time": datetime.time(9, 0),
                "closing_time": datetime.time(18, 0),
                "working_days": "Mon-Sat"
            }
        ]

        created_shops = []
        for shop_info in shops_data:
            shop, created = PrintShop.objects.get_or_create(
                name=shop_info['name'],
                defaults=shop_info
            )
            created_shops.append(shop)
            if created:
                self.stdout.write(f"Created Shop: {shop.name}")

        # 2. Define Services (Matching UI exactly)
        services_data = [
            {
                "title": "A4 Printing",
                "description": "Assignments, resumes, notes",
                "detailed_info": "Single or double-sided",
                "theme_color": "#FF8C00", # Orange
                "base_price_label": "From ₹2/pages",
                "bw_price": 2.00,
                "color_price": 8.00
            },
            {
                "title": "Document Xerox",
                "description": "Copy any document or book",
                "detailed_info": "Any page size",
                "theme_color": "#00BCD4", # Cyan
                "base_price_label": "From ₹1/pages",
                "bw_price": 1.00,
                "color_price": 5.00
            },
            {
                "title": "Photo Print",
                "description": "Glossy or matte photo prints",
                "detailed_info": "4*6, 5*7, passport size. Glossy or matte finish.",
                "theme_color": "#9C27B0", # Purple
                "base_price_label": "From ₹5/pages",
                "bw_price": 5.00,
                "color_price": 15.00
            },
            {
                "title": "Spiral Binding",
                "description": "Bind your project or thesis",
                "detailed_info": "Hard/Soft cover - Any thickness - A4 or A3",
                "theme_color": "#4CAF50", # Green
                "base_price_label": "From ₹15/pages",
                "bw_price": 15.00,
                "color_price": 15.00
            }
        ]

        # 3. Inject Services for each Shop
        for shop in created_shops:
            for s_info in services_data:
                service, created = Service.objects.get_or_create(
                    shop=shop,
                    title=s_info['title'],
                    defaults=s_info
                )
                if created:
                    self.stdout.write(f"  - Added Service: {service.title} to {shop.name}")

        self.stdout.write(self.style.SUCCESS('Successfully seeded database with UI-aligned data.'))