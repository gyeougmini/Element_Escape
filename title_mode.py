from pico2d import *

import game_framework
import intro_mode
from button import Button

START_BUTTON_Y = 200
QUIT_BUTTON_Y = 120
OPTION_BUTTON_MARGIN = 50  # 오른쪽 위 모서리에서 설정 버튼 중심까지의 거리


def start_game():
    game_framework.fade_to(intro_mode)


def open_option():
    # TODO: 설정 화면이 정해지면 여기서 전환
    pass


def init():
    global image, buttons
    image = load_image('sprite_sheet/sprite_sheet_bg/title_bg.png')
    width, height = get_canvas_width(), get_canvas_height()
    buttons = [
        Button('sprite_sheet/sprite_sheet_bg/title_bg_start.png', 256, 60, width // 2, START_BUTTON_Y, start_game),
        Button('sprite_sheet/sprite_sheet_bg/title_bg_quit.png', 256, 60, width // 2, QUIT_BUTTON_Y, game_framework.quit),
        Button('sprite_sheet/sprite_sheet_bg/title_bg_option.png', 64, 64,
               width - OPTION_BUTTON_MARGIN, height - OPTION_BUTTON_MARGIN, open_option),
    ]


def finish():
    pass


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            game_framework.quit()
        else:
            for button in buttons:
                button.handle_event(event)


def update(frame_time):
    for button in buttons:
        button.update(frame_time)


def draw():
    width, height = get_canvas_width(), get_canvas_height()
    image.draw(width // 2, height // 2, width, height)
    for button in buttons:
        button.draw()
