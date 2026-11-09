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


def push_out_offset(bb, bbs):
    """bb가 장애물과 겹쳐 있으면, 어떤 장애물과도 겹치지 않게 되는 가장 짧은 (dx, dy)를 돌려줌.
    겹치지 않았으면 (0, 0), 빠져나갈 곳이 없으면 None.
    (문이 열리며 생긴 충돌 박스처럼, 캐릭터가 서 있던 자리에 장애물이 새로 생겼을 때 사용)"""
    if not collide_any(bb, bbs):
        return (0, 0)
    left, bottom, right, top = bb
    candidates = []
    for o_left, o_bottom, o_right, o_top in (o for o in bbs if collide(bb, o)):
        # 겹친 장애물의 네 변 바깥으로 밀어내는 경우들
        candidates += [(o_left - right, 0), (o_right - left, 0),
                       (0, o_bottom - top), (0, o_top - bottom)]
    for dx, dy in sorted(candidates, key=lambda d: abs(d[0]) + abs(d[1])):
        moved = (left + dx, bottom + dy, right + dx, top + dy)
        if not collide_any(moved, bbs):
            return (dx, dy)
    return None


def draw_bb(bb):
    draw_rectangle(*bb)
