from django import template

register = template.Library()


@register.filter
def percent_of(value, total):
    try:
        total = float(total)
        if total <= 0:
            return 0
        return min(round(float(value) / total * 100, 1), 100)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


@register.simple_tag(takes_context=True)
def nav_active(context, url_name):
    request = context.get('request')
    if not request:
        return ''
    resolver = request.resolver_match
    if resolver and resolver.url_name == url_name:
        return 'active'
    return ''
