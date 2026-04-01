from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Inventory, StockMovement


class AuthTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='Test@1234')

    def test_login_page_loads(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)

    def test_signup_page_loads(self):
        response = self.client.get('/signup/')
        self.assertEqual(response.status_code, 200)

    def test_login_with_correct_credentials(self):
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'Test@1234'
        })
        self.assertRedirects(response, '/')

    def test_login_with_wrong_credentials(self):
        response = self.client.post('/login/', {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertContains(response, 'Invalid')

    def test_logout(self):
        self.client.login(username='testuser', password='Test@1234')
        response = self.client.get('/logout/')
        self.assertRedirects(response, '/login/')

    def test_redirect_to_login_if_not_logged_in(self):
        response = self.client.get('/')
        self.assertRedirects(response, '/login/?next=/')


class InventoryTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='Test@1234')
        self.client.login(username='testuser', password='Test@1234')

        # create a sample item
        self.item = Inventory.objects.create(
            item_name='Test Item',
            quantity=10,
            price=100.0,
            supplier='Test Supplier',
            category='Electronics'
        )

    def test_inventory_list_loads(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_add_item(self):
        response = self.client.post('/add/', {
            'item_name': 'New Item',
            'quantity': 5,
            'price': 200.0,
            'supplier': 'Supplier A',
            'category': 'Furniture'
        })
        self.assertRedirects(response, '/')
        self.assertTrue(Inventory.objects.filter(item_name='New Item').exists())

    def test_add_duplicate_item(self):
        response = self.client.post('/add/', {
            'item_name': 'Test Item',
            'quantity': 5,
            'price': 200.0,
            'supplier': 'Supplier A',
            'category': 'Furniture'
        })
        self.assertRedirects(response, '/add/')

    def test_update_item(self):
        response = self.client.post('/update/' + str(self.item.id) + '/', {
            'item_name': 'Updated Item',
            'quantity': 20,
            'price': 150.0,
            'supplier': 'Updated Supplier',
            'category': 'Electronics'
        })
        self.assertRedirects(response, '/')
        updated = Inventory.objects.get(id=self.item.id)
        self.assertEqual(updated.item_name, 'Updated Item')

    def test_delete_item(self):
        response = self.client.post('/delete/' + str(self.item.id) + '/')
        self.assertRedirects(response, '/')
        self.assertFalse(Inventory.objects.filter(id=self.item.id).exists())

    def test_add_item_with_empty_fields(self):
        response = self.client.post('/add/', {
            'item_name': '',
            'quantity': '',
            'price': '',
            'supplier': '',
            'category': 'Electronics'
        })
        self.assertRedirects(response, '/add/')


class StockMovementTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='Test@1234')
        self.client.login(username='testuser', password='Test@1234')

        self.item = Inventory.objects.create(
            item_name='Stock Item',
            quantity=10,
            price=50.0,
            supplier='Supplier B',
            category='Stationery'
        )

    def test_stock_in(self):
        self.client.post('/stock/' + str(self.item.id) + '/', {
            'movement_type': 'IN',
            'quantity': 5,
            'reason': 'New purchase'
        })
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 15)

    def test_stock_out(self):
        self.client.post('/stock/' + str(self.item.id) + '/', {
            'movement_type': 'OUT',
            'quantity': 3,
            'reason': 'Sold to customer'
        })
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 7)

    def test_stock_out_more_than_available(self):
        response = self.client.post('/stock/' + str(self.item.id) + '/', {
            'movement_type': 'OUT',
            'quantity': 50,
            'reason': 'Test'
        })
        self.item.refresh_from_db()
        # quantity should not change
        self.assertEqual(self.item.quantity, 10)

    def test_stock_history_loads(self):
        response = self.client.get('/history/')
        self.assertEqual(response.status_code, 200)
