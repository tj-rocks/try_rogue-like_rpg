#!/bin/bash
# run_tests.sh - 全ての自動テストを実行する

# スクリプトのあるディレクトリの親ディレクトリ（プロジェクトルート）に移動
cd "$(dirname "$0")/.."

# VENV_PYTHON が未定義ならデフォルト値を設定
if [ -z "$PYTHON_EXE" ]; then
    PYTHON_EXE="./venv/bin/python"
fi
VENV_PYTHON=$PYTHON_EXE

echo "========================================"
echo "🚀 2DGame テストスイート実行中..."
echo "========================================"

# テストモードを強制（セーブデータの汚染防止）
export TEST_MODE=1
export PYTHONPATH=$PYTHONPATH:.

# --- [SAFEGUARD] 本番セーブデータの物理バックアップ ---
OFFICIAL_SAVE="components/data/savefile/save_official.json"
BACKUP_SAVE="components/data/savefile/save_official.json.bak"

# 既にバックアップがある場合、前回の終了に失敗した可能性がある
if [ -f "$BACKUP_SAVE" ]; then
    echo "⚠️ 警告: 前回のバックアップファイル ($BACKUP_SAVE) が残っています。"
    echo "前回のテストが異常終了した可能性があります。手動で確認してください。"
    # 本番データが空、または異常な場合はバックアップから戻すなどの判断が必要だが、
    # ここでは安全のため、実行を停止してユーザーに委ねる
    exit 1
fi

if [ -f "$OFFICIAL_SAVE" ]; then
    echo "💾 本番セーブデータを一時的にバックアップします..."
    cp "$OFFICIAL_SAVE" "$BACKUP_SAVE"
fi

# スクリプト終了時に必ず復元する設定 (エラー時や中断時も含む)
function cleanup {
    # 最後に必ず復元を実行
    if [ -f "$BACKUP_SAVE" ]; then
        echo "🔄 バックアップから本番データを復元しています..."
        mv "$BACKUP_SAVE" "$OFFICIAL_SAVE"
        echo "✅ 本番データの復元が完了しました。"
    fi
}

# EXITだけでなく、Ctrl+C(INT)や終了要求(TERM)でもcleanupを走らせる
trap cleanup EXIT INT TERM

echo "----------------------------------------"
echo "🔍 セーブデータ隔離チェック実行中..."
$VENV_PYTHON "tests/test_save_isolation.py"
if [ $? -ne 0 ]; then
    echo "❌ 警告: セーブデータの隔離に失敗しました。テストを中止します。"
    exit 1
fi
echo "✅ 隔離確認完了。安全にテストを開始します。"

TEST_FILES=(
    "tests/test_boot.py"
    "tests/test_hitbox.py"
    "tests/test_accessory_pickup.py"
    "tests/test_shop_sell_accessory.py"
    "tests/test_save_load.py"
    "tests/test_revive_cure.py"
    "tests/test_death.py"
    "tests/test_shopping.py"
    "tests/test_quest.py"
    "tests/test_blacksmith.py"
    "tests/test_game_flow.py"
    "tests/test_combat_sim.py"
    "tests/test_npc_collision.py"
    "tests/test_enemy_collision.py"
    "tests/test_item_turn_consumption.py"
    "tests/test_equip_turn_consumption.py"
    "tests/test_town_services.py"
    "tests/test_inn_debt.py"
    "tests/test_stave_effects.py"
    "tests/test_combat_damage.py"
    "tests/test_combat_logic.py"
    "tests/test_attack_turn_transition.py"
    "tests/test_collision_phasing.py"
    "tests/test_decimal_impact.py"
    "tests/test_equipment_offsets.py"
    "tests/test_evasion.py"
    "tests/test_movement.py"
    "tests/test_rank_limit.py"
    "tests/test_trap.py"
    "tests/test_quest_feedback.py"
    "tests/test_quest_generation.py"
    "tests/test_delivery_all_types.py"
    "tests/test_boss_spawn.py"
    "tests/test_guild_autosave.py"
    "tests/test_dungeon_growth.py"
    "tests/test_outbreak_event.py"
    "tests/test_teleport_system.py"
    "tests/test_village_spawning.py"
    "tests/test_equipment_cross_stats.py"
    "tests/test_equip_kago_bonus.py"
    "tests/test_armor_penetration.py"
    "tests/test_blacksmith_stones.py"
    "tests/test_full_inventory_pickup.py"
    "tests/test_potions.py"
)

SUCCESS_COUNT=0
TOTAL_COUNT=${#TEST_FILES[@]}

for test in "${TEST_FILES[@]}"; do
    echo "----------------------------------------"
    echo "Running: $test"
    $VENV_PYTHON "$test"
    if [ $? -eq 0 ]; then
        echo "✅ $test: PASSED"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo "❌ $test: FAILED"
    fi
done

echo "========================================"
echo "📊 テスト結果報告: $SUCCESS_COUNT / $TOTAL_COUNT 合格"
echo "========================================"

if [ $SUCCESS_COUNT -eq $TOTAL_COUNT ]; then
    exit 0
else
    exit 1
fi
