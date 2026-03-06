from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Screenshot:
    path: Path
    image_url: str
    width_px: int
    height_px: int
    scale_factor: float


@dataclass(frozen=True)
class DisplayGeometry:
    width_points: float
    height_points: float
    width_px: int
    height_px: int
    scale_factor: float
