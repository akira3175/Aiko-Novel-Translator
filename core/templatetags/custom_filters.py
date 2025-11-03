"""
Custom template filters
"""
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Nhân hai số"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def striptags(value):
    """Remove HTML tags và checkpoint info"""
    import re
    if not value:
        return ""
    
    # Remove checkpoint info
    value = re.sub(r'\s*checkpoint:\d+\s*', '', value)
    
    # Remove HTML tags
    value = re.sub(r'<[^>]+>', '', value)
    
    return value.strip()