# 파이어볼, 이펙트처럼 생겼다 사라지는 오브젝트들을 관리
# 각 오브젝트는 update(frame_time), draw(), alive 를 가짐

objects = []
obstacles = []  # (bb, burnable) 목록. 메인에서 배경을 만든 뒤 채움


def add(o):
    objects.append(o)


def update(frame_time):
    for o in objects[:]:
        o.update(frame_time)
    objects[:] = [o for o in objects if o.alive]


def draw():
    for o in objects:
        o.draw()
