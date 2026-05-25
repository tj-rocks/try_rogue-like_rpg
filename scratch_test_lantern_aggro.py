import pygame
pygame.init()
pygame.display.set_mode((100, 100))

from components.sprites.player import Player

class MockLantern:
    def __init__(self, iid, aggro_mod, enhance):
        self.iid = iid
        self.enhance = enhance
        self._aggro_mod = aggro_mod

    def get_stat(self, key, default=0):
        if key == "aggro_mod":
            return self._aggro_mod
        return default

player = Player()
player.weapon_inventory = []
player.armor_inventory = []
player.shield_inventory = []
player.lantern_inventory = []

# Create a mock lantern
lantern = MockLantern(iid=999, aggro_mod=0, enhance=0)
player.lantern_inventory.append(lantern)
player.equipped_lantern = 999

# Test 1: +0
aggro_0 = player.get_aggro_modifier()
print(f"[Lantern +0] Aggro Mod: {aggro_0}")
assert aggro_0 == 0

# Test 2: +1
lantern.enhance = 1
aggro_1 = player.get_aggro_modifier()
print(f"[Lantern +1] Aggro Mod: {aggro_1}")
assert aggro_1 == -0.5

# Test 3: +10
lantern.enhance = 10
aggro_10 = player.get_aggro_modifier()
print(f"[Lantern +10] Aggro Mod: {aggro_10}")
assert aggro_10 == -5.0

print("All tests passed successfully!")
