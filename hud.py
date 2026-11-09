from pico2d import *

# 모든 원소 HUD 이미지는 같은 크기(152x144)이며, 바탕(벤 다이어그램) 위에 켜진 부분만 겹쳐 그림
# 원 배치: 불(위), 물(왼쪽 아래), 전기(오른쪽 아래). 두 원이 겹친 부분이 콤보
HUD_DIR = 'sprite_sheet_hud/'
BASE_IMAGE = 'element_hud_base.png'
ELEMENT_IMAGES = {
    'fire': 'element_on_fire.png',
    'water': 'element_on_water.png',
    'electric': 'element_on_electric.png',
}
# 두 속성이 함께 켜지면 켜지는 콤보
COMBO_IMAGES = {
    ('fire', 'water'): 'combo_steam.png',
    ('fire', 'electric'): 'combo_plasma.png',
    ('water', 'electric'): 'combo_shock.png',
}
HUD_WIDTH, HUD_HEIGHT = 152, 144
HUD_MARGIN = 10  # 화면 아래쪽 끝에서 HUD까지의 거리

# HP/에너지 바: 테두리(392x32) 안쪽에 상하좌우 8px 여백을 두고 채움(376x16)을 그림
BAR_FRAME_WIDTH = 392
BAR_FILL_WIDTH, BAR_FILL_HEIGHT = 376, 16
BAR_GAP = 10       # 원소 HUD와 아이콘 사이 거리 (아이콘은 바의 안쪽, 즉 원소 HUD 쪽에 둠)
ICON_GAP = 6       # 아이콘과 바 사이 거리
FLASH_TIME = 0.4   # HP가 줄면 깎인 부분이 밝게 남아 있다가 사라지는 시간(초)


class Bar:
    """테두리 + 남은 양만큼 왼쪽부터 채워지는 바. flash 이미지가 있으면 줄어든 부분을 잠깐 밝게 보여줌"""

    def __init__(self, fill_path, icon_path, flash_path=None):
        self.frame = load_image(HUD_DIR + 'hp_ep_bar_frame.png')
        self.fill = load_image(HUD_DIR + fill_path)
        self.icon = load_image(HUD_DIR + icon_path)
        self.flash = load_image(HUD_DIR + flash_path) if flash_path else None
        self.ratio = None        # 마지막으로 그린 채움 비율
        self.flash_from = 0.0    # 깎이기 전 비율 (이 지점까지 밝게 표시)
        self.flash_time = 0.0

    def update(self, frame_time, value, max_value):
        ratio = max(0.0, min(1.0, value / max_value))
        if self.ratio is not None and ratio < self.ratio and self.flash:
            # 이미 깜빡이는 중이면 처음 깎이기 전 지점을 유지
            self.flash_from = max(self.flash_from, self.ratio) if self.flash_time > 0 else self.ratio
            self.flash_time = FLASH_TIME
        self.ratio = ratio
        self.flash_time = max(0.0, self.flash_time - frame_time)

    def draw_fill(self, image, left, y, start_ratio, end_ratio):
        start = int(BAR_FILL_WIDTH * start_ratio)
        width = int(BAR_FILL_WIDTH * end_ratio) - start
        if width <= 0:
            return
        image.clip_draw(start, 0, width, BAR_FILL_HEIGHT, left + start + width / 2, y)

    def draw(self, center_x, y, icon_side):
        """icon_side: 아이콘을 바의 'left' 또는 'right' 바깥쪽에 그림"""
        self.frame.draw(center_x, y)
        fill_left = center_x - BAR_FILL_WIDTH / 2
        ratio = self.ratio or 0.0
        if self.flash and self.flash_time > 0:
            self.draw_fill(self.flash, fill_left, y, ratio, self.flash_from)
        self.draw_fill(self.fill, fill_left, y, 0.0, ratio)
        offset = BAR_FRAME_WIDTH / 2 + ICON_GAP + self.icon.w / 2
        self.icon.draw(center_x - offset if icon_side == 'left' else center_x + offset, y)


class ElementHud:
    """화면 아래 가운데: 켜져 있는 속성과 콤보, 그 왼쪽에 HP 바, 오른쪽에 에너지 바"""

    def __init__(self):
        self.base = load_image(HUD_DIR + BASE_IMAGE)
        self.elements = {name: load_image(HUD_DIR + path) for name, path in ELEMENT_IMAGES.items()}
        self.combos = {pair: load_image(HUD_DIR + path) for pair, path in COMBO_IMAGES.items()}
        self.hp_bar = Bar('hp_bar_fill.png', 'hp_icon_heart.png', 'hp_bar_fill_flash.png')
        self.energy_bar = Bar('ep_bar_fill.png', 'ep_icon_battery.png')

    def update(self, frame_time, kai):
        self.hp_bar.update(frame_time, kai.hp, kai.max_hp)
        self.energy_bar.update(frame_time, kai.energy, kai.max_energy)

    def draw(self, active):
        """active: 켜져 있는 속성 이름의 집합 (예: {'fire', 'water'})"""
        x = get_canvas_width() // 2
        y = HUD_MARGIN + HUD_HEIGHT // 2
        self.base.draw(x, y)
        for name, image in self.elements.items():
            if name in active:
                image.draw(x, y)
        for (a, b), image in self.combos.items():
            if a in active and b in active:
                image.draw(x, y)
        # 원소 HUD | 아이콘 | 바 순서로 바깥쪽으로 배치: HP는 왼쪽, 에너지는 오른쪽
        for bar, sign in ((self.hp_bar, -1), (self.energy_bar, 1)):
            bar_offset = HUD_WIDTH / 2 + BAR_GAP + bar.icon.w + ICON_GAP + BAR_FRAME_WIDTH / 2
            bar.draw(x + sign * bar_offset, y, 'right' if sign < 0 else 'left')
