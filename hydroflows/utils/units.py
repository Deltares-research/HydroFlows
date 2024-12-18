"""Utils for unit conversions."""

__all__ = ["convert_to_meters"]


def convert_to_meters(value: float, unit) -> float:
    """
    Convert a value to meters.

    Parameters
    ----------
    value (float): Value to convert.
    unit (str): The unit of the value ("m", "cm", "mm", "ft", or "in").

    Returns
    -------
    float: value converted to meters.
    """
    CONVERSION_FACTORS = {
        "m": 1,
        "cm": 0.01,
        "mm": 0.001,
        "ft": 0.3048,  # 1 foot = 0.3048 meters
        "in": 0.0254,  # 1 inch = 0.0254 meters
    }
    return value * CONVERSION_FACTORS[unit]
