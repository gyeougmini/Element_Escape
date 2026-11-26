from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from brute import Brute
from drone import Drone
from potion import Potion
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
# 구역과 그 사이의 통로 (sewer_bg.png 기준 y는 위에서부터): 아래쪽부터 차례로 이어짐
#   (구역 이름, 위쪽 끝 y, 아래쪽 끝 y)
ZONES = [('bottom', 578, 705), ('middle', 390, 493), ('top', 135, 312)]
#   두 구역 사이의 통로: (지나갈 수 있는 x 범위 왼쪽, 오른쪽). 위아래 끝은 두 구역 사이의 벽/물길
PASSAGES = [(128, 192),   # bottom <-> middle: 벽돌 벽의 틈
            (637, 707)]   # middle <-> top: 오수 물길 위 철망 다리
PASSAGE_MARGIN = 26    # 통로를 지날 때 양쪽 끝에서 이만큼 안쪽으로 걸음 (px)
PASSAGE_STEP_OUT = 24  # 통로 앞에서 기다리는 자리: 통로 끝에서 이만큼 떨어진 곳 (px)
# 하수 변이체 2마리 (발 가운데 x, 발 y, 순찰 왼쪽 끝 x, 오른쪽 끝 x, 처음 걷는 방향), sewer_bg.png 기준
BRUTES = [
    (605, 254, 100, 920, -1),   # 위쪽 구역 (오수 기계 앞)
    (475, 454, 100, 920, 1),    # 가운데 구역 (물길과 벽돌 벽 사이)
]
# 전기 드론 2마리: 날아다니므로 벽과 물길 위로도 다님 (그림자 가운데 x, y)
DRONES = [(146, 225), (473, 619)]
DRONE_BOUNDS = (70, 140, 954, 700)  # 날아다닐 수 있는 범위 (그림자 가운데 기준, (left, top, right, bottom))
# 바닥에 놓인 물약 (종류, 그림자 가운데 x, 그림자 아래쪽 끝 y)
POTIONS = [('hp', 84, 690), ('ep', 930, 482)]
KAI_START_IMAGE_POS = (864, 650)  # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지, 물의 초능력을 얻었는지), 없으면 처음 값
# 디버깅용: 이전 단계 없이 하수 터널부터 시작하면(Element_Escape.py에서 바로 실행) 물 공격을 가진 상태로 시작
DEBUG_START_WITH_WATER = True


