from pico2d import *

WIDTH, HEIGHT = 1280, 720

running = True


def handle_events():
    global running
    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False


open_canvas(WIDTH, HEIGHT)

background = load_image('sprite_sheet/cell_bg.png')
kai = load_image('sprite_sheet/kai_animation_sheet.png')

# kai_animation_sheet.png: 576x512, 9열 x 8행, 프레임 64x64
FRAME_SIZE = 64
SHEET_HEIGHT = 512
WALK_FRAMES = 6
KAI_SCALE = 1.5

kai_x, kai_y = WIDTH // 2, HEIGHT // 2
kai_row = 0  # 0행: 정면
frame = 0

while running:
    handle_events()
    clear_canvas()
    background.draw(WIDTH // 2, HEIGHT // 2, WIDTH, HEIGHT)
    # pico2d는 좌하단이 원점이므로 위에서부터의 행 번호를 뒤집어서 계산
    kai.clip_draw(frame * FRAME_SIZE, SHEET_HEIGHT - (kai_row + 1) * FRAME_SIZE,
                  FRAME_SIZE, FRAME_SIZE,
                  kai_x, kai_y, FRAME_SIZE * KAI_SCALE, FRAME_SIZE * KAI_SCALE)
    update_canvas()
    frame = (frame + 1) % WALK_FRAMES
    delay(0.1)

close_canvas()
