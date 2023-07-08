"""Helper functions for Vantage integration."""


def scale_color_brightness(
    color: tuple[int, ...], brightness: int | None
) -> tuple[int, ...]:
    """Scale the brightness of an RGB/RGBW color tuple."""
    if brightness is None:
        return color

    return tuple(int(round(c * brightness / 255)) for c in color)


def brightness_to_level(brightness: int) -> float:
    """Convert a HA brightness value [0..255] to a Vantage level value [0..100]."""
    return brightness / 255 * 100


def level_to_brightness(level: float) -> int:
    """Convert a Vantage level value [0..100] to a HA brightness value [0..255]."""
    return round(level / 100 * 255)
