from pico2d import *
from pico2d import pico2d as pico2d_core  # SDL renderer에 접근하기 위해 사용
from sdl2 import SDL_SetRenderDrawBlendMode, SDL_BLENDMODE_BLEND

# 화면(모드) 전환을 관리: 각 모드는 init, finish, handle_events, update(frame_time), draw 를 가짐
# 모드의 draw는 그리기만 하고, clear_canvas/update_canvas는 여기서 호출

FADE_TIME = 0.5  # 페이드 아웃/인 각각의 시간(초)

running = False
current_mode = None
mode_changed = False

# 페이드 전환: None -> 'out'(검게 어두워짐) -> 모드 전환 -> 'in'(검은 화면에서 밝아짐) -> None
fade_state = None
fade_time = 0.0
next_mode = None


def change_mode(mode):
    global current_mode, mode_changed
    if current_mode:
        current_mode.finish()
    current_mode = mode
    current_mode.init()
    mode_changed = True


def fade_to(mode):
    """화면을 검게 어둡게 한 뒤 모드를 바꾸고, 새 모드를 검은 화면에서 밝아지게 보여줌"""
    global fade_state, fade_time, next_mode
    if fade_state == 'out':
        return  # 이미 전환 중
    fade_state, fade_time, next_mode = 'out', 0.0, mode


def quit():
    global running
    running = False


def handle_events():
    if fade_state == 'out':
        # 다른 화면으로 넘어가는 중에는 입력을 받지 않음 (창 닫기만 처리)
        for event in get_events():
            if event.type == SDL_QUIT:
                quit()
        return
    current_mode.handle_events()


def update_fade(frame_time):
    global fade_state, fade_time, next_mode
    if fade_state is None:
        return
    fade_time += frame_time
    if fade_time < FADE_TIME:
        return
    if fade_state == 'out':
        change_mode(next_mode)
        fade_state, fade_time, next_mode = 'in', 0.0, None
    else:
        fade_state = None


def draw_fade():
    if fade_state is None:
        return
    progress = min(fade_time / FADE_TIME, 1.0)
    alpha = progress if fade_state == 'out' else 1.0 - progress
    draw_rectangle(0, 0, get_canvas_width(), get_canvas_height(),
                   0, 0, 0, int(alpha * 255), filled=True)


def run(start_mode):
    global running, mode_changed
    running = True
    # pico2d는 기본적으로 반투명 사각형을 그리지 않으므로 알파 블렌딩을 켬
    SDL_SetRenderDrawBlendMode(pico2d_core.renderer, SDL_BLENDMODE_BLEND)
    change_mode(start_mode)
    last_time = get_time()
    while running:
        handle_events()
        now = get_time()
        frame_time = now - last_time
        last_time = now
        update_fade(frame_time)
        if mode_changed:
            # 모드를 바꾸며 이미지를 불러오는 데 걸린 시간이 첫 프레임에 몰리지 않도록 시간 초기화
            mode_changed = False
            last_time = get_time()
            frame_time = 0.0
        current_mode.update(frame_time)
        clear_canvas()
        current_mode.draw()
        draw_fade()
        update_canvas()
        delay(0.01)
    current_mode.finish()
