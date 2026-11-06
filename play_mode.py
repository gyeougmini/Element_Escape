from pico2d import *

import game_framework
import game_world
from background import Background
from collision import draw_bb
from kai import Kai

show_bbs = False  # F1로 충돌 박스 표시 토글
KAI_START_IMAGE_POS = (560, 305)  # 시작 위치: cell_bg.png 바닥의 '07' 글자 (위에서부터의 픽셀 좌표)


def init():
    global background, kai
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height)
    kai = Kai(0, 0)
    start_x, start_y = KAI_START_IMAGE_POS
    kai.place_feet_at(background.to_canvas_x(start_x), background.to_canvas_y(start_y))
    game_world.obstacles = background.get_obstacles()


def finish():
    game_world.objects.clear()


def handle_events():
    global show_bbs
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            import title_mode  # title_mode가 play_mode를 import하므로 순환 import를 피해 여기서 불러옴
            game_framework.fade_to(title_mode)
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
            show_bbs = not show_bbs
        else:
            kai.handle_event(event)


def update(frame_time):
    kai.update(frame_time, background.get_bbs())
    game_world.update(frame_time)


def draw():
    background.draw()
    # 카이가 창살 뒤(감방 안)에 있으면 창살이 카이를 가리도록 나중에 그림
    if kai.foot_y() > background.gate_base_y:
        kai.draw()
        background.draw_gate()
    else:
        background.draw_gate()
        kai.draw()
    # 파이어볼과 불꽃 이펙트는 항상 맨 위에 그림
    game_world.draw()
    if show_bbs:
        background.draw_bbs()
        draw_bb(kai.get_bb())
        for o in game_world.objects:
            if hasattr(o, 'get_bb'):
                draw_bb(o.get_bb())
