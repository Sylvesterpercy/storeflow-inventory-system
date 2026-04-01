import csv
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from .models import Inventory, StockMovement
from .forms import InventoryForm, SignupForm, LoginForm


def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not username or not password or not confirm_password:
            messages.error(request, 'All fields are required.')
            return redirect('signup_view')

        if len(username) < 3:
            messages.error(request, 'Username must be at least 3 characters.')
            return redirect('signup_view')

        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return redirect('signup_view')

        if not any(char.isupper() for char in password):
            messages.error(request, 'Password must have at least one uppercase letter.')
            return redirect('signup_view')

        if not any(char.isdigit() for char in password):
            messages.error(request, 'Password must have at least one number.')
            return redirect('signup_view')

        if not any(char in '@#!$%&*' for char in password):
            messages.error(request, 'Password must have at least one special character (@, #, !, $, %, &, *).')
            return redirect('signup_view')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('signup_view')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken. Try another one.')
            return redirect('signup_view')

        User.objects.create_user(username=username, password=password)
        messages.success(request, 'Account created! Please login.')
        return redirect('login_view')

    return render(request, 'inventory/signup.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            return render(request, 'inventory/login.html', {'error': 'Both fields are required.'})

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('inventory_list')
        else:
            return render(request, 'inventory/login.html', {'error': 'Invalid username or password.'})

    return render(request, 'inventory/login.html')


def logout_view(request):
    logout(request)
    return redirect('login_view')


@login_required(login_url='login_view')
def dashboard(request):
    all_items = Inventory.objects.all()
    total_items = all_items.count()
    total_quantity = sum(item.quantity for item in all_items)
    total_value = sum(item.quantity * item.price for item in all_items)
    low_stock_count = all_items.filter(quantity__lt=5).count()
    return render(request, 'inventory/dashboard.html', {
        'total_items': total_items,
        'total_quantity': total_quantity,
        'total_value': round(total_value, 2),
        'low_stock_count': low_stock_count,
    })


@login_required(login_url='login_view')
def inventory_list(request):
    items = Inventory.objects.all().order_by('id')

    # search
    search = request.GET.get('search')
    if search:
        items = items.filter(item_name__icontains=search) | items.filter(supplier__icontains=search)

    # sort
    sort = request.GET.get('sort')
    if sort == 'name':
        items = items.order_by('item_name')
    elif sort == 'price':
        items = items.order_by('price')

    total = items.count()

    # pagination - 5 items per page
    paginator = Paginator(items, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/list.html', {'items': page_obj, 'total': total, 'page_obj': page_obj})


@login_required(login_url='login_view')
def inventory_add(request):
    if request.method == 'POST':
        name = request.POST.get('item_name')
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')
        supplier = request.POST.get('supplier')
        category = request.POST.get('category')

        # if other is selected, use the typed category name
        if category == 'Other':
            other_category = request.POST.get('other_category')
            if other_category:
                category = other_category
            else:
                messages.error(request, 'Please specify the category name.')
                return redirect('inventory_add')

        if not name or not quantity or not price or not supplier:
            messages.error(request, 'All fields are required.')
            return redirect('inventory_add')

        if int(quantity) < 0:
            messages.error(request, 'Quantity cannot be negative.')
            return redirect('inventory_add')

        if float(price) < 0:
            messages.error(request, 'Price cannot be negative.')
            return redirect('inventory_add')

        if Inventory.objects.filter(item_name=name).exists():
            messages.error(request, 'Item with this name already exists.')
            return redirect('inventory_add')

        Inventory.objects.create(
            item_name=name,
            quantity=quantity,
            price=price,
            supplier=supplier,
            category=category
        )
        messages.success(request, 'Item added successfully.')
        return redirect('inventory_list')

    return render(request, 'inventory/add.html')


@login_required(login_url='login_view')
def inventory_update(request, id):
    item = Inventory.objects.get(id=id)
    if request.method == 'POST':
        name = request.POST.get('item_name')
        quantity = request.POST.get('quantity')
        price = request.POST.get('price')
        supplier = request.POST.get('supplier')
        category = request.POST.get('category')

        if not name or not quantity or not price or not supplier:
            messages.error(request, 'All fields are required.')
            return render(request, 'inventory/update.html', {'item': item})

        if int(quantity) < 0:
            messages.error(request, 'Quantity cannot be negative.')
            return render(request, 'inventory/update.html', {'item': item})

        if float(price) < 0:
            messages.error(request, 'Price cannot be negative.')
            return render(request, 'inventory/update.html', {'item': item})

        item.item_name = name
        item.quantity = quantity
        item.price = price
        item.supplier = supplier
        item.category = category
        item.save()
        messages.success(request, 'Item updated successfully.')
        return redirect('inventory_list')

    return render(request, 'inventory/update.html', {'item': item})


@login_required(login_url='login_view')
def inventory_delete(request, id):
    item = Inventory.objects.get(id=id)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted successfully.')
        return redirect('inventory_list')
    return render(request, 'inventory/delete_confirm.html', {'item': item})


@login_required(login_url='login_view')
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory.csv"'

    writer = csv.writer(response)
    writer.writerow(['Item Name', 'Category', 'Quantity', 'Price', 'Supplier', 'Created Date'])

    items = Inventory.objects.all()
    for item in items:
        writer.writerow([item.item_name, item.category, item.quantity, item.price, item.supplier, item.created_date])

    return response


@login_required(login_url='login_view')
def stock_movement(request, id):
    item = Inventory.objects.get(id=id)

    if request.method == 'POST':
        movement_type = request.POST.get('movement_type')
        quantity = request.POST.get('quantity')
        reason = request.POST.get('reason')

        if not movement_type or not quantity or not reason:
            messages.error(request, 'All fields are required.')
            return render(request, 'inventory/stock_movement.html', {'item': item})

        quantity = int(quantity)

        if quantity <= 0:
            messages.error(request, 'Quantity must be greater than 0.')
            return render(request, 'inventory/stock_movement.html', {'item': item})

        if movement_type == 'OUT' and quantity > item.quantity:
            messages.error(request, 'Not enough stock. Available: ' + str(item.quantity))
            return render(request, 'inventory/stock_movement.html', {'item': item})

        # update item quantity
        if movement_type == 'IN':
            item.quantity += quantity
        else:
            item.quantity -= quantity

        item.save()

        # save movement record
        StockMovement.objects.create(
            item=item,
            movement_type=movement_type,
            quantity=quantity,
            reason=reason,
            done_by=request.user
        )

        messages.success(request, 'Stock updated successfully.')
        return redirect('inventory_list')

    return render(request, 'inventory/stock_movement.html', {'item': item})


@login_required(login_url='login_view')
def stock_history(request):
    history = StockMovement.objects.all().order_by('-date')
    return render(request, 'inventory/stock_history.html', {'history': history})
