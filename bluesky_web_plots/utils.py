def deep_update(original: dict, updates: dict) -> dict:
    """Recursively update a dictionary."""
    for key, value in updates.items():
        if (
            isinstance(value, dict)
            and key in original
            and isinstance(original[key], dict)
        ):
            original[key] = deep_update(original[key], value)
        else:
            original[key] = value
    return original
