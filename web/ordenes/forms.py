from decimal import Decimal

from django import forms

ESTADOS = [("Pendiente", "Pendiente"), ("Pagada", "Pagada"), ("Anulada", "Anulada")]


class OrdenForm(forms.Form):
    cliente = forms.CharField(label="Cliente", max_length=120)
    fecha = forms.DateField(
        label="Fecha",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    estado = forms.ChoiceField(label="Estado", choices=ESTADOS)


class DetalleForm(forms.Form):
    producto = forms.CharField(label="Producto", max_length=120)
    cantidad = forms.IntegerField(label="Cantidad", min_value=1, max_value=10000)
    precio_unitario = forms.DecimalField(
        label="Precio unitario",
        min_value=Decimal("0"),
        max_value=Decimal("99999.99"),
        max_digits=7,
        decimal_places=2,
    )
