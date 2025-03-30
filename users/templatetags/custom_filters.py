from django import template

register = template.Library()

@register.filter
def humanize_url_name(value):
    """Convert URL name to human-readable format (e.g., 'my_rides' -> 'My Rides')"""
    return value.replace('_', ' ').title()