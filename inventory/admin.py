from django.contrib import admin
from .models import Inventory, StockMovement, Organization, UserProfile

admin.site.register(Inventory)
admin.site.register(StockMovement)
admin.site.register(Organization)
admin.site.register(UserProfile)