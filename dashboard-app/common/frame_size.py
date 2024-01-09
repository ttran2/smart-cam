from enum import Enum
from typing import Optional


class FrameSize(Enum):
    # https://github.com/shariltumin/esp32-cam-micropython-2022/blob/main/firmwares-20230717/Note.md
    S_96X96 = (1, 96, 96)
    QQVGA = (2, 160, 120)
    QCIF = (3, 176, 144)
    HQVGA = (4, 240, 176)
    S_240X240 = (5, 240, 240)
    QVGA = (6, 320, 240)
    CIF = (7, 400, 296)
    HVGA = (8, 480, 320)
    VGA = (9, 640, 480)
    SVGA = (10, 800, 600)
    XGA = (11, 1024, 768)
    HD = (12, 1280, 720)
    SXGA = (13, 1280, 1024)
    UXGA = (14, 1600, 1200)
    FHD = (15, 1920, 1080)

    @property
    def key(self) -> int:
        return self.value[0]

    @property
    def width(self) -> int:
        return self.value[1]

    @property
    def height(self) -> int:
        return self.value[2]

    @staticmethod
    def determine_by(width: int, height: int) -> Optional["FrameSize"]:
        for frame_size in FrameSize:
            if frame_size.value[1:] == (width, height):
                return frame_size
