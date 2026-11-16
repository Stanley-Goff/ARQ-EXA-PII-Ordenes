from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("", views.orden_list, name="orden_list"),
    path("ordenes/nueva/", views.orden_create, name="orden_create"),
    path("ordenes/<int:orden_id>/", views.orden_detail, name="orden_detail"),
    path("ordenes/<int:orden_id>/editar/", views.orden_edit, name="orden_edit"),
    path("ordenes/<int:orden_id>/eliminar/", views.orden_delete, name="orden_delete"),
    path("ordenes/<int:orden_id>/detalles/nuevo/", views.detalle_create, name="detalle_create"),
    path("ordenes/<int:orden_id>/detalles/<int:detalle_id>/editar/", views.detalle_edit, name="detalle_edit"),
    path("ordenes/<int:orden_id>/detalles/<int:detalle_id>/eliminar/", views.detalle_delete, name="detalle_delete"),
]
