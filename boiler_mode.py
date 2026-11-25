import math

from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from bat import spawn_bats
from collision import collide, draw_bb, push_out_offset
from flame import Flame
from hud import ElementHud
from kai import Kai, DIRECTION_ROWS
from rat import spawn_rats
from sliding_door import SlidingDoor
from water_tank import WaterTank

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
    (265, 135, 568, 185, OBJECT),  # 보일러
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
# 박쥐: 날아다니므로 방벽 위아래 어디에든 무작위로 3마리. 방 안쪽 바닥 범위 안에서만 날아다님
BAT_COUNT = 3
BAT_AREAS = [(90, 200, 940, 680)]      # 처음 놓이는 범위 (boiler_bg.png 기준 (left, top, right, bottom))
BAT_BOUNDS = (70, 150, 954, 694)       # 날아다닐 수 있는 범위 (그림자 가운데 기준)
# 위쪽의 두 물통: 물 공격을 맞힐 때마다 물이 조금씩 차오르고, 둘 다 차면 수로 문이 열림
# (받침대, 물이 차오르는 유리관 안쪽, 다 차면 초록으로 바뀌는 받침대의 두 불빛), 모두 (left, top, right, bottom)
WATER_TANKS = [
    ((72, 135, 184, 188), (80, 38, 176, 126), [(84, 164, 90, 170), (166, 164, 172, 170)]),     # 왼쪽
    ((650, 135, 760, 188), (656, 38, 752, 126), [(660, 164, 666, 170), (742, 164, 748, 170)]),  # 오른쪽
]
# 오른쪽 위 수로 문: 배경에 그려진 두 짝 미닫이 문과 가운데 갈라지는 x
CANAL_DOOR_BOX = (824, 76, 904, 128)
CANAL_DOOR_SEAM_X = 864
KAI_START_IMAGE_POS = (864, 650)  # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지, 물의 초능력을 얻었는지), 없으면 처음 값
# 디버깅용: 이전 단계 없이 보일러실부터 시작하면(Element_Escape.py에서 바로 실행) 물 공격을 가진 상태로 시작
# 워든 맵을 거쳐 들어오면 넘겨받은 값을 그대로 쓰므로 실제 게임 흐름에는 영향이 없음
DEBUG_START_WITH_WATER = True


def carry_over(kai):
    """이전 단계의 카이 HP, 에너지, 물의 초능력을 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy, kai.water_unlocked)


def update_obstacles():
    # 불길은 꺼지면 지나갈 수 있으므로 배경, 물통, 불길의 장애물을 매 프레임 합침
    object_obstacles = [o.get_obstacle() for o in tanks + flames]
    game_world.obstacles = background.get_obstacles() + [o for o in object_obstacles if o]


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
    global background, flames, tanks, canal_door, rats, bats, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, BOILER_IMAGE, None, BOILER_OBSTACLES)
    flames = [Flame(background, box) for box in FLAME_BOXES]
    tanks = [WaterTank(background, *tank) for tank in WATER_TANKS]
    canal_door = SlidingDoor(background, CANAL_DOOR_BOX, CANAL_DOOR_SEAM_X)
    update_obstacles()
    rats = spawn_rats(RAT_COUNT, [to_canvas_box(area) for area in RAT_AREAS], obstacle_bbs())
    start = (background.to_canvas_x(KAI_START_IMAGE_POS[0]), background.to_canvas_y(KAI_START_IMAGE_POS[1]))
    bats = spawn_bats(BAT_COUNT, [to_canvas_box(area) for area in BAT_AREAS], to_canvas_box(BAT_BOUNDS), start)
    game_world.hittables = rats + bats
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
    for tank in tanks:
        tank.update(frame_time)
    # 두 물통에 물이 다 차면 수로 문이 열림
    if all(tank.is_full() for tank in tanks):
        canal_door.open()
    canal_door.update(frame_time)
    update_obstacles()
    # 서 있던 자리에 장애물이 생기면 끼어서 못 움직이므로 밀어냄
    # (날고 있는 박쥐는 벽 위에 있어도 되므로 바닥에 떨어진 박쥐만)
    for actor in [kai] + rats + [bat for bat in bats if not bat.is_flying()]:
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
    # 박쥐: 날 때는 벽 위로도 다니고, 물에 맞아 바닥에 떨어지면 벽에 막히며 느려짐
    for bat in bats:
        bat.update(frame_time, obstacle_bbs(), kai)
        bat.touch(kai)
        # 바닥에 떨어진 박쥐도 불길에 닿으면 덴다 (날고 있으면 불길 위를 지나감)
        if not bat.is_dead() and not bat.is_flying() and not bat.is_knocked_back():
            flame = touching_flame(bat)
            if flame:
                burn_by_flame(bat, flame)
    # 쓰러지는 연출이 끝난 적은 지우고, HP가 남은 적만 공격에 맞도록 함
    rats[:] = [rat for rat in rats if rat.alive]
    bats[:] = [bat for bat in bats if bat.alive]
    game_world.hittables = [enemy for enemy in rats + bats if not enemy.is_dead()]
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    canal_door.draw()       # 열리는 수로 문과
    for tank in tanks:
        tank.draw()         # 물통에 차오르는 물 (둘 다 배경 그림의 일부라서 배경 바로 위에 그림)
    # 발(불길은 아래쪽 끝)이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    # 날고 있는 박쥐는 공중에 있으므로 모든 것 위에 그림
    grounded = [kai] + rats + flames + [bat for bat in bats if not bat.is_flying()]
    for actor in sorted(grounded, key=lambda a: a.foot_y(), reverse=True):
        actor.draw()
    for bat in sorted([bat for bat in bats if bat.is_flying()], key=lambda a: a.foot_y(), reverse=True):
        bat.draw()
    game_world.draw()
    hud.draw(kai.active_elements())
    if show_bbs:
        for bb in obstacle_bbs():
            draw_bb(bb)
        draw_bb(kai.get_bb())
        for enemy in rats + bats:
            draw_bb(enemy.get_bb())
            draw_bb(enemy.get_hit_bb())
            enemy.draw_chase_range()
