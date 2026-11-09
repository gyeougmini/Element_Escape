from pico2d import *

# 모든 HUD 이미지는 같은 크기(152x144)이며, 바탕(벤 다이어그램) 위에 켜진 부분만 겹쳐 그림
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
HUD_HEIGHT = 144
HUD_MARGIN = 10  # 화면 아래쪽 끝에서 HUD까지의 거리


class ElementHud:
    """화면 아래 가운데에 켜져 있는 속성과 콤보를 보여주는 HUD"""

    def __init__(self):
        self.base = load_image(HUD_DIR + BASE_IMAGE)
        self.elements = {name: load_image(HUD_DIR + path) for name, path in ELEMENT_IMAGES.items()}
        self.combos = {pair: load_image(HUD_DIR + path) for pair, path in COMBO_IMAGES.items()}

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
