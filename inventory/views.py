import csv
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from .models import Inventory, StockMovement
from .forms import InventoryForm, StockMovementForm, SignupForm, LoginForm


def signup_view(request):
    form = SignupForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken.')
                return render(request, 'inventory/signup.html', {'form': form})
            User.objects.create_user(username=username, password=password)
            messages.success(request, 'Account created! Please login.')
            return redirect('login_view')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    return render(request, 'inventory/signup.html', {'form': form})


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

    search = request.GET.get('search')
    if search:
        items = items.filter(item_name__icontains=search) | items.filter(supplier__icontains=search)

    category = request.GET.get('category')
    if category:
        items = items.filter(category=category)

    sort = request.GET.get('sort')
    if sort == 'name':
        items = items.order_by('item_name')
    elif sort == 'price':
        items = items.order_by('price')

    total = items.count()

    paginator = Paginator(items, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventory/list.html', {'items': page_obj, 'total': total, 'page_obj': page_obj})


@login_required(login_url='login_view')
def inventory_add(request):
    form = InventoryForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data['item_name']
            # duplicate check
            if Inventory.objects.filter(item_name=name).exists():
                messages.error(request, 'Item with this name already exists.')
                return render(request, 'inventory/add.html', {'form': form})
            form.save()
            messages.success(request, 'Item added successfully.')
            return redirect('inventory_list')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    return render(request, 'inventory/add.html', {'form': form})


@login_required(login_url='login_view')
def inventory_update(request, id):
    item = Inventory.objects.get(id=id)
    form = InventoryForm(request.POST or None, instance=item)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Item updated successfully.')
            return redirect('inventory_list')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    return render(request, 'inventory/update.html', {'form': form, 'item': item})


@login_required(login_url='login_view')
def inventory_detail(request, id):
    item = Inventory.objects.get(id=id)
    # get stock history for this item
    history = StockMovement.objects.filter(item=item).order_by('-date')
    return render(request, 'inventory/detail.html', {'item': item, 'history': history})


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
    writer.writerow(['Item Name', 'Category', 'Quantity', 'Unit Price', 'Total Price', 'Supplier', 'Created Date'])
    items = Inventory.objects.all()
    for item in items:
        writer.writerow([item.item_name, item.category, item.quantity, item.price, item.total_price, item.supplier, item.created_date])
    return response


@login_required(login_url='login_view')
def stock_movement(request, id):
    item = Inventory.objects.get(id=id)
    form = StockMovementForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            movement_type = form.cleaned_data['movement_type']
            quantity = form.cleaned_data['quantity']
            reason = form.cleaned_data['reason']

            if movement_type == 'OUT' and quantity > item.quantity:
                messages.error(request, 'Not enough stock. Available: ' + str(item.quantity))
                return render(request, 'inventory/stock_movement.html', {'item': item, 'form': form})

            if movement_type == 'IN':
                item.quantity += quantity
            else:
                item.quantity -= quantity
            item.save()

            StockMovement.objects.create(
                item=item,
                movement_type=movement_type,
                quantity=quantity,
                reason=reason,
                done_by=request.user
            )
            messages.success(request, 'Stock updated successfully.')
            return redirect('inventory_list')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    return render(request, 'inventory/stock_movement.html', {'item': item, 'form': form})


@login_required(login_url='login_view')
def stock_history(request):
    history = StockMovement.objects.all().order_by('-date')
    return render(request, 'inventory/stock_history.html', {'history': history})
