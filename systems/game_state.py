# 毎フレーム（1秒間に60回）読み書きが発生するため、JSONファイルではなく
# ディスクアクセス不要で非常に高速なPythonの「辞書ファイル（グローバル変数）」としてシステム状態を管理します
# ※ 使い勝手はJSONと全く一緒です！

game_state = {
    "current_scene": "title",    # "opening", "title", "game"
    "opening_index": 0,          # オープニングの現在の画像番号
    "opening_timer": 0,          # 次の画像までのタイマー
    "opening_alpha": 0,          # フェードイン用の不透明度
    "opening_seen": False,       # オープニングを既に見たか
    "title_selected_idx": 1,     # タイトル画面での選択項目 (0: Continue, 1: New Game)
    
    "dialog_active": False,
    "dialog_modal": True,   # ボタン入力を待つ（ポーズする）かどうか
    "confirm_active": False,
    "inventory_active": False,
    "enhance_active": False,
    "status_active": False,  # ステータス画面用
    "shop_active": False,    # ショップ（売買）画面用
    "item_action_active": False, # 「使う・捨てる」メニュー用
    "ore_selection_active": False, # 鍛冶屋での「どの鉱石使う？」メニュー用
    "parameter_selection_active": False, # 鍛冶屋での「どのパラメータを鍛える？」メニュー用
    "stave_selection_active": False, # 杖の回復対象選択用
    "bank_active": False,        # 銀行画面用
    "teleport_active": False,    # テレポート画面用
    "turn_state": "player",       # "player" or "enemies"
    "current_enemy_idx": 0,      # 現在行動中の敵のインデックス
    "inter_action_timer": 0,     # 行動間の待機時間用タイマー
    "dialog_just_closed": False, # ダイアログを閉じた瞬間の誤爆防止用
    "warehouse_active": False,   # 預かり屋画面用
    "guild_active": False,       # ギルド画面用
    "menu_active": False,        # メインメニュー用
    "equip_active": False,       # 装備画面用
    "stave_inventory_active": False, # 杖インベントリ用
    "event_item_active": False,  # 貴重品インベントリ用
}

# どのダイアログ（メニュー）が開いていても、ゲーム全体をポーズするための共通判定関数
def is_paused():
    # ダイアログがアクティブでも、モーダル（決定ボタン待ち）でなければポーズしない
    dialog_pausing = game_state["dialog_active"] and game_state["dialog_modal"]
    return (dialog_pausing or 
            game_state["confirm_active"] or 
            game_state["inventory_active"] or 
            game_state["enhance_active"] or
            game_state["status_active"] or
            game_state.get("ore_selection_active", False) or
            game_state.get("parameter_selection_active", False) or
            game_state["stave_selection_active"] or
            game_state["bank_active"] or
            game_state["shop_active"] or
            game_state.get("warehouse_active", False) or
            game_state.get("guild_active", False) or
            game_state.get("menu_active", False) or
            game_state.get("equip_active", False) or
            game_state.get("stave_inventory_active", False) or
            game_state.get("teleport_active", False) or
            game_state.get("event_item_active", False))
