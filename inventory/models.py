from django.db import models
from django.contrib.auth.models import User

CATEGORY_CHOICES = [
    ('Electronics', 'Electronics'),
    ('Furniture', 'Furniture'),
    ('Stationery', 'Stationery'),
    ('Clothing', 'Clothing'),
    ('Other', 'Other'),
]

class Inventory(models.Model):
    item_name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    price = models.FloatField()
    supplier = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    created_date = models.DateField(auto_now_add=True, null=True)

    def __str__(self):
        return self.item_name

    @property
    def total_price(self):
        return round(self.quantity * self.price, 2)


class StockMovement(models.Model):
    MOVEMENT_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]

    item = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    movement_type = models.CharField(max_length=3, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    reason = models.CharField(max_length=200)
    done_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.item.item_name + ' - ' + self.movement_type
    