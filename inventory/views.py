import csv
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from .models import Inventory, StockMovement, Organization, UserProfile, ActivityLog
from .forms import InventoryForm, StockMovementForm, LoginForm, AdminSignupForm, CreateStaffForm, ChangePasswordForm


# helper to save activity log
def log_activity(user, action, description):
    try:
        profile = UserProfile.objects.get(user=user)
        org = profile.organization
    except UserProfile.DoesNotExist:
        org = None
    ActivityLog.objects.create(
        user=user,
        action=action,
        description=description,
        organization=org
    )


# helper to send low stock email to admin of the same organization
def send_low_stock_email(item):
    from django.core.mail import send_mail
    from django.conf import settings

    # find the admin of the same organization as the item
    if item.organization:
        admin_profile = UserProfile.objects.filter(
            organization=item.organization,
            user__is_staff=True
        ).first()
        if not admin_profile or not admin_profile.user.email:
            return
        admin = admin_profile.user
    else:
        return

    subject = 'Low Stock Alert - ' + item.item_name
    message = 'Hello ' + admin.username + ',\n\nThe item "' + item.item_name + '" is running low on stock.\n\nCurrent Quantity: ' + str(item.quantity) + '\nCategory: ' + item.category + '\nSupplier: ' + item.supplier + '\n\nPlease restock soon.\n\nStoreFlow - ' + (item.organization.name if item.organization else '')

    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [admin.email])
    except:
        pass


def admin_signup(request):
    form = AdminSignupForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            org_name = form.cleaned_data['organization_name']

            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken.')
                return render(request, 'inventory/admin_signup.html', {'form': form})

            org = Organization.objects.create(name=org_name)
            user = User.objects.create_user(username=username, password=password)
            user.is_staff = True
            user.email = form.cleaned_data['email']
            user.save()
            UserProfile.objects.create(user=user, organization=org)

            messages.success(request, 'Admin account created! Please login.')
            return redirect('login_view')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    return render(request, 'inventory/admin_signup.html', {'form': form})


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if not user.is_staff:
                    return render(request, 'inventory/login.html', {'form': form, 'error': 'This is Admin login. Please use Staff login.'})
                login(request, user)
                log_activity(user, 'LOGIN', 'Admin logged in')
                return redirect('inventory_list')
            else:
                return render(request, 'inventory/login.html', {'form': form, 'error': 'Invalid username or password.'})
        else:
            return render(request, 'inventory/login.html', {'form': form, 'error': 'Both fields are required.'})
    return render(request, 'inventory/login.html', {'form': form})


def staff_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_staff:
                return render(request, 'inventory/staff_login.html', {'error': 'This is Staff login. Please use Admin login.'})
            login(request, user)
            log_activity(user, 'LOGIN', 'Staff logged in')
            try:
                profile = UserProfile.objects.get(user=user)
                if profile.must_change_password:
                    return redirect('change_password')
            except UserProfile.DoesNotExist:
                pass
            return redirect('inventory_list')
        else:
            return render(request, 'inventory/staff_login.html', {'error': 'Invalid username or password.'})
    return render(request, 'inventory/staff_login.html')


def logout_view(request):
    log_activity(request.user, 'LOGOUT', 'User logged out')
    logout(request)
    return redirect('login_view')


@login_required(login_url='login_view')
def change_password(request):
    form = ChangePasswordForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            request.user.set_password(new_password)
            request.user.save()
            profile = UserProfile.objects.get(user=request.user)
            profile.must_change_password = False
            profile.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'Password changed successfully.')
            return redirect('inventory_list')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    return render(request, 'inventory/change_password.html', {'form': form})


