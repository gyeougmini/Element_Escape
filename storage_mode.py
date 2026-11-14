from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from box import make_boxes
from collision import draw_bb, push_out_offset
from hud import ElementHud
from ice import IceBlock
from kai import Kai, DIRECTION_ROWS

# 창고(storage_bg.png): 감방에서 창고 문으로 들어오면 나오는 다음 단계
STORAGE_IMAGE = 'sprite_sheet/sprite_sheet_bg/storage_bg.png'
# 통과할 수 없는 벽과 물체: storage_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
STORAGE_OBSTACLES = [
    # 외벽
    (0, 0, 1024, 135, WALL),     # 위 (냉동 보관 문, 간수실 문 포함)
    (0, 700, 1024, 768, WALL),   # 아래 (입구의 빨간 점선)
    (0, 0, 64, 768, WALL),       # 왼쪽
    (960, 0, 1024, 768, WALL),   # 오른쪽
    # 물체
    (64, 135, 318, 200, OBJECT),   # 왼쪽 위 선반
    (705, 130, 765, 188, OBJECT),  # 파란 드럼통
    (895, 335, 955, 435, OBJECT),  # 노란 드럼통
    (100, 462, 195, 483, OBJECT),  # 나무 팔레트
    (835, 508, 955, 615, OBJECT),  # 비닐로 싼 상자 더미
    (390, 655, 467, 678, OBJECT),  # 손수레
]
# 나무 상자: storage_bg.png 기준 (몸체 가운데 x, 몸체 아래쪽 끝 y). 맞닿은 상자끼리 불이 번짐
STORAGE_BOX_POSITIONS = [
    # 입구를 가둔 ㄱ자 줄: 위쪽 가로줄(왼쪽 벽부터) + 오른쪽 세로줄(아래쪽 벽까지).
    # 하나만 태우면 불이 줄을 따라 번져 길이 열림
    (90, 460), (142, 460), (194, 460), (246, 460), (298, 460), (350, 460),
    (350, 520), (350, 580), (350, 640), (350, 700),
    # 오른쪽 아래 빨간 점선 구역의 한 줄
    (634, 583), (686, 583), (738, 583),
]
STORAGE_BOX_CONTENTS = {}
# 얼음 블록: 냉동 보관 문 앞 서리 위에 한 줄. 같은 기준 (몸체 가운데 x, 몸체 아래쪽 끝 y)
ICE_POSITIONS = [(492, 235), (544, 235), (596, 235)]
KAI_START_IMAGE_POS = (160, 630)  # 시작 위치: 왼쪽 아래 입구 안쪽, HP 바에 가리지 않는 높이 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지), 없으면 처음 값


def carry_over(kai):
    """이전 단계의 카이 HP와 에너지를 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy)


def update_obstacles():
    # 상자는 타서 무너지고 얼음은 녹으면 지나갈 수 있으므로 배경, 상자, 얼음의 장애물을 매 프레임 합침
    object_obstacles = [o.get_obstacle() for o in boxes + ices]
    game_world.obstacles = (background.get_obstacles()
                            + [obstacle for obstacle in object_obstacles if obstacle])


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, boxes, ices, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, STORAGE_IMAGE, None, STORAGE_OBSTACLES)
    boxes = make_boxes(background, STORAGE_BOX_POSITIONS, STORAGE_BOX_CONTENTS)
    ices = [IceBlock(background, x, bottom) for x, bottom in ICE_POSITIONS]
    update_obstacles()
    game_world.hittables = []
    hud = ElementHud()
    kai = Kai(0, 0)
    if carried_stats:
        kai.hp, kai.energy = carried_stats
    start_x, start_y = KAI_START_IMAGE_POS
    kai.place_feet_at(background.to_canvas_x(start_x), background.to_canvas_y(start_y))
    kai.row = DIRECTION_ROWS[(0, 1)]  # 입구에서 창고 안쪽(위)을 바라봄


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
    for box in boxes:
        box.update(frame_time)
    boxes[:] = [box for box in boxes if box.alive]  # 다 타서 사라진 상자는 지움
    for ice in ices:
        ice.update(frame_time)
    ices[:] = [ice for ice in ices if ice.alive]  # 다 녹은 얼음은 지움
    update_obstacles()
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
    # 발(상자는 몸체 아래쪽 끝)이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    for actor in sorted([kai] + boxes + ices, key=lambda a: a.foot_y(), reverse=True):
        actor.draw()
    game_world.draw()
    hud.draw(kai.active_elements())
    if show_bbs:
        for bb in obstacle_bbs():
            draw_bb(bb)
        draw_bb(kai.get_bb())
