from django.contrib import admin
from .models import Inventory, StockMovement

admin.site.register(Inventory)
admin.site.register(StockMovement)