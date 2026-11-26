from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from collision import draw_bb, push_out_offset
from hud import ElementHud
from kai import Kai, DIRECTION_ROWS

# 하수 터널(sewer_bg.png): 수로에서 돌 다리를 만들어 열린 하수 터널 문으로 들어오면 나오는 단계
SEWER_IMAGE = 'sprite_sheet/sprite_sheet_bg/sewer_bg.png'
# 통과할 수 없는 벽과 물체: sewer_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
SEWER_OBSTACLES = [
    # 외벽
    (0, 0, 1024, 135, WALL),     # 위 (저수조 문 포함)
    (0, 705, 1024, 768, WALL),   # 아래 (오른쪽 아래 입구 포함)
    (0, 0, 64, 768, WALL),       # 왼쪽
    (960, 0, 1024, 768, WALL),   # 오른쪽
    # 아래쪽을 가로막는 벽돌 벽: 왼쪽 틈(x 128~192, 위쪽 화살표)으로만 지나갈 수 있음
    (64, 493, 128, 578, WALL),
    (192, 493, 960, 578, WALL),
    # 가운데를 가로지르는 오수 물길 (난간 포함): 철망 다리(x 637~707)로만 건널 수 있음
    (64, 312, 637, 390, WALL),
    (707, 312, 960, 390, WALL),
    # 물체
    (196, 125, 312, 188, OBJECT),  # 왼쪽 위 초록 오수 통
    (522, 120, 630, 188, OBJECT),  # 오수 기계
]
KAI_START_IMAGE_POS = (864, 650)  # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지, 물의 초능력을 얻었는지), 없으면 처음 값
# 디버깅용: 이전 단계 없이 하수 터널부터 시작하면(Element_Escape.py에서 바로 실행) 물 공격을 가진 상태로 시작
DEBUG_START_WITH_WATER = True


def carry_over(kai):
    """이전 단계의 카이 HP, 에너지, 물의 초능력을 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy, kai.water_unlocked)


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, SEWER_IMAGE, None, SEWER_OBSTACLES)
    game_world.obstacles = background.get_obstacles()
    game_world.hittables = []
    hud = ElementHud()
    kai = Kai(0, 0)
    if carried_stats:
        kai.hp, kai.energy, kai.water_unlocked = carried_stats
    elif DEBUG_START_WITH_WATER:
        kai.water_unlocked = True
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
            import title_mode  # 순환 import를 피해 여기서 불러옴
            game_framework.fade_to(title_mode)
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
            show_bbs = not show_bbs
        else:
            kai.handle_event(event)


def update(frame_time):
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