def carry_over(kai):
    """이전 단계의 카이 HP, 에너지, 물의 초능력을 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy, kai.water_unlocked)


def to_canvas_box(box):
    left, top, right, bottom = box
    return (background.to_canvas_x(left), background.to_canvas_y(bottom),
            background.to_canvas_x(right), background.to_canvas_y(top))


def zone_of(y):
    """캔버스 y가 몇 번째 구역(ZONES의 순서)인지. 두 구역 사이의 통로 위면 x.5 (예: 0.5는 벽돌 벽의 틈)"""
    image_y = to_image_y(y)
    for i, (_, top, bottom) in enumerate(ZONES):
        if top <= image_y <= bottom:
            return i
    for i in range(len(ZONES) - 1):
        if ZONES[i + 1][2] < image_y < ZONES[i][1]:
            return i + 0.5
    return 0 if image_y > ZONES[0][2] else len(ZONES) - 1


def to_image_y(y):
    return 768 - y * 768 / background.height


def passage_points(i):
    """i번째 통로(구역 i와 i+1 사이)의 (가운데 x, 아래쪽 구역 쪽 대기 자리 y, 위쪽 구역 쪽 대기 자리 y), 캔버스 좌표"""
    left, right = PASSAGES[i]
    center_x = background.to_canvas_x((left + right) / 2)
    below_y = background.to_canvas_y(ZONES[i][1]) - PASSAGE_STEP_OUT
    above_y = background.to_canvas_y(ZONES[i + 1][2]) + PASSAGE_STEP_OUT
    return center_x, below_y, above_y


def in_passage_lane(i, x):
    left, right = PASSAGES[i]
    return background.to_canvas_x(left) + PASSAGE_MARGIN <= x <= background.to_canvas_x(right) - PASSAGE_MARGIN


def route(x, y, tx, ty):
    """하수 변이체가 (x, y)에서 (tx, ty)로 가려면 먼저 향할 곳: 다른 구역이면 사이의 통로(벽 틈, 철망 다리)를 거침"""
    here, there = zone_of(y), zone_of(ty)
    if here == there or abs(here - there) < 1 and (here % 1 or there % 1) and in_passage_lane(int(min(here, there)), x):
        return tx, ty
    step = 1 if there > here else -1
    if here % 1:  # 통로 위: 가는 쪽 구역으로 빠져나감
        i = int(here)
        center_x, below_y, above_y = passage_points(i)
        return center_x, (above_y if step > 0 else below_y)
    i = int(here) if step > 0 else int(here) - 1  # 지나야 할 통로
    center_x, below_y, above_y = passage_points(i)
    near_y, far_y = (below_y, above_y) if step > 0 else (above_y, below_y)
    if in_passage_lane(i, x):
        return center_x, far_y  # 통로 줄에 들어섰으면 곧장 건넘
    return center_x, near_y     # 통로 앞으로


def sight(x, y, tx, ty):
    """높은 벽돌 벽(아래쪽 구역과 가운데 구역 사이) 너머는 틈으로만 보임. 오수 물길은 낮아서 너머가 보임"""
    a, b = zone_of(y), zone_of(ty)
    if (a < 0.5) == (b < 0.5) or a == 0.5 or b == 0.5:
        return True
    # 시선이 벽을 지나는 높이에서 틈 안을 지나면 보임
    wall_y = background.to_canvas_y((ZONES[0][1] + ZONES[1][2]) / 2)
    t = (wall_y - y) / (ty - y) if ty != y else 0
    cross_x = x + (tx - x) * t
    left, right = PASSAGES[0]
    return background.to_canvas_x(left) <= cross_x <= background.to_canvas_x(right)


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, brutes, drones, potions, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, SEWER_IMAGE, None, SEWER_OBSTACLES)
    game_world.obstacles = background.get_obstacles()
    brutes = [Brute(background.to_canvas_x(x), background.to_canvas_y(y),
                    background.to_canvas_x(left), background.to_canvas_x(right), start_dir, route, sight)
              for x, y, left, right, start_dir in BRUTES]
    drones = [Drone(background.to_canvas_x(x), background.to_canvas_y(y), to_canvas_box(DRONE_BOUNDS))
              for x, y in DRONES]
    potions = [Potion(kind, background.to_canvas_x(x), background.to_canvas_y(y)) for kind, x, y in POTIONS]
    game_world.hittables = brutes + drones
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
    for brute in brutes:
        brute.update(frame_time, obstacle_bbs(), kai)
        brute.touch(kai)
    for drone in drones:
        drone.update(frame_time, obstacle_bbs(), kai)
    for potion in potions:
        potion.update(frame_time, kai)
    potions[:] = [potion for potion in potions if potion.alive]
    drones[:] = [drone for drone in drones if drone.alive]
    # 하수 변이체는 죽지 않으므로 늘 공격에 맞음 (피해는 없고 불타는/젖음 상태만)
    game_world.hittables = brutes + [drone for drone in drones if not drone.is_dead()]
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    # 발이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함. 드론은 공중에 있으므로 모든 것 위에 그림
    for actor in sorted([kai] + brutes + potions, key=lambda a: a.foot_y(), reverse=True):
        actor.draw()
    for drone in sorted(drones, key=lambda a: a.foot_y(), reverse=True):
        drone.draw()
    game_world.draw()
    hud.draw(kai.active_elements())
    if show_bbs:
        for bb in obstacle_bbs():
            draw_bb(bb)
        draw_bb(kai.get_bb())
        for enemy in brutes + drones:
            draw_bb(enemy.get_bb())
            draw_bb(enemy.get_hit_bb())
            enemy.draw_chase_range()
        for o in game_world.objects:
            if hasattr(o, 'draw_range'):
                o.draw_range()  # 증기가 시야를 가리는 범위
