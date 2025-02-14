"""Climate utility functions."""

CLIMATE_VARS = {
    "precip": {
        "resample": "sum",
        "multiplier": True,
    },
    "temp": {
        "resample": "mean",
        "multiplier": False,
    },
    "pet": {
        "resample": "sum",
        "multiplier": True,
    },
    "temp_dew": {
        "resample": "mean",
        "multiplier": False,
    },
    "kin": {
        "resample": "mean",
        "multiplier": True,
    },
    "wind": {
        "resample": "mean",
        "multiplier": True,
    },
    "tcc": {
        "resample": "mean",
        "multiplier": True,
    },
}


def intersection(lst1, lst2):
    """Get matching elements from two lists."""
    return list(set(lst1) & set(lst2))
