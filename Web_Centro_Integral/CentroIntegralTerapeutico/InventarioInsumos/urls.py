# InventarioInsumos/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_insumos, name='lista_insumos'),
    path('crear/', views.crear_insumo, name='crear_insumo'),
    path('editar/<int:pk>/', views.editar_insumo, name='editar_insumo'),
    path('eliminar/<int:pk>/', views.eliminar_insumo, name='eliminar_insumo'),
]