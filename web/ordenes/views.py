from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from . import api
from .api import ApiError
from .forms import DetalleForm, OrdenForm


def health(request):
    return HttpResponse("ok")


def _payload_orden(datos):
    return {
        "cliente": datos["cliente"],
        "fecha": datos["fecha"].isoformat(),
        "estado": datos["estado"],
    }


def _payload_detalle(datos):
    return {
        "producto": datos["producto"],
        "cantidad": datos["cantidad"],
        "precio_unitario": str(datos["precio_unitario"]),
    }


# --------------------------------------------------------------------- ordenes
def orden_list(request):
    ordenes = []
    try:
        ordenes = api.listar_ordenes()
    except ApiError as exc:
        messages.error(request, str(exc))
    return render(request, "ordenes/orden_list.html", {"ordenes": ordenes})


def orden_detail(request, orden_id):
    try:
        orden = api.obtener_orden(orden_id)
    except ApiError as exc:
        messages.error(request, str(exc))
        return redirect("orden_list")
    return render(request, "ordenes/orden_detail.html", {"orden": orden})


@require_http_methods(["GET", "POST"])
def orden_create(request):
    if request.method == "POST":
        form = OrdenForm(request.POST)
        if form.is_valid():
            try:
                orden = api.crear_orden(_payload_orden(form.cleaned_data))
                messages.success(request, f"Orden #{orden['id']} creada correctamente.")
                return redirect("orden_detail", orden_id=orden["id"])
            except ApiError as exc:
                messages.error(request, str(exc))
    else:
        form = OrdenForm(initial={"fecha": date.today(), "estado": "Pendiente"})
    return render(request, "ordenes/form.html", {
        "form": form, "titulo": "Nueva orden", "cancelar": "/",
    })


@require_http_methods(["GET", "POST"])
def orden_edit(request, orden_id):
    try:
        orden = api.obtener_orden(orden_id)
    except ApiError as exc:
        messages.error(request, str(exc))
        return redirect("orden_list")

    if request.method == "POST":
        form = OrdenForm(request.POST)
        if form.is_valid():
            try:
                api.actualizar_orden(orden_id, _payload_orden(form.cleaned_data))
                messages.success(request, f"Orden #{orden_id} actualizada.")
                return redirect("orden_detail", orden_id=orden_id)
            except ApiError as exc:
                messages.error(request, str(exc))
    else:
        form = OrdenForm(initial={
            "cliente": orden["cliente"],
            "fecha": date.fromisoformat(orden["fecha"]),
            "estado": orden["estado"],
        })
    return render(request, "ordenes/form.html", {
        "form": form, "titulo": f"Editar orden #{orden_id}", "cancelar": f"/ordenes/{orden_id}/",
    })


@require_http_methods(["GET", "POST"])
def orden_delete(request, orden_id):
    if request.method == "POST":
        try:
            api.eliminar_orden(orden_id)
            messages.success(request, f"Orden #{orden_id} eliminada junto con sus detalles.")
            return redirect("orden_list")
        except ApiError as exc:
            messages.error(request, str(exc))
            return redirect("orden_detail", orden_id=orden_id)
    return render(request, "ordenes/confirm_delete.html", {
        "mensaje": f"¿Eliminar la orden #{orden_id} y todos sus detalles?",
        "cancelar": f"/ordenes/{orden_id}/",
    })


# --------------------------------------------------------------------- detalles
@require_http_methods(["GET", "POST"])
def detalle_create(request, orden_id):
    if request.method == "POST":
        form = DetalleForm(request.POST)
        if form.is_valid():
            try:
                api.agregar_detalle(orden_id, _payload_detalle(form.cleaned_data))
                messages.success(request, "Detalle agregado. El total de la orden fue recalculado.")
                return redirect("orden_detail", orden_id=orden_id)
            except ApiError as exc:
                messages.error(request, str(exc))
    else:
        form = DetalleForm(initial={"cantidad": 1})
    return render(request, "ordenes/form.html", {
        "form": form,
        "titulo": f"Agregar detalle a la orden #{orden_id}",
        "cancelar": f"/ordenes/{orden_id}/",
    })


@require_http_methods(["GET", "POST"])
def detalle_edit(request, orden_id, detalle_id):
    try:
        orden = api.obtener_orden(orden_id)
    except ApiError as exc:
        messages.error(request, str(exc))
        return redirect("orden_list")

    detalle = next((d for d in orden["detalles"] if d["id"] == detalle_id), None)
    if detalle is None:
        messages.error(request, f"El detalle {detalle_id} no existe en la orden #{orden_id}.")
        return redirect("orden_detail", orden_id=orden_id)

    if request.method == "POST":
        form = DetalleForm(request.POST)
        if form.is_valid():
            try:
                api.actualizar_detalle(detalle_id, _payload_detalle(form.cleaned_data))
                messages.success(request, "Detalle actualizado. El total de la orden fue recalculado.")
                return redirect("orden_detail", orden_id=orden_id)
            except ApiError as exc:
                messages.error(request, str(exc))
    else:
        form = DetalleForm(initial={
            "producto": detalle["producto"],
            "cantidad": detalle["cantidad"],
            "precio_unitario": detalle["precio_unitario"],
        })
    return render(request, "ordenes/form.html", {
        "form": form,
        "titulo": f"Editar detalle #{detalle_id} de la orden #{orden_id}",
        "cancelar": f"/ordenes/{orden_id}/",
    })


@require_http_methods(["GET", "POST"])
def detalle_delete(request, orden_id, detalle_id):
    if request.method == "POST":
        try:
            api.eliminar_detalle(detalle_id)
            messages.success(request, "Detalle eliminado. El total de la orden fue recalculado.")
        except ApiError as exc:
            messages.error(request, str(exc))
        return redirect("orden_detail", orden_id=orden_id)
    return render(request, "ordenes/confirm_delete.html", {
        "mensaje": f"¿Eliminar el detalle #{detalle_id} de la orden #{orden_id}?",
        "cancelar": f"/ordenes/{orden_id}/",
    })
