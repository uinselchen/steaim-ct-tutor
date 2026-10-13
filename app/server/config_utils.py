def parse_bool_value(value, default=False):
    """Convert common environment-file boolean values safely."""
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")
