from django import template

register = template.Library()


@register.filter(name="abs")
def abs_filter(value):
    """Devuelve el valor absoluto de un número (Django no trae este filtro)."""
    try:
        return abs(value)
    except (TypeError, ValueError):
        return value
