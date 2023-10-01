import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Coordinate:
    x: int
    y: int

    def as_tuple(self) -> tuple[int, int]:
        return self.x, self.y

    def distance_to(self, other_coordinate: "Coordinate") -> int:  # euclidean distance
        distance = math.sqrt((other_coordinate.x - self.x) ** 2 + (other_coordinate.y - self.y) ** 2)
        return abs(int(distance))

    @staticmethod
    def of_center(bounding_box: np.ndarray) -> "Coordinate":
        center_x = (bounding_box[0] + bounding_box[2]) / 2
        center_y = (bounding_box[1] + bounding_box[3]) / 2
        return Coordinate(int(center_x), int(center_y))
