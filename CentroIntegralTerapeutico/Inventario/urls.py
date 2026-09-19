from django.contrib import admin
from django.urls import path, include
from Pacientes import views as pacientes_views # si tienes esto
from . import views

urlpatterns = [
    path('', views.lista_medicamentos, name='lista_medicamentos'),
    path('crear/', views.crear_medicamento, name='crear_medicamento'),
    path('<int:pk>/editar/', views.editar_medicamento, name='editar_medicamento'),
    path('<int:pk>/eliminar/', views.eliminar_medicamento, name='eliminar_medicamento'),
    path('medicamento/<int:pk>/modificar_cantidad/', views.modificar_cantidad_medicamento, name='modificar_cantidad_medicamento'),

    # URL para imprimir una etiqueta específica (ya la tenías)
    path('<int:pk>/imprimir/', views.imprimir_etiqueta_medicamento, name='imprimir_etiqueta_medicamento'),

    # NUEVAS URLS para la impresión de múltiples etiquetas:
    # Asegúrate de que estas dos líneas estén presentes
    path('medicamentos/seleccionar-imprimir/', views.seleccionar_medicamentos_para_imprimir, name='seleccionar_medicamentos_para_imprimir'),
    path('medicamentos/imprimir-lotes/<str:selected_ids_str>/', views.imprimir_varias_etiquetas_pdf, name='imprimir_varias_etiquetas_pdf'),



     # URLs para el punto de venta
    path('punto-de-venta/', views.punto_venta, name='punto_venta'),
    path('ajax/agregar/', views.ajax_agregar_a_venta, name='ajax_agregar_a_venta'),
    path('ajax/eliminar/', views.ajax_eliminar_de_venta, name='ajax_eliminar_de_venta'),
    path('ajax/finalizar/', views.ajax_finalizar_venta, name='ajax_finalizar_venta'),




    # --- AÑADE ESTAS URLS PARA EL SISTEMA DE CORTE DE CAJA ---
    path('cortes/iniciar/', views.iniciar_corte_view, name='iniciar_corte'),
    path('cortes/activo/', views.corte_activo_view, name='corte_activo'),
    path('cortes/cerrar/', views.cerrar_corte_view, name='cerrar_corte'),
    path('cortes/historial/', views.historial_cortes_view, name='historial_cortes'),
    path('cortes/exitoso/', views.corte_exitoso_view, name='corte_exitoso'),





    # URL para imprimir el recibo. El <int:venta_id> le pasa el ID de la venta.
    path('recibo/<int:venta_id>/', views.imprimir_recibo, name='imprimir_recibo'),


    # URL para el historial de ventas
    path('reporte/ventas/', views.historial_ventas, name='historial_ventas'),
    path('reporte/ventas/eliminar-lote/', views.eliminar_ventas_lote, name='eliminar_ventas_lote'),
    path('reporte/ventas/eliminar-antiguas/', views.eliminar_ventas_antiguas, name='eliminar_ventas_antiguas'),
    
    path('cortes/eliminar-antiguos/', views.eliminar_cortes_antiguos, name='eliminar_cortes_antiguos'),

    path('accounts/', include('django.contrib.auth.urls')), # <-- ¡Verifica que esta línea exista!





]