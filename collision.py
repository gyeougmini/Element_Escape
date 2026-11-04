from pico2d import draw_rectangle

# 충돌 박스(bb)는 캔버스 좌표의 (left, bottom, right, top) 튜플


def collide(a, b):
    left_a, bottom_a, right_a, top_a = a
    left_b, bottom_b, right_b, top_b = b
    if right_a <= left_b or left_a >= right_b:
        return False
    if top_a <= bottom_b or bottom_a >= top_b:
        return False
    return True


def collide_any(bb, bbs):
    return any(collide(bb, other) for other in bbs)


def draw_bb(bb):
    draw_rectangle(*bb)
