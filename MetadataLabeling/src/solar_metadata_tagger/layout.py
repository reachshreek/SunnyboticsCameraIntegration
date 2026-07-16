from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import MetadataTaggerError
from .models import SiteAssignment


@dataclass(frozen=True)
class PanelFeature:
    feature_id: str
    row: str
    panel: str
    polygon: tuple[tuple[float, float], ...]  # (longitude, latitude)
    center: tuple[float, float]


class LayoutResolver:
    """Assign row/panel from a GeoJSON polygon layout."""

    def __init__(self, features: tuple[PanelFeature, ...], nearest_limit_m: float = 3.0) -> None:
        self.features = features
        self.nearest_limit_m = nearest_limit_m

    @classmethod
    def from_geojson(cls, path: str | Path) -> "LayoutResolver":
        layout_path = Path(path)
        try:
            raw = json.loads(layout_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise MetadataTaggerError(
                "LAYOUT_NOT_FOUND", "Layout file was not found.", path=str(layout_path)
            ) from exc
        except json.JSONDecodeError as exc:
            raise MetadataTaggerError(
                "LAYOUT_INVALID_JSON", "Layout file is not valid JSON.", path=str(layout_path)
            ) from exc

        if raw.get("type") != "FeatureCollection" or not isinstance(raw.get("features"), list):
            raise MetadataTaggerError(
                "LAYOUT_INVALID", "Layout must be a GeoJSON FeatureCollection."
            )

        parsed: list[PanelFeature] = []
        for index, feature in enumerate(raw["features"]):
            try:
                props = feature["properties"]
                geometry = feature["geometry"]
                if geometry["type"] != "Polygon":
                    raise ValueError("Only Polygon geometry is supported")
                ring = geometry["coordinates"][0]
                polygon = tuple((float(point[0]), float(point[1])) for point in ring)
                if len(polygon) < 4:
                    raise ValueError("Polygon must contain at least four coordinates")
                row = str(props["row"])
                panel = str(props["panel"])
                feature_id = str(feature.get("id", f"feature-{index}"))
                center = _polygon_center(polygon)
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                raise MetadataTaggerError(
                    "LAYOUT_INVALID",
                    "A layout feature is invalid.",
                    feature_index=index,
                    detail=str(exc),
                ) from exc
            parsed.append(PanelFeature(feature_id, row, panel, polygon, center))

        nearest_limit = float(raw.get("properties", {}).get("nearest_limit_m", 3.0))
        return cls(tuple(parsed), nearest_limit_m=nearest_limit)

    def resolve(self, latitude: float, longitude: float) -> SiteAssignment:
        containing = [f for f in self.features if _point_in_polygon(longitude, latitude, f.polygon)]
        if len(containing) == 1:
            feature = containing[0]
            return SiteAssignment(feature.row, feature.panel, "polygon", feature.feature_id, 0.0)
        if len(containing) > 1:
            raise MetadataTaggerError(
                "LAYOUT_AMBIGUOUS",
                "Coordinate falls inside multiple panel polygons.",
                feature_ids=[f.feature_id for f in containing],
            )
        if not self.features:
            return SiteAssignment(None, None, "no-layout-features")

        nearest = min(
            self.features,
            key=lambda f: _haversine_m(latitude, longitude, f.center[1], f.center[0]),
        )
        distance = _haversine_m(latitude, longitude, nearest.center[1], nearest.center[0])
        if distance <= self.nearest_limit_m:
            return SiteAssignment(nearest.row, nearest.panel, "nearest-center", nearest.feature_id, distance)
        return SiteAssignment(None, None, "no-match", distance_m=distance)


def _point_in_polygon(x: float, y: float, polygon: tuple[tuple[float, float], ...]) -> bool:
    inside = False
    j = len(polygon) - 1
    for i, (xi, yi) in enumerate(polygon):
        xj, yj = polygon[j]
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-15) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _polygon_center(polygon: tuple[tuple[float, float], ...]) -> tuple[float, float]:
    # A simple mean is sufficient for the small panel polygons expected here.
    points = polygon[:-1] if polygon[0] == polygon[-1] else polygon
    return (
        sum(p[0] for p in points) / len(points),
        sum(p[1] for p in points) / len(points),
    )


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_008.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
