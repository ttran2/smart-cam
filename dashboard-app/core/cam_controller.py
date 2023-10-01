from typing import Optional

import cv2
import numpy as np
from supervision import Detections

from common import Coordinate, Detection, Timer, LoggerInterface
from core.esp32_bridge import Esp32Bridge


PERSON_CLASS_ID = 0


class CamController:
    """
    CamController main method is `handle(...)`, where it takes the camera frame and YOLO detections, and appropriately
    send camera movement instruction.

    This class responsibilities are:
    - parse the YOLO detections for each frame
    - pick a target to track if a target is not picked yet
    - send movement commands to Esp32Bridge to keep the tracked target near the center of the screen
        - it indicates how far the target is from the center in Pixels
    - attempt to recover if we lose the target for a short period of time (coyote system) before selecting a new target
    """

    def __init__(self, width: int, height: int, esp32_bridge: Esp32Bridge, tracking_enabled: bool = True,
                 target_class_id: int = PERSON_CLASS_ID, coyote_seconds: int = 3, boundary_offset: int = 10,
                 show_arrows: bool = True, show_boundaries: bool = True, show_center: bool = True,
                 logger_class: Optional[LoggerInterface] = None):
        self.width = width  # camera width
        self.height = height  # camera height
        self.esp32_bridge = esp32_bridge  # the module that communicates with the Esp32 Cam
        self.tracking_enabled = tracking_enabled  # enable/disable tracking feature
        self.target_class_id = target_class_id  # the object type we want to track
        self.coyote_seconds = coyote_seconds  # how long do we wait before finding a new target
        self.boundary_offset = boundary_offset  # create a boundary by offsetting this much from the center
        self.show_arrows = show_arrows  # display arrows that shows where we want cam to move
        self.show_boundaries = show_boundaries  # show a box where we try to get the target in
        self.show_center = show_center  # show the center of the target
        self.logger_class = logger_class  # an instance of a logger class that is able to push a log message to the GUI

        self.center_x = self.center_y = self.center = self.boundary_top_left = self.boundary_bottom_right = None
        self.resize(self.width, self.height)

        self.target_tracker_id: Optional[int] = None  # the tracker ID of the target that we are following
        self.coyote_timer: Optional[Timer] = None  # the time we attempt to find our old target before selecting a new target

    def resize(self, width: int, height: int):
        self.width = width
        self.height = height
        self.center_x = int(self.width / 2)
        self.center_y = int(self.height / 2)
        self.center = Coordinate(x=self.center_x, y=self.center_y)
        self.resize_boundary()

    def resize_boundary(self, boundary_offset: Optional[int] = None):
        if boundary_offset is not None:
            self.boundary_offset = int(boundary_offset)
        self.boundary_top_left = Coordinate(
            x=self.center_x - self.boundary_offset,
            y=self.center_y - self.boundary_offset
        )
        self.boundary_bottom_right = Coordinate(
            x=self.center_x + self.boundary_offset,
            y=self.center_y + self.boundary_offset
        )

    def log(self, msg: str):
        if self.logger_class is not None:
            self.logger_class.log(message=msg)

    @staticmethod
    def draw_arrow(frame, direction):
        arrow_size = 50
        arrow_color = (0, 0, 255)
        arrow_thickness = 5
        padding = 50
        h, w, _ = frame.shape

        if direction == "up":
            start_point = (w // 2, h + padding + arrow_size)
            end_point = (w // 2, h + padding)
        elif direction == "down":
            start_point = (w // 2, h - padding - arrow_size)
            end_point = (w // 2, h - arrow_size)
        elif direction == "left":
            start_point = (padding + arrow_size, h // 2)
            end_point = (padding, h // 2)
        else:  # direction == "right"
            start_point = (w - padding - arrow_size, h // 2)
            end_point = (w - padding, h // 2)

        cv2.arrowedLine(frame, start_point, end_point, arrow_color, arrow_thickness)

    def _get_closest_detection(self, detections: Detections, tracker_id_override: Optional[int] = None) -> Optional[Detection]:
        """ Return the closest detection to the center of the screen (or detection with the provided tracker id) """
        detection = None
        shortest_distance = None
        for xyxy, mask, confidence, class_id, tracker_id in detections:
            detection_center = Coordinate.of_center(xyxy)
            distance = self.center.distance_to(detection_center)
            if shortest_distance is None or distance < shortest_distance or tracker_id_override == tracker_id:
                detection = Detection(
                    org_detections=detections,
                    xyxy=xyxy,
                    center=detection_center,
                    mask=mask,
                    confidence=confidence,
                    class_id=class_id,
                    tracker_id=tracker_id
                )
                shortest_distance = distance
                if tracker_id_override == tracker_id:
                    return detection
        return detection

    def _select_target(self, detections: Detections) -> Optional[Detection]:
        """ Choose a new target that is closest to the center of the screen """
        target_detection = self._get_closest_detection(detections)
        if target_detection is not None and target_detection.tracker_id is not None:
            self.target_tracker_id = target_detection.tracker_id
            self.coyote_timer = None
            self.log(f"Selected a new target ID {self.target_tracker_id}")
        return target_detection

    def _get_target(self, detections: Detections) -> Optional[Detection]:
        """ Get detection from all detections based on tracker ID """
        try:
            detections = detections[detections.tracker_id == self.target_tracker_id]
        except IndexError as e:
            return
        if len(detections) > 0:
            return Detection(
                org_detections=detections,
                xyxy=detections.xyxy[0],
                center=Coordinate.of_center(detections.xyxy[0]),
                mask=detections.mask,
                confidence=detections.confidence,
                class_id=detections.class_id,
                tracker_id=detections.tracker_id
            )

    def handle(self, frame: np.ndarray, detections: Detections) -> Optional[Detection]:
        if len(detections) == 0:
            return
        if self.tracking_enabled is False:
            self.target_tracker_id = self.coyote_timer = None
            return
        detections = detections[detections.class_id == self.target_class_id]  # filter detections by class ID
        if self.coyote_timer is not None:
            if self.coyote_timer.is_expired():  # expired coyote timer
                self.target_tracker_id = self.coyote_timer = None
                self.log(f"Couldn't find the target. Looking for new target...")
                return
            else:  # not expired coyote timer
                if self.show_boundaries:
                    cv2.circle(frame, self.center.as_tuple(), radius=self.boundary_offset, color=(255, 255, 255))
                closest_detection = self._get_closest_detection(detections, tracker_id_override=self.target_tracker_id)
                if closest_detection is not None and self.target_tracker_id == closest_detection.tracker_id:
                    self.log(f"Re-established tracking on target ID {self.target_tracker_id}")
                elif closest_detection is None or closest_detection.center.distance_to(self.center) > self.boundary_offset:
                    return closest_detection  # couldn't find the target, but we still have time left
                else:
                    self.log(f"Assuming target ID {self.target_tracker_id} changed to "
                                       f"{closest_detection.tracker_id}")
                self.target_tracker_id = closest_detection.tracker_id
                self.coyote_timer = None
                target_detection = closest_detection
        else:
            if self.target_tracker_id is None:  # no coyote timer and no target id... probably newly initialized
                target_detection = self._select_target(detections)
            else:  # no coyote timer but yes target id
                target_detection = self._get_target(detections)
                if target_detection is None:
                    self.coyote_timer = Timer.set_to_expire_in(seconds=self.coyote_seconds)
                    self.log(f"Lost track of target ID {self.target_tracker_id}! "
                             f"Got {self.coyote_seconds} seconds to find the target...")
                    return

        if target_detection is not None:
            x_vector = target_detection.center.x - self.center_x
            y_vector = target_detection.center.y - self.center_y
            if abs(x_vector) <= self.boundary_offset:
                x_vector = 0
            if abs(y_vector) <= self.boundary_offset:
                y_vector = 0
            if self.show_boundaries:
                cv2.rectangle(frame, self.boundary_top_left.as_tuple(), self.boundary_bottom_right.as_tuple(),
                              color=(255, 255, 255))
            if self.show_arrows is True:
                if x_vector < 0:
                    self.draw_arrow(frame, "left")
                elif x_vector > 0:
                    self.draw_arrow(frame, "right")
                if y_vector < 0:
                    self.draw_arrow(frame, "up")
                elif y_vector > 0:
                    self.draw_arrow(frame, "down")
            self.esp32_bridge.move_by_pixel(x_vector, y_vector)
            if self.show_center is True:
                cv2.circle(frame, target_detection.center.as_tuple(), radius=5, color=(0, 255, 0))
        return target_detection
