import os
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import pymssql
from flask import Flask, jsonify, request
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException

ESTADOS = ("Pendiente", "Pagada", "Anulada")
MAX_CANTIDAD = 10000
MAX_PRECIO = Decimal("99999.99")


class JSONProvider(DefaultJSONProvider):
    ensure_ascii = False
    sort_keys = False

    @staticmethod
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, datetime):
            return o.date().isoformat()
        if isinstance(o, date):
            return o.isoformat()
        return DefaultJSONProvider.default(o)


app = Flask(__name__)
app.json = JSONProvider(app)


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


# ----------------------------------------------------------------- base de datos
def get_connection():
    return pymssql.connect(
        server=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", "1433"),
        user=os.environ.get("DB_USER", "sa"),
        password=os.environ["DB_PASSWORD"],
        database=os.environ.get("DB_NAME", "OrdenesDB"),
        login_timeout=5,
        as_dict=True,
    )


@contextmanager
def db():
    """Abre una conexion y un cursor; hace commit al salir o rollback si hay error."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_orden(cur, orden_id):
    cur.execute(
        "SELECT id, cliente, fecha, estado, total FROM ordenes WHERE id = %s", (orden_id,)
    )
    orden = cur.fetchone()
    if orden is None:
        raise ApiError(404, f"La orden {orden_id} no existe")
    return orden


def listar_detalles(cur, orden_id):
    cur.execute(
        "SELECT id, orden_id, producto, cantidad, precio_unitario, subtotal "
        "FROM orden_detalle WHERE orden_id = %s ORDER BY id",
        (orden_id,),
    )
    return cur.fetchall()


def orden_completa(cur, orden_id):
    orden = obtener_orden(cur, orden_id)
    orden["detalles"] = listar_detalles(cur, orden_id)
    return orden


def recalcular_total(cur, orden_id):
    cur.execute(
        "UPDATE ordenes SET total = "
        "(SELECT COALESCE(SUM(subtotal), 0) FROM orden_detalle WHERE orden_id = %s) "
        "WHERE id = %s",
        (orden_id, orden_id),
    )


def insertar_detalle(cur, orden_id, producto, cantidad, precio):
    cur.execute(
        "INSERT INTO orden_detalle (orden_id, producto, cantidad, precio_unitario, subtotal) "
        "OUTPUT INSERTED.id VALUES (%s, %s, %s, %s, %s)",
        (orden_id, producto, cantidad, precio, cantidad * precio),
    )
    return cur.fetchone()["id"]


# ------------------------------------------------------------------ validaciones
def cuerpo_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "El cuerpo de la peticion debe ser un objeto JSON")
    return data


def validar_texto(valor, campo):
    if not isinstance(valor, str) or not valor.strip():
        raise ApiError(400, f"El campo '{campo}' es obligatorio")
    valor = valor.strip()
    if len(valor) > 120:
        raise ApiError(400, f"El campo '{campo}' admite maximo 120 caracteres")
    return valor


def validar_fecha(valor):
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ApiError(400, "El campo 'fecha' debe tener el formato AAAA-MM-DD")


def validar_estado(valor):
    if valor not in ESTADOS:
        raise ApiError(400, f"El campo 'estado' debe ser uno de: {', '.join(ESTADOS)}")
    return valor


def validar_cantidad(valor):
    try:
        if isinstance(valor, bool) or (isinstance(valor, float) and not valor.is_integer()):
            raise ValueError
        cantidad = int(valor)
    except (TypeError, ValueError):
        raise ApiError(400, "El campo 'cantidad' debe ser un numero entero")
    if not 1 <= cantidad <= MAX_CANTIDAD:
        raise ApiError(400, f"El campo 'cantidad' debe estar entre 1 y {MAX_CANTIDAD}")
    return cantidad


def validar_precio(valor):
    try:
        if isinstance(valor, bool):
            raise ValueError
        precio = Decimal(str(valor)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ApiError(400, "El campo 'precio_unitario' debe ser un numero")
    if not precio.is_finite() or not 0 <= precio <= MAX_PRECIO:
        raise ApiError(400, f"El campo 'precio_unitario' debe estar entre 0 y {MAX_PRECIO}")
    return precio


def validar_detalle(data):
    if not isinstance(data, dict):
        raise ApiError(400, "Cada detalle debe ser un objeto JSON")
    return (
        validar_texto(data.get("producto"), "producto"),
        validar_cantidad(data.get("cantidad")),
        validar_precio(data.get("precio_unitario")),
    )


# -------------------------------------------------------------------- ordenes
@app.get("/api/ordenes")
def listar_ordenes():
    with db() as cur:
        cur.execute("SELECT id, cliente, fecha, estado, total FROM ordenes ORDER BY id")
        return jsonify(cur.fetchall())


@app.get("/api/ordenes/<int:orden_id>")
def ver_orden(orden_id):
    with db() as cur:
        return jsonify(orden_completa(cur, orden_id))


@app.post("/api/ordenes")
def crear_orden():
    data = cuerpo_json()
    cliente = validar_texto(data.get("cliente"), "cliente")
    fecha = validar_fecha(data["fecha"]) if data.get("fecha") else date.today()
    estado = validar_estado(data.get("estado", "Pendiente"))
    detalles = data.get("detalles", [])
    if not isinstance(detalles, list):
        raise ApiError(400, "El campo 'detalles' debe ser una lista")
    detalles = [validar_detalle(d) for d in detalles]

    with db() as cur:
        cur.execute(
            "INSERT INTO ordenes (cliente, fecha, estado, total) "
            "OUTPUT INSERTED.id VALUES (%s, %s, %s, 0)",
            (cliente, fecha, estado),
        )
        orden_id = cur.fetchone()["id"]
        for producto, cantidad, precio in detalles:
            insertar_detalle(cur, orden_id, producto, cantidad, precio)
        recalcular_total(cur, orden_id)
        return jsonify(orden_completa(cur, orden_id)), 201


@app.put("/api/ordenes/<int:orden_id>")
def actualizar_orden(orden_id):
    data = cuerpo_json()
    if not any(campo in data for campo in ("cliente", "fecha", "estado")):
        raise ApiError(400, "Envie al menos uno de los campos: cliente, fecha, estado")

    with db() as cur:
        actual = obtener_orden(cur, orden_id)
        cliente = validar_texto(data["cliente"], "cliente") if "cliente" in data else actual["cliente"]
        fecha = validar_fecha(data["fecha"]) if "fecha" in data else actual["fecha"]
        estado = validar_estado(data["estado"]) if "estado" in data else actual["estado"]
        cur.execute(
            "UPDATE ordenes SET cliente = %s, fecha = %s, estado = %s WHERE id = %s",
            (cliente, fecha, estado, orden_id),
        )
        return jsonify(orden_completa(cur, orden_id))


@app.delete("/api/ordenes/<int:orden_id>")
def eliminar_orden(orden_id):
    with db() as cur:
        obtener_orden(cur, orden_id)
        cur.execute("DELETE FROM orden_detalle WHERE orden_id = %s", (orden_id,))
        cur.execute("DELETE FROM ordenes WHERE id = %s", (orden_id,))
    return jsonify(mensaje=f"Orden {orden_id} eliminada junto con sus detalles")


# -------------------------------------------------------------------- detalles
@app.get("/api/ordenes/<int:orden_id>/detalles")
def ver_detalles(orden_id):
    with db() as cur:
        obtener_orden(cur, orden_id)
        return jsonify(listar_detalles(cur, orden_id))


@app.post("/api/ordenes/<int:orden_id>/detalles")
def agregar_detalle(orden_id):
    producto, cantidad, precio = validar_detalle(cuerpo_json())
    with db() as cur:
        obtener_orden(cur, orden_id)
        detalle_id = insertar_detalle(cur, orden_id, producto, cantidad, precio)
        recalcular_total(cur, orden_id)
        cur.execute(
            "SELECT id, orden_id, producto, cantidad, precio_unitario, subtotal "
            "FROM orden_detalle WHERE id = %s",
            (detalle_id,),
        )
        return jsonify(cur.fetchone()), 201


@app.put("/api/detalles/<int:detalle_id>")
def actualizar_detalle(detalle_id):
    data = cuerpo_json()
    if not any(campo in data for campo in ("producto", "cantidad", "precio_unitario")):
        raise ApiError(400, "Envie al menos uno de los campos: producto, cantidad, precio_unitario")

    with db() as cur:
        cur.execute(
            "SELECT id, orden_id, producto, cantidad, precio_unitario "
            "FROM orden_detalle WHERE id = %s",
            (detalle_id,),
        )
        actual = cur.fetchone()
        if actual is None:
            raise ApiError(404, f"El detalle {detalle_id} no existe")

        producto = validar_texto(data["producto"], "producto") if "producto" in data else actual["producto"]
        cantidad = validar_cantidad(data["cantidad"]) if "cantidad" in data else actual["cantidad"]
        precio = validar_precio(data["precio_unitario"]) if "precio_unitario" in data else actual["precio_unitario"]

        cur.execute(
            "UPDATE orden_detalle SET producto = %s, cantidad = %s, precio_unitario = %s, "
            "subtotal = %s WHERE id = %s",
            (producto, cantidad, precio, cantidad * precio, detalle_id),
        )
        recalcular_total(cur, actual["orden_id"])
        cur.execute(
            "SELECT id, orden_id, producto, cantidad, precio_unitario, subtotal "
            "FROM orden_detalle WHERE id = %s",
            (detalle_id,),
        )
        return jsonify(cur.fetchone())


@app.delete("/api/detalles/<int:detalle_id>")
def eliminar_detalle(detalle_id):
    with db() as cur:
        cur.execute("SELECT orden_id FROM orden_detalle WHERE id = %s", (detalle_id,))
        fila = cur.fetchone()
        if fila is None:
            raise ApiError(404, f"El detalle {detalle_id} no existe")
        cur.execute("DELETE FROM orden_detalle WHERE id = %s", (detalle_id,))
        recalcular_total(cur, fila["orden_id"])
    return jsonify(mensaje=f"Detalle {detalle_id} eliminado")


# ---------------------------------------------------------------------- health
@app.get("/health")
def health():
    try:
        with db() as cur:
            cur.execute("SELECT 1 AS ok")
        return jsonify(status="ok", db="ok")
    except Exception as exc:  # noqa: BLE001
        app.logger.error("Healthcheck: no hay conexion con la base de datos: %s", exc)
        return jsonify(status="error", db="sin conexion"), 503


# --------------------------------------------------------------------- errores
@app.errorhandler(ApiError)
def manejar_api_error(err):
    return jsonify(error=err.message), err.status


@app.errorhandler(HTTPException)
def manejar_http(err):
    mensajes = {404: "Recurso no encontrado", 405: "Metodo no permitido para esta ruta"}
    return jsonify(error=mensajes.get(err.code, err.description)), err.code


@app.errorhandler(Exception)
def manejar_error_interno(err):
    app.logger.exception("Error no controlado: %s", err)
    return jsonify(error="Error interno del servidor"), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)