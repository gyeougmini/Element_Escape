from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from collision import collide, draw_bb, push_out_offset
from dialogue import FONT_PATH
from flame import Flame
from hud import ElementHud
from kai import Kai, DIRECTION_ROWS
from kingrat import KingRat
from notice import Notice
from sliding_door import SlidingDoor

# 킹랫 방(kingrat_bg.png): 스테이지 2의 보스방. 하수 터널에서 저수조 문으로 들어오면 나오는 단계
KINGRAT_IMAGE = 'sprite_sheet/sprite_sheet_bg/kingrat_bg.png'
# 통과할 수 없는 벽과 물체: kingrat_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
KINGRAT_OBSTACLES = [
    # 외벽
    (0, 0, 1024, 135, WALL),     # 위 (쥐구멍, 발전실 문 포함)
    (0, 705, 1024, 768, WALL),   # 아래 (오른쪽 아래 입구 포함)
    (0, 0, 64, 768, WALL),       # 왼쪽
    (960, 0, 1024, 768, WALL),   # 오른쪽
    # 가운데 저수조 (수심 3m, 난간 포함). 위쪽 배수구에서 저수조로 이어지는 철망은 하수구 덮개라서 밟고 지나갈 수 있음
    (240, 300, 785, 588, WALL),
    # 물체
    (72, 125, 188, 188, OBJECT),   # 왼쪽 위 밸브 장치
    (596, 128, 686, 186, OBJECT),  # 전기 장치
]
KINGRAT_START_IMAGE_POS = (260, 230)  # 킹 랫 시작 위치: 왼쪽 위 쥐구멍 앞 (발 가운데)
ROOM_BOX = (64, 135, 960, 705)
POOL_WATER_BOX = (262, 338, 766, 572)  # 저수조의 물 부분 (킹 랫이 뛰어들어 헤엄치는 곳)        # 방 안쪽 (독 침이 날아가는 범위, 킹 랫이 튀어나올 수 있는 범위)
# 패턴 C: 킹 랫의 HP가 50% 이하가 되면 방 가장자리 네 곳에 화재 타일이 생김 (물로 꺼야 지나갈 수 있음)
FIRE_TILE_BOXES = [
    (66, 390, 130, 442),    # 왼쪽
    (894, 390, 958, 442),   # 오른쪽
    (470, 137, 534, 189),   # 위쪽
    (300, 596, 364, 648),   # 아래쪽 (화면 아래 HUD에 가리지 않는 높이)
]
FIRE_TILE_NOTICE_TEXT = '킹 랫이 분노했다!\n방 가장자리에 불이 번진다!'
FIRE_TILE_NOTICE_HOLD = 1.8
# 화재 타일에 닿으면 킹 랫도 덴다 (젖어 있으면 증기 폭발)
FLAME_RANGE = 16
FLAME_DAMAGE = 10
# 오른쪽 위 발전실 문: 킹 랫을 쓰러뜨리면 열림
POWER_DOOR_BOX = (824, 77, 904, 128)
POWER_DOOR_SEAM_X = 864
# 보스 HP 바 (화면 위쪽 가운데, 캔버스 좌표)
BOSS_BAR_WIDTH = 460
BOSS_BAR_HEIGHT = 12
BOSS_BAR_TOP_MARGIN = 44
BOSS_NAME = '킹 랫'
KAI_START_IMAGE_POS = (864, 650)  # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
boss_font = None
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지, 물의 초능력을 얻었는지), 없으면 처음 값
# 디버깅용: 이전 단계 없이 킹랫 방부터 시작하면(Element_Escape.py에서 바로 실행) 물 공격을 가진 상태로 시작
DEBUG_START_WITH_WATER = True


