from django import template

register = template.Library()


@register.filter(name="get_item")
def get_item(d, key):
    if d is None:
        return ""
    if hasattr(d, "get"):
        v = d.get(key, "")
    else:
        try:
            v = d[key]
        except (KeyError, IndexError, TypeError):
            return ""
    if v is None or v == 0 or v == 0.0 or v == "0":
        return ""
    return v