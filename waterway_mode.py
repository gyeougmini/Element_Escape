from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from bat import spawn_bats
from brute import Brute
from flame import Flame
from rat import spawn_rats
from sliding_door import SlidingDoor
from collision import collide, draw_bb, push_out_offset
from glass_bridge import GlassBridge
from hud import ElementHud
from kai import Kai, DIRECTION_ROWS

# 수로(waterway_bg.png): 보일러실의 두 물통을 채워 열린 수로 문으로 들어오면 나오는 단계
WATERWAY_IMAGE = 'sprite_sheet/sprite_sheet_bg/waterway_bg.png'
# 통과할 수 없는 벽과 물체: waterway_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
WATERWAY_OBSTACLES = [
    # 외벽
    (0, 0, 1024, 135, WALL),     # 위 (하수 터널 문 포함)
    (0, 705, 1024, 768, WALL),   # 아래 (오른쪽 아래 입구 포함)
    (0, 0, 64, 768, WALL),       # 왼쪽
    (960, 0, 1024, 768, WALL),   # 오른쪽
    # 가운데를 가로지르는 물길 (난간 포함): 유리판 자리(난간 기둥 사이)만 빼고 막음
    (64, 318, 460, 455, WALL),
    (566, 318, 960, 455, WALL),
    # 물체
    (330, 135, 440, 188, OBJECT),  # 왼쪽 위 기계
    (585, 135, 695, 188, OBJECT),  # 파란 탱크
    (708, 452, 764, 512, OBJECT),  # 물길 아래 제어 상자
    (840, 600, 882, 626, OBJECT),  # 오른쪽 아래 나무 상자
]
# 물길 가운데 유리판: 불(용암구체) 공격에 맞으면 급랭되어 돌 발판이 되고, 그 위로 물길을 건널 수 있음
GLASS_BOX = (448, 332, 576, 448)   # 유리판 그림의 자리
BRIDGE_PATH = (460, 318, 566, 455)  # 유리판이 막고 있는 길 (위아래 난간 기둥 사이)
BRIDGE_MARGIN = 30   # 다리로 건널 때 기둥에 걸리지 않도록 다리 양쪽 끝에서 이만큼 안쪽으로 걸음 (px)
BRIDGE_STEP_OUT = 24  # 다리 앞에서 기다리는 자리: 물길 끝에서 이만큼 떨어진 곳 (px)
# 하수 변이체(brute) 2마리: 물길 건너편(위쪽)에서 각자의 줄을 좌우로 순찰. 죽지 않으므로 증기로 시선을 가려 피해야 함
# (발 가운데 x, 발 y, 순찰 왼쪽 끝 x, 오른쪽 끝 x, 처음 걷는 방향), 모두 waterway_bg.png 기준
BRUTES = [
    (300, 222, 100, 920, 1),    # 위쪽 줄 (기계들 앞)
    (760, 292, 100, 920, -1),   # 아래쪽 줄 (물길 난간 앞)
]
# 실험 쥐 2마리: 물길 양쪽 바닥에 무작위로 (waterway_bg.png 기준 (left, top, right, bottom)). 물을 건너지 못함
RAT_COUNT = 2
RAT_AREAS = [
    (70, 195, 955, 310),   # 건너편 (기계들 앞)
    (70, 465, 700, 690),   # 입구 쪽 (오른쪽 아래 입구 근처는 뺌)
]
# 변이 박쥐 2마리: 날아다니므로 물길 위도 자유롭게 오감. 방 안쪽 전체를 날아다님
BAT_COUNT = 2
BAT_AREAS = [(90, 150, 940, 680)]     # 처음 놓이는 범위
BAT_BOUNDS = (70, 140, 954, 700)      # 날아다닐 수 있는 범위 (그림자 가운데 기준)
# 시작 자리(오른쪽 아래 입구) 왼쪽을 막고 타오르는 불길: 제어 상자 아래 파이프를 따라 세로로 세 칸
# 제어 상자와 함께 오른쪽 아래 구역을 막으므로 물 공격으로 꺼야 나갈 수 있음
# waterway_bg.png 기준 (left, top, right, bottom), 가로는 제어 상자 폭과 같음
FLAME_BOXES = [
    (708, 512, 764, 576),
    (708, 576, 764, 640),
    (708, 640, 764, 705),
]
# 불길에서 이 거리(px) 안으로 쥐나 떨어진 박쥐의 발이 들어오면 데어서 피해를 받고 밀려나며 불이 붙음 (보일러실과 같음)
FLAME_RANGE = 16
FLAME_DAMAGE = 10
# 오른쪽 위 하수 터널 문: 배경에 그려진 두 짝 미닫이 문과 가운데 갈라지는 x. 돌 다리를 만드는 순간 열림
TUNNEL_DOOR_BOX = (824, 77, 904, 128)
TUNNEL_DOOR_SEAM_X = 864
KAI_START_IMAGE_POS = (864, 650)  # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지, 물의 초능력을 얻었는지), 없으면 처음 값
# 디버깅용: 이전 단계 없이 수로부터 시작하면(Element_Escape.py에서 바로 실행) 물 공격을 가진 상태로 시작
DEBUG_START_WITH_WATER = True