def carry_over(kai):
    """이전 단계의 카이 HP, 에너지, 물의 초능력을 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy, kai.water_unlocked)


def to_canvas_box(box):
    left, top, right, bottom = box
    return (background.to_canvas_x(left), background.to_canvas_y(bottom),
            background.to_canvas_x(right), background.to_canvas_y(top))


def bb_center(bb):
    left, bottom, right, top = bb
    return (left + right) / 2, (bottom + top) / 2


def update_obstacles():
    # 화재 타일은 꺼지면 지나갈 수 있으므로 매 프레임 합침
    flame_obstacles = [flame.get_obstacle() for flame in flames]
    game_world.obstacles = background.get_obstacles() + [o for o in flame_obstacles if o]


def burn_if_touching_flame(enemy):
    # 불길 가까이에 발이 닿으면 불길 반대쪽으로 밀어내며 불 공격을 받은 것처럼 처리
    left, bottom, right, top = enemy.get_bb()
    reach = (left - FLAME_RANGE, bottom - FLAME_RANGE, right + FLAME_RANGE, top + FLAME_RANGE)
    for flame in flames:
        if flame.is_burning() and collide(reach, flame.get_bb()):
            fx, fy = bb_center(flame.get_bb())
            ex, ey = bb_center(enemy.get_bb())
            length = ((ex - fx) ** 2 + (ey - fy) ** 2) ** 0.5
            enemy.on_fireball_hit(*(((ex - fx) / length, (ey - fy) / length) if length else (0, -1)), FLAME_DAMAGE)
            return


def draw_boss_bar():
    # 화면 위쪽 가운데에 보스 이름과 남은 HP
    if kingrat.is_death_done():
        return
    center_x = get_canvas_width() / 2
    top = get_canvas_height() - BOSS_BAR_TOP_MARGIN
    left = center_x - BOSS_BAR_WIDTH / 2
    bottom = top - BOSS_BAR_HEIGHT
    boss_font.draw(left, top + 12, BOSS_NAME, (235, 235, 235))
    draw_rectangle(left - 2, bottom - 2, left + BOSS_BAR_WIDTH + 2, top + 2, 20, 20, 25, 230, filled=True)
    ratio = kingrat.hp / kingrat.max_hp
    if ratio > 0:
        draw_rectangle(left, bottom, left + BOSS_BAR_WIDTH * ratio, top, 200, 40, 40, 255, filled=True)
    # 패턴 C가 시작되는 HP 50% 자리
    draw_rectangle(center_x - 1, bottom, center_x + 1, top, 240, 200, 80, 255, filled=True)


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, kai, hud, kingrat, flames, fire_tiles_spawned, power_door, notice, boss_font
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, KINGRAT_IMAGE, None, KINGRAT_OBSTACLES)
    flames = []
    fire_tiles_spawned = False
    update_obstacles()
    power_door = SlidingDoor(background, POWER_DOOR_BOX, POWER_DOOR_SEAM_X)
    notice = None
    if boss_font is None:
        boss_font = load_font(FONT_PATH, 20)
    kingrat = KingRat(background.to_canvas_x(KINGRAT_START_IMAGE_POS[0]),
                      background.to_canvas_y(KINGRAT_START_IMAGE_POS[1]), to_canvas_box(ROOM_BOX),
                      to_canvas_box(POOL_WATER_BOX))
    game_world.hittables = [kingrat]
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
    global fire_tiles_spawned, notice
    for flame in flames:
        flame.update(frame_time)
    flames[:] = [flame for flame in flames if flame.alive]  # 다 꺼진 불길은 지움
    # 패턴 C: HP가 50% 이하가 되면 한 번, 방 가장자리에 화재 타일 4개
    if not fire_tiles_spawned and not kingrat.is_dead() and kingrat.hp <= kingrat.max_hp / 2:
        fire_tiles_spawned = True
        flames.extend(Flame(background, box) for box in FIRE_TILE_BOXES)
        notice = Notice(FIRE_TILE_NOTICE_TEXT, FIRE_TILE_NOTICE_HOLD)
    update_obstacles()
    # 서 있던 자리에 장애물(화재 타일)이 생기면 끼어서 못 움직이므로 밀어냄
    # (물속이나 공중에 있는 킹 랫은 저수조 위에 있어도 되므로 빼고)
    for actor in [kai] + ([] if kingrat.ignores_obstacles() else [kingrat]):
        offset = push_out_offset(actor.get_bb(), obstacle_bbs())
        if offset:
            actor.x += offset[0]
            actor.y += offset[1]
    kai.update(frame_time, obstacle_bbs())
    kingrat.update(frame_time, obstacle_bbs(), kai)
    kingrat.touch(kai)
    if not kingrat.is_dead() and not kingrat.is_invulnerable() and not kingrat.is_knocked_back():
        burn_if_touching_flame(kingrat)
    # 잠수 중(무적)이거나 쓰러지면 공격이 지나감
    game_world.hittables = [] if kingrat.is_dead() or kingrat.is_invulnerable() else [kingrat]
    # 킹 랫이 쓰러지는 연출이 끝나면 발전실 문이 열림
    if kingrat.is_death_done():
        power_door.open()
    power_door.update(frame_time)
    if notice:
        notice.update(frame_time)
        if notice.is_done():
            notice = None
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    power_door.draw()  # 열리는 발전실 문 (배경 그림의 일부라서 배경 바로 위에 그림)
    # 발이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    actors = [kai] + flames + ([] if kingrat.is_death_done() else [kingrat])
    for actor in sorted(actors, key=lambda a: a.foot_y(), reverse=True):
        actor.draw()
    game_world.draw()
    hud.draw(kai.active_elements())
    draw_boss_bar()
    if notice:
        notice.draw()
    if show_bbs:
        for bb in obstacle_bbs():
            draw_bb(bb)
        draw_bb(kai.get_bb())
        draw_bb(kingrat.get_bb())
        draw_bb(kingrat.get_hit_bb())
        kingrat.draw_range()
        for o in game_world.objects:
            if hasattr(o, 'draw_range'):
                o.draw_range()  # 증기가 시야를 가리는 범위
