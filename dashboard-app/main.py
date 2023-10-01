import flet as ft

import gui


def main(page: ft.Page):
    page.window_width = 1600
    page.window_height = 1100
    page.window_top = 100
    page.window_left = 50
    page.padding = 50
    gui.cam_gui.initialize_theme(page=page)
    page.add(
        gui.PARENT_CONTAINER
    )


if __name__ == '__main__':
    ft.app(target=main)
