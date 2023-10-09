import base64
import os
from typing import Union, Optional

import cv2
import numpy as np
import supervision
from supervision import Detections
from ultralytics import YOLO

from common import LoggerInterface, FrameSize
from core import Esp32Bridge, CamController


class VideoHandler:
    """
    VideoHandler mainly handles receiving the camera feed and propagating the camera feed to YOLO (for object detection)
    and to the CamController (to send movement instructions to esp32 cam).

    This class responsibilities are:
    - handles and connects to a video source (esp32cam, webcam, etc.) and fetch video frames
    - handle/manage and load the YOLO (detection/tracking) models
    - uses YOLO tracking system to assign tracking ID to objects
    - renders bounding boxes and bounding box labels
    - propagate the video frame to the CamController
    """

    def __init__(self, esp32_bridge: Esp32Bridge, logger_class: Optional[LoggerInterface] = None):
        super().__init__()
        self.esp32_bridge = esp32_bridge
        self.logger_class = logger_class
        self.cam_controller = CamController(
            width=800,
            height=600,
            esp32_bridge=self.esp32_bridge,
            tracking_enabled=False,
            target_class_id=0,
            coyote_seconds=3,
            boundary_offset=100,
            show_arrows=True,
            show_boundaries=True,
            show_center=True,
            logger_class=self.logger_class
        )
        self.box_annotator = supervision.BoxAnnotator(
            thickness=2,
            text_thickness=1,
            text_scale=0.5
        )
        self.model_name = self.model = None
        self.video_source_ip = self.video_capture = None
        self.show_bounding_boxes = True

    def set_video_input(self, source: Union[str, int, None] = None) -> bool:
        if type(source) is str and source.isdigit():
            source = int(source)
        if source is None:
            self.video_source_ip = self.video_capture = None
            return True
        camera_source = f"http://{source}/camera" if type(source) is str else source
        video_capture = cv2.VideoCapture(camera_source)
        if not video_capture.isOpened():
            return False
        self.video_source_ip = source
        self.video_capture = video_capture
        return True

    def set_model(self, model_name: Optional[str] = None):
        self.model_name = model_name
        if model_name is None:
            self.model = None
        else:
            model_filepath = os.path.join(os.getcwd(), "models", f"{model_name}.pt")
            self.model = YOLO(model_filepath)

    @staticmethod
    def list_downloaded_models() -> list[str]:
        models = []
        models_dir = os.path.join(os.getcwd(), "models")
        for filename in os.listdir(models_dir):
            model_name, file_extension = os.path.splitext(filename)
            if file_extension == ".pt":
                models.append(model_name)
        return models

    def _track_target(self, frame: np.ndarray) -> np.ndarray:
        # for result in self.model.track(source="http://192.168.4.1:80/camera", show=False, stream=True, agnostic_nms=True, verbose=False):
        results = self.model.track(source=frame, show=False, stream=False, agnostic_nms=True, verbose=False)
        result = results[0]

        detections = supervision.Detections.from_ultralytics(result)

        if result.boxes.id is not None:
            detections.tracker_id = result.boxes.id.cpu().numpy().astype(int)

        our_detection = self.cam_controller.handle(frame=frame, detections=detections)
        interested_detections = our_detection.org_detections if our_detection is not None else Detections.empty()

        if self.show_bounding_boxes is True:
            labels = [
                f"{tracker_id} {self.model.model.names[class_id]} ({class_id}) {confidence:0.2f}"
                for _, _, confidence, class_id, tracker_id
                in interested_detections
            ]
            frame = self.box_annotator.annotate(
                scene=frame,
                detections=interested_detections,
                labels=labels
            )
        return frame

    def process_frame(self) -> Optional[str]:
        if self.video_capture is None:
            return

        ret, frame = self.video_capture.read()

        if ret is False or frame is None:
            return

        if self.video_source_ip == 0:  # TODO: remove this temporary code to make webcam smaller
            frame = cv2.resize(frame, (800, 600), interpolation=cv2.INTER_LINEAR)

        frame_height, frame_width, frame_channels = frame.shape
        if self.cam_controller.width != frame_width or self.cam_controller.height != frame_height:
            self.cam_controller.resize(width=frame_width, height=frame_height)

        if self.model is not None:
            frame = self._track_target(frame)

        # encode frame (image) for Flet GUI
        _, im_arr = cv2.imencode('.png', frame)
        im_b64 = base64.b64encode(im_arr)
        return im_b64.decode("utf-8")

    def get_frame_size(self) -> tuple[int, int]:
        return self.cam_controller.width, self.cam_controller.height

    def determine_frame_size(self) -> Optional[FrameSize]:
        width, height = self.get_frame_size()
        return FrameSize.determine_by(width=width, height=height)
