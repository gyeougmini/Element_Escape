from pico2d import *

import game_framework
import game_world
from background import Background
from collision import draw_bb
from kai import Kai
from notice import Notice

show_bbs = False  # F1로 충돌 박스 표시 토글
KAI_START_IMAGE_POS = (560, 305)  # 시작 위치: cell_bg.png 바닥의 '07' 글자 (위에서부터의 픽셀 좌표)
# 시작 안내: 화면이 밝아진 뒤 나타나고, 안내가 사라질 때까지 모든 입력을 막음
MOVE_NOTICE_TEXT = '플레이어 이동: WASD'
MOVE_NOTICE_DELAY = 0.5  # game_framework.FADE_TIME과 같게 해서 화면이 다 밝아진 뒤 등장
MOVE_NOTICE_HOLD = 2.0
LIGHTS_OFF_DELAY = 3.0  # 안내가 사라지고 이 시간(초)이 지나면 조명이 꺼짐 (cell_dark_bg.png로 교체)


def init():
    global background, kai, notice, after_notice_time
    notice = Notice(MOVE_NOTICE_TEXT, MOVE_NOTICE_HOLD, MOVE_NOTICE_DELAY)
    after_notice_time = 0.0
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
        elif not notice.is_done():
            continue  # 안내 중에는 키보드/마우스 입력을 모두 무시
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            import title_mode  # title_mode가 play_mode를 import하므로 순환 import를 피해 여기서 불러옴
            game_framework.fade_to(title_mode)
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
            show_bbs = not show_bbs
        else:
            kai.handle_event(event)


def update(frame_time):
    global after_notice_time
    notice.update(frame_time)
    if notice.is_done():
        after_notice_time += frame_time
        if after_notice_time >= LIGHTS_OFF_DELAY:
            background.set_dark(True)
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
    notice.draw()
    if show_bbs:
        background.draw_bbs()
        draw_bb(kai.get_bb())
        for o in game_world.objects:
            if hasattr(o, 'get_bb'):
                draw_bb(o.get_bb())