def carry_over(kai):
    """이전 단계의 카이 HP, 에너지, 물의 초능력을 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy, kai.water_unlocked)


def update_obstacles():
    # 유리판이 돌로 굳거나 불길이 꺼지면 지나갈 수 있으므로 매 프레임 합침
    object_obstacles = [o.get_obstacle() for o in [bridge] + flames]
    game_world.obstacles = background.get_obstacles() + [o for o in object_obstacles if o]


def touching_flame(enemy):
    """적의 발 가까이에 있는 타는 불길, 없으면 None"""
    left, bottom, right, top = enemy.get_bb()
    reach = (left - FLAME_RANGE, bottom - FLAME_RANGE, right + FLAME_RANGE, top + FLAME_RANGE)
    for flame in flames:
        if flame.is_burning() and collide(reach, flame.get_bb()):
            return flame
    return None


def burn_by_flame(enemy, flame):
    # 불길 가운데에서 적 쪽으로 밀어냄 (파이어볼에 맞은 것과 같은 반응: 피해, 밀려남, 불붙음)
    fx, fy = bb_center(flame.get_bb())
    ex, ey = bb_center(enemy.get_bb())
    dx, dy = ex - fx, ey - fy
    length = (dx * dx + dy * dy) ** 0.5
    dir_x, dir_y = (dx / length, dy / length) if length else (0, -1)
    enemy.on_fireball_hit(dir_x, dir_y, FLAME_DAMAGE)


def bank(y):
    """캔버스 y가 물길의 어느 쪽인지: 'up'(건너편), 'down'(입구 쪽), 'bridge'(물길 위, 다리)"""
    left, bottom, right, top = bridge.path_bb
    if y > top:
        return 'up'
    if y < bottom:
        return 'down'
    return 'bridge'


def route(x, y, tx, ty):
    """하수 변이체가 (x, y)에서 (tx, ty)로 가려면 먼저 향할 곳. 물길 건너편은 돌 다리로만 갈 수 있음 (없으면 None)"""
    from_bank, to_bank = bank(y), bank(ty)
    if from_bank == to_bank:
        return tx, ty
    if not bridge.is_stone():
        return None
    left, bottom, right, top = bridge.path_bb
    lane_left, lane_right = left + BRIDGE_MARGIN, right - BRIDGE_MARGIN
    center_x = (left + right) / 2
    in_lane = lane_left <= x <= lane_right
    if to_bank == 'bridge':
        # 다리 위의 카이: 다리 줄에 들어섰으면 곧장, 아니면 다리 앞으로
        if in_lane:
            return min(max(tx, lane_left), lane_right), ty
        return center_x, (top + BRIDGE_STEP_OUT if from_bank == 'up' else bottom - BRIDGE_STEP_OUT)
    exit_y = top + BRIDGE_STEP_OUT if to_bank == 'up' else bottom - BRIDGE_STEP_OUT
    if from_bank == 'bridge' or in_lane:
        return center_x, exit_y  # 다리를 따라 곧장 건넘
    return center_x, (top + BRIDGE_STEP_OUT if from_bank == 'up' else bottom - BRIDGE_STEP_OUT)  # 다리 앞으로


def can_walk_to(enemy, target):
    """쥐나 바닥에 떨어진 박쥐가 target에게 걸어갈 수 있는지: 물길의 같은 쪽이거나 어느 한쪽이 다리 위에 있을 때만
    (쥐와 박쥐는 다리로 돌아가는 길을 찾지 못하므로 건너편의 카이는 쫓지 않음)"""
    _, enemy_y = bb_center(enemy.get_bb())
    _, target_y = bb_center(target.get_bb())
    banks = (bank(enemy_y), bank(target_y))
    return banks[0] == banks[1] or 'bridge' in banks


def to_canvas_box(box):
    left, top, right, bottom = box
    return (background.to_canvas_x(left), background.to_canvas_y(bottom),
            background.to_canvas_x(right), background.to_canvas_y(top))


def bb_center(bb):
    left, bottom, right, top = bb
    return (left + right) / 2, (bottom + top) / 2


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, bridge, flames, tunnel_door, brutes, rats, bats, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, WATERWAY_IMAGE, None, WATERWAY_OBSTACLES)
    bridge = GlassBridge(background, GLASS_BOX, BRIDGE_PATH)
    flames = [Flame(background, box) for box in FLAME_BOXES]
    tunnel_door = SlidingDoor(background, TUNNEL_DOOR_BOX, TUNNEL_DOOR_SEAM_X)
    update_obstacles()
    brutes = [Brute(background.to_canvas_x(x), background.to_canvas_y(y),
                    background.to_canvas_x(left), background.to_canvas_x(right), start_dir, route)
              for x, y, left, right, start_dir in BRUTES]
    start = (background.to_canvas_x(KAI_START_IMAGE_POS[0]), background.to_canvas_y(KAI_START_IMAGE_POS[1]))
    rats = spawn_rats(RAT_COUNT, [to_canvas_box(area) for area in RAT_AREAS], obstacle_bbs())
    bats = spawn_bats(BAT_COUNT, [to_canvas_box(area) for area in BAT_AREAS], to_canvas_box(BAT_BOUNDS), start)
    for enemy in rats + bats:
        enemy.can_reach = can_walk_to
    # 변이체는 죽지 않으므로 늘 공격에 맞음 (피해는 없고 불타는/젖음 상태만)
    game_world.hittables = brutes + rats + bats
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
    bridge.update(frame_time)
    for flame in flames:
        flame.update(frame_time)
    flames[:] = [flame for flame in flames if flame.alive]  # 다 꺼진 불길은 지움
    # 돌 다리를 만드는 순간(유리판이 불에 맞아 굳기 시작하면) 하수 터널 문이 열림
    if not bridge.is_glass():
        tunnel_door.open()
    tunnel_door.update(frame_time)
    update_obstacles()
    # 서 있던 자리에 장애물이 생기면 끼어서 못 움직이므로 밀어냄
    # (물에 맞아 떨어진 박쥐가 물길 위였으면 가까운 쪽 바닥으로. 날고 있는 박쥐는 물 위에 있어도 됨)
    for actor in [kai] + rats + [bat for bat in bats if not bat.is_flying()]:
        offset = push_out_offset(actor.get_bb(), obstacle_bbs())
        if offset:
            actor.x += offset[0]
            actor.y += offset[1]
    kai.update(frame_time, obstacle_bbs())
    for brute in brutes:
        brute.update(frame_time, obstacle_bbs(), kai)
        brute.touch(kai)
    for enemy in rats + bats:
        enemy.update(frame_time, obstacle_bbs(), kai)
        enemy.touch(kai)
        # 쥐와 바닥에 떨어진 박쥐는 불길에 닿으면 덴다 (날고 있는 박쥐는 불길 위를 지나감)
        on_ground = not hasattr(enemy, 'is_flying') or not enemy.is_flying()
        if on_ground and not enemy.is_dead() and not enemy.is_knocked_back():
            flame = touching_flame(enemy)
            if flame:
                burn_by_flame(enemy, flame)
    # 쓰러지는 연출이 끝난 적은 지우고, HP가 남은 적만 공격에 맞도록 함
    rats[:] = [rat for rat in rats if rat.alive]
    bats[:] = [bat for bat in bats if bat.alive]
    game_world.hittables = brutes + [enemy for enemy in rats + bats if not enemy.is_dead()]
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    tunnel_door.draw()  # 열리는 하수 터널 문 (배경 그림의 일부라서 배경 바로 위에 그림)
    bridge.draw()  # 돌로 굳은 발판 (배경 그림의 유리판 위에 덮어 그림)
    # 발이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    # 날고 있는 박쥐는 공중에 있으므로 모든 것 위에 그림
    grounded = [kai] + brutes + rats + flames + [bat for bat in bats if not bat.is_flying()]
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
        for brute in brutes:
            draw_bb(brute.get_bb())
            draw_bb(brute.get_hit_bb())
            brute.draw_chase_range()
        for enemy in rats + bats:
            draw_bb(enemy.get_bb())
            draw_bb(enemy.get_hit_bb())
            enemy.draw_chase_range()
        for o in game_world.objects:
            if hasattr(o, 'draw_range'):
                o.draw_range()  # 증기가 시야를 가리는 범위
