from enum import Enum
from typing import Optional


class FrameSize(Enum):
    HQVGA = (240, 160)
    QVGA = (320, 240)
    HVGA = (480, 320)
    VGA = (640, 480)
    SVGA = (800, 600)
    XGA = (1024, 768)
    HD = (1280, 720)
    SXGA = (1280, 1024)
    UXGA = (1600, 1200)
    FHD = (1920, 1080)

    @staticmethod
    def determine_by(width: int, height: int) -> Optional["FrameSize"]:
        for frame_size in FrameSize:
            if frame_size.value == (width, height):
                return frame_size
