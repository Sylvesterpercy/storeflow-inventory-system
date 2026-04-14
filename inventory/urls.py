from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_list, name='inventory_list'),
    path('add/', views.inventory_add, name='inventory_add'),
    path('delete/<int:id>/', views.inventory_delete, name='inventory_delete'),
    path('update/<int:id>/', views.inventory_update, name='inventory_update'),
    path('signup/', views.signup_view, name='signup_view'),
    path('login/', views.login_view, name='login_view'),
    path('logout/', views.logout_view, name='logout_view'),
    path('detail/<int:id>/', views.inventory_detail, name='inventory_detail'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('export/', views.export_csv, name='export_csv'),
    path('stock/<int:id>/', views.stock_movement, name='stock_movement'),
    path('history/', views.stock_history, name='stock_history'),
]