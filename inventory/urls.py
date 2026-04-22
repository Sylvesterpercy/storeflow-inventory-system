from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_list, name='inventory_list'),
    path('add/', views.inventory_add, name='inventory_add'),
    path('delete/<int:id>/', views.inventory_delete, name='inventory_delete'),
    path('update/<int:id>/', views.inventory_update, name='inventory_update'),
    path('admin-signup/', views.admin_signup, name='admin_signup'),
    path('login/', views.login_view, name='login_view'),
    path('staff-login/', views.staff_login_view, name='staff_login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('change-password/', views.change_password, name='change_password'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('deactivate-user/<int:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('detail/<int:id>/', views.inventory_detail, name='inventory_detail'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('export/', views.export_csv, name='export_csv'),
    path('stock/<int:id>/', views.stock_movement, name='stock_movement'),
    path('history/', views.stock_history, name='stock_history'),
    path('activity-log/', views.activity_log, name='activity_log'),
    path('import/', views.import_csv, name='import_csv'),
    path('profile/', views.profile_view, name='profile_view'),
]
