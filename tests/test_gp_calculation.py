
import os
import sys
import unittest
from unittest.mock import MagicMock

# プロジェクトルートをパスに追加
sys.path.append(os.getcwd())

# テスト用の環境変数設定
os.environ["TEST_MODE"] = "1"
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

from systems.guild import GuildSystem

class TestGPCalculation(unittest.TestCase):
    def setUp(self):
        self.guild = GuildSystem()

    def test_gp_divisor_logic(self):
        """GPが報酬ゴールドの1/10（除数設定値）になることを検証"""
        from constants import GUILD_QUEST_GP_DIVISOR, GP_RANK_DIFF_MULTIPLIERS
        # プレイヤーランクが F の時
        player_rank = "F"
        
        # 1. MATCH (Player F, Quest F)
        q = self.guild._generate_hunt_quest(["F"], 1.0, 1, 3, player_rank=player_rank)
        if q:
            # 基本GP = gold // divisor
            # MATCH倍率適用
            base_gp = q["reward_gold"] // GUILD_QUEST_GP_DIVISOR
            expected_gp = int(base_gp * GP_RANK_DIFF_MULTIPLIERS["MATCH"])
            expected_gp = max(1, expected_gp)
            self.assertEqual(q["reward_gp"], expected_gp, f"GP calculation mismatch for MATCH. Gold: {q['reward_gold']}, GP: {q['reward_gp']}, Expected: {expected_gp}")

    def test_rank_diff_multipliers(self):
        """ランク格差による倍率補正を検証"""
        from constants import GUILD_QUEST_GP_DIVISOR, GP_RANK_DIFF_MULTIPLIERS
        # プレイヤーランク D の場合
        player_rank = "D"
        
        # 1. CHALLENGE (Quest C, Player D)
        q_challenge = self.guild._generate_hunt_quest(["C"], 1.0, 10, 15, player_rank=player_rank)
        if q_challenge:
            base_gp = q_challenge["reward_gold"] // GUILD_QUEST_GP_DIVISOR
            expected_gp = int(base_gp * GP_RANK_DIFF_MULTIPLIERS["CHALLENGE"])
            expected_gp = max(1, expected_gp)
            self.assertEqual(q_challenge["reward_gp"], expected_gp, "CHALLENGE multiplier not applied correctly")

        # 2. MATCH (Quest D, Player D)
        q_match = self.guild._generate_hunt_quest(["D"], 1.0, 5, 10, player_rank=player_rank)
        if q_match:
            base_gp = q_match["reward_gold"] // GUILD_QUEST_GP_DIVISOR
            expected_gp = int(base_gp * GP_RANK_DIFF_MULTIPLIERS["MATCH"])
            expected_gp = max(1, expected_gp)
            self.assertEqual(q_match["reward_gp"], expected_gp, "MATCH multiplier not applied correctly")

        # 3. EASY (Quest F, Player D)
        q_easy = self.guild._generate_hunt_quest(["F"], 1.0, 1, 3, player_rank=player_rank)
        if q_easy:
            base_gp = q_easy["reward_gold"] // GUILD_QUEST_GP_DIVISOR
            expected_gp = int(base_gp * GP_RANK_DIFF_MULTIPLIERS["EASY"])
            expected_gp = max(1, expected_gp)
            self.assertEqual(q_easy["reward_gp"], expected_gp, "EASY multiplier not applied correctly")

if __name__ == "__main__":
    unittest.main()
