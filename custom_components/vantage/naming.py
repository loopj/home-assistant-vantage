"""Hierarchical naming utility for Vantage load entities.

Replicates the register_id() naming algorithm from pyvantage so that entity IDs
match the old integration exactly, preserving all automations and history.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiovantage import Vantage
    from aiovantage.objects import LocationObject


def get_area_lineage(client: "Vantage", area_vid: int | None) -> list[str]:
    """Walk the area tree upward from area_vid, returning names closest-to-root.

    For example, area "Dining Room Balcony" whose parent is "1st Floor" whose
    parent is "Exterior" whose parent is the root "Harr Residence" returns:
        ["Dining Room Balcony", "1st Floor", "Exterior", "Harr Residence"]
    """
    lineage: list[str] = []
    current = area_vid
    count = 0
    while current and count < 10:
        area = client.areas.get(current)
        if area is None:
            break
        lineage.append(area.d_name or area.name)
        current = area.area  # parent area VID; 0 or None at root
        count += 1
    return lineage


def hierarchical_load_name(client: "Vantage", obj: "LocationObject") -> str:
    """Build a hierarchical name for a load, matching pyvantage register_id().

    Algorithm (mirrors pyvantage exactly):
    1. Walk the area tree upward to get the lineage (closest-to-root order).
    2. Drop the root area (last element).
    3. Reverse to get top-down order.
    4. Skip any area whose name starts with "Station Load " or "Color Load ".
    5. Join with "-" and append the load's display name.

    Example: VID 447 in "Dining Room Balcony" → "1st Floor" → "Exterior" → root
      returns "Exterior-1st Floor-Dining Room Balcony-Fan (Ceiling)"
    """
    lineage = get_area_lineage(client, obj.area)
    parts = [
        p
        for p in reversed(lineage[:-1])  # drop root, reverse to top-down
        if not p.startswith("Station Load ")
        and not p.startswith("Color Load ")
    ]
    prefix = "-".join(parts) + "-" if parts else ""
    load_name = getattr(obj, "d_name", None) or obj.name
    return prefix + load_name
