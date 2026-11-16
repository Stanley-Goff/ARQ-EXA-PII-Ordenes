"""Cliente de la API REST. El frontend solo habla con la API, nunca con la base de datos."""
import requests
from django.conf import settings


class ApiError(Exception):
    """Error legible para mostrar al usuario."""


def _request(method, path, payload=None):
    url = settings.API_URL.rstrip("/") + path
    try:
        resp = requests.request(method, url, json=payload, timeout=10)
    except requests.exceptions.Timeout:
        raise ApiError("La API tardo demasiado en responder. Intente de nuevo.")
    except requests.exceptions.ConnectionError:
        raise ApiError("No se pudo conectar con la API. Verifique que el servicio este activo.")
    except requests.exceptions.RequestException as exc:
        raise ApiError(f"Error al comunicarse con la API: {exc}")

    try:
        data = resp.json()
    except ValueError:
        data = None

    if resp.status_code >= 400:
        detalle = data.get("error") if isinstance(data, dict) else None
        raise ApiError(detalle or f"La API respondio con el codigo {resp.status_code}.")
    return data


def listar_ordenes():
    return _request("GET", "/api/ordenes")


def obtener_orden(orden_id):
    return _request("GET", f"/api/ordenes/{orden_id}")


def crear_orden(payload):
    return _request("POST", "/api/ordenes", payload)


def actualizar_orden(orden_id, payload):
    return _request("PUT", f"/api/ordenes/{orden_id}", payload)


def eliminar_orden(orden_id):
    return _request("DELETE", f"/api/ordenes/{orden_id}")


def agregar_detalle(orden_id, payload):
    return _request("POST", f"/api/ordenes/{orden_id}/detalles", payload)


def actualizar_detalle(detalle_id, payload):
    return _request("PUT", f"/api/detalles/{detalle_id}", payload)


def eliminar_detalle(detalle_id):
    return _request("DELETE", f"/api/detalles/{detalle_id}")