@login_required(login_url='login_view')
def manage_users(request):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission.')
        return redirect('inventory_list')

    admin_profile = UserProfile.objects.get(user=request.user)
    org = admin_profile.organization
    staff_profiles = UserProfile.objects.filter(organization=org).exclude(user=request.user)

    form = CreateStaffForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            email = form.cleaned_data['email']

            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already taken.')
                return render(request, 'inventory/manage_users.html', {'form': form, 'staff_profiles': staff_profiles, 'org': org})

            user = User.objects.create_user(username=username, password=password)
            user.is_staff = False
            user.email = email
            user.save()
            UserProfile.objects.create(user=user, organization=org, must_change_password=True)

            # send email to staff with credentials
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                subject = 'Your StoreFlow Account - ' + org.name
                message = 'Hello ' + username + ',\n\nYour account has been created on StoreFlow.\n\nUsername: ' + username + '\nTemporary Password: ' + password + '\n\nPlease login and change your password immediately.\n\nLogin here: http://127.0.0.1:8000/staff-login/\n\nRegards,\n' + request.user.username + '\n' + org.name
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])
                log_activity(request.user, 'CREATE', 'Created staff user: ' + username + ' and sent credentials to ' + email)
                messages.success(request, 'Staff user ' + username + ' created. Credentials sent to ' + email)
            except:
                log_activity(request.user, 'CREATE', 'Created staff user: ' + username)
                messages.success(request, 'Staff user ' + username + ' created but email could not be sent. Temporary password: ' + password)

            return redirect('manage_users')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])

    return render(request, 'inventory/manage_users.html', {'form': form, 'staff_profiles': staff_profiles, 'org': org})


@login_required(login_url='login_view')
def deactivate_user(request, user_id):
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission.')
        return redirect('inventory_list')
    user = User.objects.get(id=user_id)
    user.is_active = False
    user.save()
    log_activity(request.user, 'UPDATE', 'Deactivated user: ' + user.username)
    messages.success(request, user.username + ' has been deactivated.')
    return redirect('manage_users')


