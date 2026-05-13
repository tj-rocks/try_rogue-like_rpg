#!/bin/bash
# run_tests.sh - 全ての自動テストを実行する

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
    "tests/test_lantern_pickup.py"
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
