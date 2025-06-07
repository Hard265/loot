from django import template
from datetime import datetime

from django.utils.html import re

register = template.Library()

@register.filter(name="format_date")
def format_date(date_str, format):
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime(format)
    except ValueError:
        return date_str

@register.filter(name="format_size")
def format_size(size):
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.1f} {units[index]}"
