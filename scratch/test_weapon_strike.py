import sys
import os
sys.path.append("/Users/tj/Desktop/2DGame")
import pygame
pygame.init()
pygame.display.set_mode((1, 1))
from components.sprites.player import Player

p = Player()

def test_strike(p, weapon_key=None):
    from components.sprites.weapon import OneHanded
    from constants import WEAPON_DATA
    
    if weapon_key:
        data = WEAPON_DATA.get(weapon_key)
        p.weapon = OneHanded(data, weapon_key)
        print(f"Testing strike with {weapon_key}...")
    else:
        p.weapon = None
        print("Testing unarmed strike...")

    from systems.dungeon import Dungeon
    class DummyDungeon:
        tile_size = 64
        enemies = []
        traps = []
        map_width = 10
        map_height = 10
        map_data = [[1]*10 for _ in range(10)]
        flash_timer = 0
    
    class DummyEnemy:
        x = 64
        y = 0
        width = 64
        height = 64
        is_dead = False
        def take_damage(self, amount): pass
        name = "Enemy"
        hp = 100
        defense = 0
        eva_bonus = 0
    
    d = DummyDungeon()
    e = DummyEnemy()
    d.enemies = [e]
    
    p.x = 0
    p.y = 0
    p.facing = "right"
    
    try:
        p._execute_strike(d)
        print("Strike executed successfully.")
    except Exception as ex:
        print(f"Caught exception: {type(ex).__name__}: {ex}")
        raise ex

# Test unarmed
test_strike(p, None)

# Test with weapon
test_strike(p, "old_sword")
