from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from collision import draw_bb, push_out_offset
from hud import ElementHud
from kai import Kai, DIRECTION_ROWS

# 보일러실(boiler_bg.png): 워든을 처치한 뒤 워든 맵의 보일러실 문으로 들어오면 나오는 단계
BOILER_IMAGE = 'sprite_sheet/sprite_sheet_bg/boiler_bg.png'
# 통과할 수 없는 벽과 물체: boiler_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
BOILER_OBSTACLES = [
    # 외벽
    (0, 0, 1024, 135, WALL),     # 위 (수로 문 포함)
    (0, 700, 1024, 768, WALL),   # 아래 (오른쪽 아래 입구 포함)
    (0, 0, 64, 768, WALL),       # 왼쪽
    (960, 0, 1024, 768, WALL),   # 오른쪽
    # 물체
    (72, 135, 184, 188, OBJECT),   # 왼쪽 물탱크
    (265, 135, 568, 185, OBJECT),  # 보일러
    (650, 135, 760, 188, OBJECT),  # 오른쪽 물탱크
    # 가운데를 가로지르는 방벽: 부서진 두 군데(x 192~320, 702~832)로만 지나갈 수 있음
    (64, 396, 192, 448, WALL),
    (320, 396, 702, 448, WALL),
    (832, 396, 960, 448, WALL),
    (728, 628, 790, 662, OBJECT),  # 오른쪽 아래 빨간 기름통과 상자
]
KAI_START_IMAGE_POS = (864, 650)  # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지, 물의 초능력을 얻었는지), 없으면 처음 값


def carry_over(kai):
    """이전 단계의 카이 HP, 에너지, 물의 초능력을 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy, kai.water_unlocked)


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, BOILER_IMAGE, None, BOILER_OBSTACLES)
    game_world.obstacles = background.get_obstacles()
    game_world.hittables = []
    hud = ElementHud()
    kai = Kai(0, 0)
    if carried_stats:
        kai.hp, kai.energy, kai.water_unlocked = carried_stats
    start_x, start_y = KAI_START_IMAGE_POS
    kai.place_feet_at(background.to_canvas_x(start_x), background.to_canvas_y(start_y))
    kai.row = DIRECTION_ROWS[(0, 1)]  # 입구에서 안쪽(위)을 바라봄


def finish():
    game_world.objects.clear()
    game_world.hittables = []


def handle_events():
    global show_bbs
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            import title_mode  # title_mode가 play_mode를 거쳐 이 모듈을 import하므로 순환 import를 피해 여기서 불러옴
            game_framework.fade_to(title_mode)
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
            show_bbs = not show_bbs
        else:
            kai.handle_event(event)


def update(frame_time):
    # 서 있던 자리에 장애물이 생기면 끼어서 못 움직이므로 밀어냄
    offset = push_out_offset(kai.get_bb(), obstacle_bbs())
    if offset:
        kai.x += offset[0]
        kai.y += offset[1]
    kai.update(frame_time, obstacle_bbs())
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    kai.draw()
    game_world.draw()
    hud.draw(kai.active_elements())
    if show_bbs:
        for bb in obstacle_bbs():
            draw_bb(bb)
        draw_bb(kai.get_bb())
