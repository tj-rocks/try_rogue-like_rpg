import random
from constants import GUILD_RANKS, WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, ENEMY_DATA, STAVE_DATA
from wordings import Text

class GuildSystem:
    def __init__(self):
        # 今日のギルドボード（ランダム生成されたクエストを保持する）
        # ※本来はセーブデータ等に保存してもよいが、今回はギルドを開くたびに変わる仕様とする。
        self.available_quests = []
        self.fixed_quests = []

    def get_current_rank(self, rank_name):
        """指定されたランク名（F, E, D...）のデータを返す"""
        for rank_data in GUILD_RANKS:
            if rank_data["rank"] == rank_name:
                return rank_data
        return GUILD_RANKS[0]

    def get_next_rank_data(self, current_rank_name):
        """現在のランクの次のランクデータを返す（最高ランクならNone）"""
        from constants import RANK_ORDER
        if current_rank_name not in RANK_ORDER: return None
        idx = RANK_ORDER.index(current_rank_name)
        if idx + 1 < len(RANK_ORDER):
            next_name = RANK_ORDER[idx + 1]
            return self.get_current_rank(next_name)
        return None

    def get_next_rank_req(self, guild_point):
        """次のランクに到達するために必要な総GPを返す（最高ランクならNone）"""
        # ※このメソッドはUI表示用に残すが、昇格自体はクエストで行う。
        for rank_data in GUILD_RANKS:
            if rank_data["required_gp"] > guild_point:
                return rank_data["required_gp"]
        return None

    def get_max_floor(self, rank_name):
        """指定されたランクから、潜れる最大階層を返す（マスタデータ参照）"""
        rank_data = self.get_current_rank(rank_name)
        return rank_data.get("limit_floor", 0)

    def get_required_rank_for_floor(self, floor):
        """特定の階層に潜るために必要な最小ランク名を返す"""
        for rank_data in GUILD_RANKS:
            if floor <= rank_data.get("limit_floor", 0):
                return rank_data["rank"]
        return "SS"

    def is_rank_at_least(self, player_rank_name, req_rank_name):
        """プレイヤーのランク名が指定されたランク以上かどうかを判定する"""
        from constants import RANK_ORDER
        if req_rank_name not in RANK_ORDER: return True
        if player_rank_name not in RANK_ORDER: return False
        
        p_idx = RANK_ORDER.index(player_rank_name)
        r_idx = RANK_ORDER.index(req_rank_name)
        # 例外: ランク "-" (0) の時は F (1) のアイテムまで使える
        if p_idx == 0 and r_idx == 1: return True
        return p_idx >= r_idx

    def generate_quests(self, player):
        """プレイヤーのランクに応じたクエストを生成する"""
        self.available_quests = []
        self.fixed_quests = []
        rank_data = self.get_current_rank(player.guild_rank)
        allowed_ranks = rank_data.get("allowed_ranks", ["F"])
        mult = rank_data["reward_multiplier"]
        min_amount, max_amount = rank_data["amount_range"]

        # 1. 固定クエストの読み込み (自分のランク以下のクエスト)
        from constants import FIXED_QUEST_DATA, RANK_ORDER
        player_rank_idx = RANK_ORDER.index(player.guild_rank)
        
        for q_data in FIXED_QUEST_DATA:
            q_id = q_data.get("id")
            min_rank = q_data.get("min_rank", "F")
            max_rank = q_data.get("max_rank", "SS")
            min_rank_idx = RANK_ORDER.index(min_rank)
            max_rank_idx = RANK_ORDER.index(max_rank)
            
            # 条件1：プレイヤーのランクが範囲内か
            if min_rank_idx <= player_rank_idx <= max_rank_idx:
                # 条件2：未クリア、あるいは繰り返し可能か
                is_completed = q_id in player.completed_fixed_quests
                if q_data.get("repeatable") or not is_completed:
                    # 条件3：現在受注していないか
                    if not any(aq.get("id") == q_id for aq in player.active_quests):
                        # 条件4：出現確率 (chance) をクリアするか（未指定なら 1.0=100%）
                        chance = q_data.get("chance", 1.0)
                        if random.random() < chance:
                            # コピーして追加
                            self.fixed_quests.append(dict(q_data))

        # 2. ランダムクエストの生成 (常に3〜4つ生成する)
        num_random = random.randint(3, 4)
        for _ in range(num_random):
            q_type = random.choice(["hunt", "delivery"])
            
            if q_type == "hunt":
                quest = self._generate_hunt_quest(allowed_ranks, mult, min_amount, max_amount)
            else:
                quest = self._generate_delivery_quest(allowed_ranks, mult, min_amount, max_amount)
            
            if quest:
                self.available_quests.append(quest)

    def _generate_hunt_quest(self, allowed_ranks, multiplier, min_amt, max_amt):
        # 許可されたランクの敵をリストアップ
        candidates = []
        for key, data in ENEMY_DATA.items():
            r = data.get("min_rank") or data.get("rank") or "F"
            # ボス属性の敵、および特殊な敵はランダムクエストの対象外とする
            if r in allowed_ranks and not data.get("is_boss", False):
                candidates.append((key, data))
        
        if not candidates:
            return None
            
        target_key, target_data = random.choice(candidates)
        amount = random.randint(min_amt, max_amt)
        
        # 個別に報酬額が設定されている場合はそれを使う。ない場合は能力値から算出（係数を2->5に強化）
        unit_reward = target_data.get("reward_gold")
        if unit_reward is None:
            unit_reward = (target_data.get("hp", 10) + target_data.get("attack", 0)) * 5
            
        from systems.math_utils import hardcore_round
        reward_gold = hardcore_round(unit_reward * amount * multiplier, is_hp=True)
        reward_gp = amount * 5 # GPは討伐数×5
        
        target_rank = target_data.get("min_rank") or target_data.get("rank") or "F"
        if target_data.get("is_static"):
            title = Text.Guild.QUEST_DESTROY_TITLE.format(rank=target_rank, name=target_data['name'], amount=amount)
        else:
            title = Text.Guild.QUEST_HUNT_TITLE.format(rank=target_rank, name=target_data['name'], amount=amount)

        return {
            "type": "hunt",
            "target_key": target_key,
            "target_name": target_data["name"],
            "amount": amount,
            "reward_gold": reward_gold,
            "reward_gp": reward_gp,
            "title": title
        }

    def _generate_delivery_quest(self, allowed_ranks, multiplier, min_amt, max_amt):
        # 許可されたランクのアイテムを候補とする
        candidates = []
        for catalog in [WEAPON_DATA, ARMOR_DATA, SHIELD_DATA, CONSUMABLE_DATA, STAVE_DATA]:
            for key, data in catalog.items():
                target_rank = data.get("min_rank") or data.get("rank") or "F"
                if target_rank in allowed_ranks and data.get("price", 0) > 0:
                    candidates.append((key, data))
                    
        if not candidates:
            return None
            
        target_key, target_data = random.choice(candidates)
        amount = random.randint(min_amt, max_amt)
        
        # 売値（購入価格の1/3）の1.2倍 * 数量 * 倍率（ランクによる追加）
        base_sell = target_data.get("price", 100) // 3
        from systems.math_utils import hardcore_round
        reward_gold = hardcore_round(base_sell * 1.2 * amount * multiplier, is_hp=True)
        reward_gp = amount * 3 # 納品は討伐よりGP低め
        
        target_rank = target_data.get("min_rank", "F")
        return {
            "type": "delivery",
            "target_key": target_key,
            "target_name": target_data["name"],
            "amount": amount,
            "reward_gold": reward_gold,
            "reward_gp": reward_gp,
            "title": Text.Guild.QUEST_DELIVERY_TITLE.format(rank=target_rank, name=target_data['name'], amount=amount)
        }
