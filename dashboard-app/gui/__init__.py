import flet as ft

from core.esp32_bridge import Esp32Bridge
from gui.camera_gui import CameraGui
from gui.config_gui import ConfigGui
from gui.logging_gui import LoggingGui
from gui.tracker_gui import TrackerGui
from logic import VideoHandler


esp32_bridge = Esp32Bridge()
video_handler = VideoHandler(esp32_bridge=esp32_bridge)

cam_gui = CameraGui(video_handler=video_handler)
config_gui = ConfigGui(video_handler=video_handler)
tracker_gui = TrackerGui(video_handler=video_handler)
logging_gui = LoggingGui(video_handler=video_handler)


PARENT_CONTAINER = ft.Container(
    expand=True,
    alignment=ft.alignment.top_center,
    content=ft.Row([
        ft.Container(  # TODO: fix so card is not expanding with the container
            expand=3,
            margin=ft.margin.only(right=20),
            content=ft.Card(
                elevation=30,
                content=ft.Container(
                    bgcolor=ft.colors.WHITE24,
                    padding=20,
                    border_radius=ft.border_radius.all(20),
                    content=cam_gui
                )
            )
        ),
        ft.Tabs(
            expand=2,
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    text="Camera",
                    icon=ft.icons.VIDEOCAM,
                    content=ft.Container(alignment=ft.alignment.center, content=config_gui),
                ),
                ft.Tab(
                    text="Tracking",
                    icon=ft.icons.IMAGE_SEARCH,
                    content=ft.Container(alignment=ft.alignment.center, content=ft.Column([tracker_gui])),
                ),
                ft.Tab(
                    text="Logs",
                    icon=ft.icons.NOTES,
                    content=ft.Container(alignment=ft.alignment.center, content=logging_gui),
                )
            ]
        )
    ])
)
