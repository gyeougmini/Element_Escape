from pico2d import get_time, delay

# 화면(모드) 전환을 관리: 각 모드는 init, finish, handle_events, update(frame_time), draw 를 가짐

running = False
current_mode = None
mode_changed = False


def change_mode(mode):
    global current_mode, mode_changed
    if current_mode:
        current_mode.finish()
    current_mode = mode
    current_mode.init()
    mode_changed = True


def quit():
    global running
    running = False


def run(start_mode):
    global running, mode_changed
    running = True
    change_mode(start_mode)
    last_time = get_time()
    while running:
        current_mode.handle_events()
        if mode_changed:
            # 모드를 바꾸며 이미지를 불러오는 데 걸린 시간이 첫 프레임에 몰리지 않도록 시간 초기화
            mode_changed = False
            last_time = get_time()
        now = get_time()
        frame_time = now - last_time
        last_time = now
        current_mode.update(frame_time)
        current_mode.draw()
        delay(0.01)
    current_mode.finish()
