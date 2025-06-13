from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using key."""
    try:
        return dictionary.get(int(key))  # Convert key to integer since schedule IDs are integers
    except (KeyError, ValueError, TypeError, AttributeError):
        return None