@login_required(login_url='login_view')
def dashboard(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        org = profile.organization
    except UserProfile.DoesNotExist:
        org = None

    # only show stats for this organization
    all_items = Inventory.objects.filter(organization=org)
    total_items = all_items.count()
    total_quantity = sum(item.quantity for item in all_items)
    total_value = sum(item.quantity * item.price for item in all_items)
    low_stock_count = all_items.filter(quantity__lt=5).count()

    # data for category chart
    categories = {}
    for item in all_items:
        if item.category in categories:
            categories[item.category] += 1
        else:
            categories[item.category] = 1

    category_labels = list(categories.keys())
    category_data = list(categories.values())

    # data for stock levels chart - top 10 items
    top_items = all_items.order_by('-quantity')[:10]
    stock_labels = [item.item_name for item in top_items]
    stock_data = [item.quantity for item in top_items]

    return render(request, 'inventory/dashboard.html', {
        'total_items': total_items,
        'total_quantity': total_quantity,
        'total_value': round(total_value, 2),
        'low_stock_count': low_stock_count,
        'category_labels': category_labels,
        'category_data': category_data,
        'stock_labels': stock_labels,
        'stock_data': stock_data,
    })


@login_required(login_url='login_view')
def inventory_list(request):
    # get user's organization
    try:
        profile = UserProfile.objects.get(user=request.user)
        org = profile.organization
    except UserProfile.DoesNotExist:
        org = None

    # only show items from this organization
    items = Inventory.objects.filter(organization=org).order_by('id')

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

    return render(request, 'inventory/list.html', {
        'items': page_obj,
        'total': total,
        'page_obj': page_obj,
    })


@login_required(login_url='login_view')
def inventory_add(request):
    form = InventoryForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            name = form.cleaned_data['item_name']

            # get user's org first
            try:
                profile = UserProfile.objects.get(user=request.user)
                org = profile.organization
            except UserProfile.DoesNotExist:
                org = None

            # duplicate check within same organization only
            if Inventory.objects.filter(item_name=name, organization=org).exists():
                messages.error(request, 'Item with this name already exists.')
                return render(request, 'inventory/add.html', {'form': form})

            category = form.cleaned_data['category']
            if category == 'Other':
                other_category = request.POST.get('other_category')
                if other_category:
                    category = other_category
                else:
                    messages.error(request, 'Please specify the category name.')
                    return render(request, 'inventory/add.html', {'form': form})

            item = form.save(commit=False)
            item.category = category
            item.organization = org
            item.save()

            log_activity(request.user, 'CREATE', 'Added item: ' + item.item_name)
            if item.quantity < 5:
                send_low_stock_email(item)
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
            log_activity(request.user, 'UPDATE', 'Updated item: ' + item.item_name)
            if item.quantity < 5:
                send_low_stock_email(item)
            messages.success(request, 'Item updated successfully.')
            return redirect('inventory_list')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    return render(request, 'inventory/update.html', {'form': form, 'item': item})


@login_required(login_url='login_view')
def inventory_detail(request, id):
    item = Inventory.objects.get(id=id)
    history = StockMovement.objects.filter(item=item).order_by('-date')
    return render(request, 'inventory/detail.html', {'item': item, 'history': history})


@login_required(login_url='login_view')
def inventory_delete(request, id):
    if not request.user.is_staff:
        messages.error(request, 'Only admin can delete items.')
        return redirect('inventory_list')
    item = Inventory.objects.get(id=id)
    if request.method == 'POST':
        log_activity(request.user, 'DELETE', 'Deleted item: ' + item.item_name)
        item.delete()
        messages.success(request, 'Item deleted successfully.')
        return redirect('inventory_list')
    return render(request, 'inventory/delete_confirm.html', {'item': item})


@login_required(login_url='login_view')
def export_csv(request):
    if not request.user.is_staff:
        messages.error(request, 'Only admin can export reports.')
        return redirect('inventory_list')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
    writer = csv.writer(response)
    writer.writerow(['Item Name', 'Category', 'Quantity', 'Unit Price', 'Total Price', 'Supplier', 'Created Date'])
    items = Inventory.objects.all()
    for item in items:
        writer.writerow([item.item_name, item.category, item.quantity, item.price, item.total_price, item.supplier, item.created_date])
    log_activity(request.user, 'EXPORT', 'Exported inventory to CSV')
    return response


@login_required(login_url='login_view')
def import_csv(request):
    if not request.user.is_staff:
        messages.error(request, 'Only admin can import data.')
        return redirect('inventory_list')

    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            messages.error(request, 'Please select a CSV file.')
            return redirect('import_csv')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('import_csv')

        decoded_file = csv_file.read().decode('utf-8')
        csv_reader = csv.DictReader(decoded_file.splitlines())

        imported = 0
        skipped = 0

        for row in csv_reader:
            item_name = row.get('Item Name', '').strip()
            category = row.get('Category', '').strip()
            quantity = row.get('Quantity', '').strip()
            price = row.get('Unit Price', '').strip()
            supplier = row.get('Supplier', '').strip()

            if not item_name or not quantity or not price or not supplier:
                skipped += 1
                continue

            if Inventory.objects.filter(item_name=item_name).exists():
                skipped += 1
                continue

            Inventory.objects.create(
                item_name=item_name,
                category=category or 'Other',
                quantity=int(quantity),
                price=float(price),
                supplier=supplier
            )
            imported += 1

        log_activity(request.user, 'IMPORT', 'Imported ' + str(imported) + ' items from CSV')
        messages.success(request, str(imported) + ' items imported. ' + str(skipped) + ' rows skipped.')
        return redirect('inventory_list')

    return render(request, 'inventory/import_csv.html')


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
                done_by=request.user,
                organization=item.organization
            )
            log_activity(request.user, 'STOCK_IN' if movement_type == 'IN' else 'STOCK_OUT', movement_type + ' ' + str(quantity) + ' units of ' + item.item_name)
            if item.quantity < 5:
                send_low_stock_email(item)
            messages.success(request, 'Stock updated successfully.')
            return redirect('inventory_list')
        else:
            for error in form.errors.values():
                messages.error(request, error[0])
    return render(request, 'inventory/stock_movement.html', {'item': item, 'form': form})


@login_required(login_url='login_view')
def stock_history(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        org = profile.organization
    except UserProfile.DoesNotExist:
        org = None
    history = StockMovement.objects.filter(organization=org).order_by('-date')
    return render(request, 'inventory/stock_history.html', {'history': history})


@login_required(login_url='login_view')
def activity_log(request):
    if not request.user.is_staff:
        messages.error(request, 'Only admin can view activity log.')
        return redirect('inventory_list')
    try:
        profile = UserProfile.objects.get(user=request.user)
        org = profile.organization
    except UserProfile.DoesNotExist:
        org = None
    activities = ActivityLog.objects.filter(organization=org).order_by('-timestamp')
    return render(request, 'inventory/activity_log.html', {'activities': activities})


@login_required(login_url='login_view')
def profile_view(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        org = profile.organization
    except UserProfile.DoesNotExist:
        org = None

    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            request.user.email = email
            request.user.save()
            messages.success(request, 'Email updated successfully.')
            return redirect('profile_view')
        else:
            messages.error(request, 'Please enter a valid email.')

    return render(request, 'inventory/profile.html', {'org': org})
