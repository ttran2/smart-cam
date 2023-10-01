from dataclasses import dataclass
from typing import Optional

import numpy as np
from supervision import Detections

from common.coordinate import Coordinate


@dataclass(frozen=True)
class Detection:
    org_detections: Detections
    xyxy: np.ndarray
    center: Coordinate
    mask: Optional[np.ndarray] = None
    confidence: Optional[np.ndarray] = None
    class_id: Optional[np.ndarray] = None
    tracker_id: Optional[np.ndarray] = None
