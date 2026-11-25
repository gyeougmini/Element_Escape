import math

from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from collision import collide, draw_bb, push_out_offset
from flame import Flame
from hud import ElementHud
from kai import Kai, DIRECTION_ROWS
from rat import spawn_rats

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
# 방벽의 부서진 두 틈을 막고 타오르는 불길: 틈마다 두 칸씩. 물 공격으로만 끌 수 있음
# boiler_bg.png 기준 (left, top, right, bottom), 위아래는 방벽과 같음
FLAME_BOXES = [
    (192, 396, 256, 448), (256, 396, 320, 448),   # 왼쪽 틈
    (702, 396, 767, 448), (767, 396, 832, 448),   # 오른쪽 틈
]
# 실험 쥐: 방벽 위아래 바닥에 무작위로 3마리. 시작 위치(오른쪽 아래 입구) 근처는 피함
RAT_COUNT = 3
RAT_AREAS = [  # boiler_bg.png 기준 (left, top, right, bottom)
    (70, 200, 955, 390),   # 방벽 위쪽 (보일러 앞)
    (70, 455, 700, 690),   # 방벽 아래쪽 왼편
]
# 불길에서 이 거리(px) 안으로 쥐의 발이 들어오면 불길에 덴 것으로 봄:
# 파이어볼에 맞은 것처럼 FLAME_DAMAGE만큼 피해를 받고 불길 반대쪽으로 밀려나며 불이 붙음
FLAME_RANGE = 16
FLAME_DAMAGE = 10
KAI_START_IMAGE_POS = (864, 650)  # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지, 물의 초능력을 얻었는지), 없으면 처음 값


def carry_over(kai):
    """이전 단계의 카이 HP, 에너지, 물의 초능력을 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy, kai.water_unlocked)


def update_obstacles():
    # 불길은 꺼지면 지나갈 수 있으므로 배경과 불길의 장애물을 매 프레임 합침
    flame_obstacles = [flame.get_obstacle() for flame in flames]
    game_world.obstacles = background.get_obstacles() + [o for o in flame_obstacles if o]


def to_canvas_box(box):
    left, top, right, bottom = box
    return (background.to_canvas_x(left), background.to_canvas_y(bottom),
            background.to_canvas_x(right), background.to_canvas_y(top))


def touching_flame(rat):
    """쥐의 발 가까이에 있는 타는 불길, 없으면 None"""
    left, bottom, right, top = rat.get_bb()
    reach = (left - FLAME_RANGE, bottom - FLAME_RANGE, right + FLAME_RANGE, top + FLAME_RANGE)
    for flame in flames:
        if flame.is_burning() and collide(reach, flame.get_bb()):
            return flame
    return None


def burn_by_flame(rat, flame):
    # 불길 가운데에서 쥐 쪽으로 밀어냄 (파이어볼에 맞은 것과 같은 반응: 피해, 밀려남, 불붙음)
    fl, fb, fr, ft = flame.get_bb()
    rl, rb, rr, rt = rat.get_bb()
    dx, dy = (rl + rr) / 2 - (fl + fr) / 2, (rb + rt) / 2 - (fb + ft) / 2
    length = math.hypot(dx, dy)
    dir_x, dir_y = (dx / length, dy / length) if length else (0, -1)
    rat.on_fireball_hit(dir_x, dir_y, FLAME_DAMAGE)


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, flames, rats, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, BOILER_IMAGE, None, BOILER_OBSTACLES)
    flames = [Flame(background, box) for box in FLAME_BOXES]
    update_obstacles()
    rats = spawn_rats(RAT_COUNT, [to_canvas_box(area) for area in RAT_AREAS], obstacle_bbs())
    game_world.hittables = list(rats)
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
    for flame in flames:
        flame.update(frame_time)
    flames[:] = [flame for flame in flames if flame.alive]  # 다 꺼진 불길은 지움
    update_obstacles()
    # 서 있던 자리에 장애물이 생기면 끼어서 못 움직이므로 밀어냄
    for actor in [kai] + rats:
        offset = push_out_offset(actor.get_bb(), obstacle_bbs())
        if offset:
            actor.x += offset[0]
            actor.y += offset[1]
    kai.update(frame_time, obstacle_bbs())
    for rat in rats:
        rat.update(frame_time, obstacle_bbs(), kai)
        rat.touch(kai)
        # 불길에 닿은 쥐는 데어서 피해를 받고 밀려나며 불이 붙음 (밀려나는 동안은 다시 데지 않음)
        if not rat.is_dead() and not rat.is_knocked_back():
            flame = touching_flame(rat)
            if flame:
                burn_by_flame(rat, flame)
    # 기절 연출이 끝난 쥐는 지우고, HP가 남은 쥐만 공격에 맞도록 함
    rats[:] = [rat for rat in rats if rat.alive]
    game_world.hittables = [rat for rat in rats if not rat.is_dead()]
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    # 발(불길은 아래쪽 끝)이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    for actor in sorted([kai] + rats + flames, key=lambda a: a.foot_y(), reverse=True):
        actor.draw()
    game_world.draw()
    hud.draw(kai.active_elements())
    if show_bbs:
        for bb in obstacle_bbs():
            draw_bb(bb)
        draw_bb(kai.get_bb())
        for rat in rats:
            draw_bb(rat.get_bb())
            draw_bb(rat.get_hit_bb())
            rat.draw_chase_range()
