import pygame
pygame.init()
pygame.display.set_mode((100, 100))

from components.sprites.player import Player, StaveInstance
from systems.magic_handler import execute_stave

class MockDungeon:
    def __init__(self):
        self.enemies = []
        self.magic_effects = []
        self.tile_size = 64
        self.map_width = 10
        self.map_height = 10
        self.current_floor = 1

class MockDialog:
    def __init__(self):
        self.text = ""
        self.is_active = False

player = Player()
player.x, player.y = 0, 0
player.facing = "right"
player.name = "Hero"

dungeon = MockDungeon()
dialog = MockDialog()

# 初期状態の確認
print(f"Original player attack: {player.attack}")
print(f"Original player total_attack: {player.total_attack}")
print(f"Original player attack_buff_turns: {player.attack_buff_turns}")
print(f"Original player attack_buff_val: {player.attack_buff_val}")

orig_total_attack = player.total_attack # 12
stave = StaveInstance("enchant_stave", charges=5)
msg = execute_stave(player, stave, dungeon, dialog)

print(f"\n--- Enchant Stave Used ---")
print(msg)
print(f"Player total_attack after buff (Expected {orig_total_attack + 5}): {player.total_attack}")
print(f"Player attack_buff_turns after buff (Expected 10): {player.attack_buff_turns}")
print(f"Player attack_buff_val after buff (Expected 5): {player.attack_buff_val}")

assert player.total_attack == orig_total_attack + 5
assert player.attack_buff_turns == 10
assert player.attack_buff_val == 5
assert len(dungeon.magic_effects) == 1
print("Enchant execution assertions passed!")

# ターン経過のシミュレーション
# Player.operate で turn_consumed が True の時にターンが減る
# operateを直接シミュレートするため、player.operate()の入力処理の代わりに operate 内の turn_consumed 分岐を実行
# operate の該当箇所:
#         if turn_consumed:
#             if self.invincible_turns > 0: ...
#             if getattr(self, "attack_buff_turns", 0) > 0:
#                 self.attack_buff_turns -= 1
#                 ...
# テストのため、Playerクラスのoperate内で行われているターン消費時の処理（invincible_turnsやattack_buff_turnsのデクリメント）を直接実行するか、
# モックの操作イベントを発火させる。
# ここでは直接 player.operate に似た処理を呼び出すために、疑似イベントを渡して operate を呼び出すか、
# もしくは直接 decrement を行う。
# player.operate(dungeon, dialog, events) を呼ぶには KEYDOWN や移動キーなどが必要。
# ここでは operate を直接呼び出すのではなく、プレイヤーがターン消費した状況を作ります。
# 実際には、operate は pygame の KEYDOWN などのイベントで turn_consumed = True になり、
# 該当ブロックを通ります。
# player.operate を実際に呼び出してみます。
# events に KEY_ATTACK を模したKEYDOWNイベントを渡します。
event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)

print("\n--- Simulating 10 turns decrement ---")
for turn in range(1, 11):
    # 初期化
    player.is_attacking = False
    player.is_moving = False
    game_state = {"dialog_just_closed": False, "turn_state": "player"}
    # systems.game_state.game_state に値をセット
    from systems.game_state import game_state as gs
    gs["dialog_just_closed"] = False
    gs["turn_state"] = "player"
    
    dialog.text = ""
    dialog.is_active = False
    
    # 攻撃キー（スペース）で攻撃行動（ターン消費）を行う
    player.operate(dungeon, dialog, [event])
    
    print(f"Turn {turn} consumed. Buff turns remaining: {player.attack_buff_turns}, Total Attack: {player.total_attack}")
    
    # ターンが引かれていることを確認
    assert player.attack_buff_turns == 10 - turn
    if turn < 10:
        assert player.total_attack == orig_total_attack + 5
    else:
        assert player.total_attack == orig_total_attack
        assert "攻撃力上昇の効果が 切れた！" in dialog.text

print("Decrement logic and expiry assertions passed!")
print("\nAll unit tests passed successfully!")
