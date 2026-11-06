import os

from pico2d import *

import game_world
from background import Background
from collision import draw_bb
from kai import Kai

WIDTH, HEIGHT = 1280, 720

running = True
show_bbs = False  # F1로 충돌 박스 표시 토글


def handle_events():
    global running, show_bbs
    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
            show_bbs = not show_bbs
        else:
            kai.handle_event(event)


# 어느 폴더에서 실행해도 sprite_sheet/ 경로를 찾을 수 있도록 작업 폴더를 고정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

open_canvas(WIDTH, HEIGHT)

background = Background(WIDTH, HEIGHT)
kai = Kai(WIDTH // 2, HEIGHT // 2)
game_world.obstacles = background.get_obstacles()

last_time = get_time()

while running:
    handle_events()

    now = get_time()
    frame_time = now - last_time
    last_time = now

    kai.update(frame_time, background.get_bbs())
    game_world.update(frame_time)

    clear_canvas()
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
    update_canvas()
    delay(0.01)

close_canvas()
