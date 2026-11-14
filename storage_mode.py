from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from box import make_boxes
from collision import collide, draw_bb, push_out_offset
from hud import ElementHud
from ice import IceBlock
from kai import Kai, DIRECTION_ROWS
from rat import Rat, spawn_rats
from storage_door import StorageDoor

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
# 상자 안에 든 것: STORAGE_BOX_POSITIONS의 순서(0부터) -> 'rat'. 상자가 다 타서 무너지면 불붙은 채로 나옴
STORAGE_BOX_CONTENTS = {
    2: 'rat',   # 가로줄 가운데
    5: 'rat',   # ㄱ자 모서리
    8: 'rat',   # 세로줄 아래쪽
    10: 'rat',  # 빨간 점선 구역 왼쪽
    12: 'rat',  # 빨간 점선 구역 오른쪽
}
# 처음부터 돌아다니는 쥐: 입구를 가둔 상자 줄 바깥 구역에 무작위로 나타남
RAT_COUNT = 7
RAT_AREAS = [  # storage_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
    (380, 140, 955, 700),  # 상자 줄 오른쪽의 넓은 바닥
    (70, 210, 370, 395),   # 상자 가로줄 위쪽
]
# 불길이 보이는 상자에서 이 거리(px) 안으로 쥐의 발이 들어오면 쥐에게 불이 옮겨붙음
BOX_FIRE_RANGE = 16
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


def to_canvas_box(box):
    left, top, right, bottom = box
    return (background.to_canvas_x(left), background.to_canvas_y(bottom),
            background.to_canvas_x(right), background.to_canvas_y(top))


def release_box_content(box):
    # 상자가 다 타서 무너지면 안에 든 쥐가 상자 자리에 불붙은 채로 나옴
    if box.take_content() != 'rat':
        return
    rat = Rat(0, 0)
    rat.place_feet_at(*box.content_pos())
    rat.ignite()
    rats.append(rat)


def near_flaming_box(rat):
    left, bottom, right, top = rat.get_bb()
    reach = (left - BOX_FIRE_RANGE, bottom - BOX_FIRE_RANGE, right + BOX_FIRE_RANGE, top + BOX_FIRE_RANGE)
    return any(box.is_flaming() and collide(reach, box.get_bb()) for box in boxes)


def all_rats_caught():
    # 돌아다니는 쥐가 모두 쓰러졌고, 아직 상자 안에 남아 있는 쥐도 없음
    return (all(rat.is_dead() for rat in rats)
            and not any(box.content == 'rat' for box in boxes))


def init():
    global background, exit_door, boxes, ices, rats, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, STORAGE_IMAGE, None, STORAGE_OBSTACLES)
    # 오른쪽 위 간수실 문: 감방의 창고 문과 자리와 그림이 같아서 같은 시트를 씀
    exit_door = StorageDoor(background)
    boxes = make_boxes(background, STORAGE_BOX_POSITIONS, STORAGE_BOX_CONTENTS)
    ices = [IceBlock(background, x, bottom) for x, bottom in ICE_POSITIONS]
    update_obstacles()
    rats = spawn_rats(RAT_COUNT, [to_canvas_box(area) for area in RAT_AREAS], obstacle_bbs())
    game_world.hittables = list(rats)
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
        release_box_content(box)
    boxes[:] = [box for box in boxes if box.alive]  # 다 타서 사라진 상자는 지움
    for ice in ices:
        ice.update(frame_time)
    ices[:] = [ice for ice in ices if ice.alive]  # 다 녹은 얼음은 지움
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
        # 번지는 불 근처로 유인된 쥐는 불타는 상태가 됨
        if not rat.is_dead() and not rat.is_burning() and near_flaming_box(rat):
            rat.ignite()
    # 기절 연출이 끝난 쥐는 지우고, HP가 남은 쥐만 파이어볼에 맞도록 함
    rats[:] = [rat for rat in rats if rat.alive]
    if all_rats_caught():
        exit_door.open()
    exit_door.update(frame_time)
    game_world.hittables = [rat for rat in rats if not rat.is_dead()]
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    exit_door.draw()
    # 발(상자는 몸체 아래쪽 끝)이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    for actor in sorted([kai] + rats + boxes + ices, key=lambda a: a.foot_y(), reverse=True):
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
