# 🗡️ 2D Rogue-like RPG project

Pygame ベースで開発している、物語重視の 2D ローグライク RPG です。  
自動生成ダンジョンと固定マップ、装備成長、ギルドランク、分岐エンディング、ボスとの読み合い戦闘を YAML 主導で組み上げています。

---

## いま遊べる要素

- ギルド加入から始まるランク制の進行
- 階層ごとに雰囲気が変わるダンジョン探索
- 10F ごとの休憩所 / 固定マップ
- 武器 / 鎧 / 盾 / 指輪 / 杖 / 鉱石によるビルド
- 鍛冶屋での通常強化とスキル強化
- 状態異常、罠、アウトブレイク、各種 NPC サービス
- 50F の父イベント
- 99F のラスボス戦と 2 系統のエンディング

---

## 操作方法

| キー | アクション |
| :--- | :--- |
| `矢印キー` | 移動 / カーソル操作 |
| `Z` / `Enter` | 決定 / 攻撃 / 調べる |
| `X` / `Esc` | キャンセル / メニュー |
| `Shift + 矢印` | その場で方向転換 |

---

## 起動

通常起動:

```bash
./venv/bin/python main.py
```

---

## プロジェクト構造

### マスターデータ

`components/data/master/` 配下の YAML を編集することで、バランスや演出をコード変更なしで調整できます。

- `dungeon.yml`: 階層ごとの地形、明るさ、BGM、固定マップ設定
- `enemies.yml`: 敵ステータス、特殊行動、出現条件、ボス設定
- `items.yml`: 消費アイテム、杖、鉱石、素材
- `equipments/*.yml`: 武器 / 鎧 / 盾 / 指輪の性能
- `story.yml`: オープニング / エンディング文面
- `balance.yml`: 全体バランス、各種係数、行動傾向テーブル
- `restpoint/*.yml`: 休憩所や最終固定マップの NPC / 配置情報

### コア実装

- `main.py`: 通常起動エントリポイント
- `components/sprites/`: プレイヤー、敵、NPC、罠などの実体
- `systems/`: ダンジョン進行、戦闘、UI、セーブ、イベント制御
- `components/data/savefile/`: セーブデータ

---

## 現在の設計方針

- データはできるだけ YAML 側で持つ
- 専用分岐は増やしすぎず、共通処理で吸収する
- 強さだけでなく「読み合い」や「選択の意味」を重視する
- ローグライクの試行錯誤と、物語の余韻を両立する

詳しい世界設定や思想は [philosophy_and_lore.md](/Users/tj/Desktop/2DGame/philosophy_and_lore.md) にまとめています。

---

## 自動テスト

一括実行:

```bash
bash tests/run_tests.sh all
```

変更ファイルに応じた実行:

```bash
bash tests/run_tests.sh changed
```

個別実行例:

```bash
./venv/bin/python tests/test_blacksmith_stones.py
```

テスト実行時は `TEST_MODE=1` が有効になり、本番セーブデータを退避したうえで検証します。

2026-07-08 時点では `46 / 46` テスト通過を確認済みです。

テスト一覧の概要は [tests/README.md](/Users/tj/Desktop/2DGame/tests/README.md) を参照してください。

---

## デバッグ / 調整ツール

- `tools/ダンジョン系のデバッグ.py`: 階層・装備・所持品を切り替えながら戦闘や進行を確認
- `tools/村作りツール.py`: 固定マップ / 村マップの配置編集
- `tools/settings_editor.py` / `tools/web/settings_editor.html`: 各種 YAML 設定の編集補助
- `tools/オートバランス調整.py`
- `tools/戦闘バランス調整.py`
- `tools/モンスターその他調整.py`
- `tools/BGMかぶりチェッカー.py`
- `tools/validate_yaml.py`

補助ドキュメント:

- [tools/DEBUG_GUIDE.md](/Users/tj/Desktop/2DGame/tools/DEBUG_GUIDE.md)

---

## 最近の実装に合う見どころ

- ラスボス `dungeon_core` は通常敵とは別系統の行動ロジックを持ち、位置関係やプレイヤー傾向を見て行動を変えます
- S ランク帯には既存ボスの残像的な雑魚敵が追加されています
- 敵ごとに `smart_ranged_move` や `stupidity` を使い分け、立ち回りに個性を持たせています
- 罠設置、ノックバック、暗闇など、特殊行動を敵データ側から付与できます
- 金の鉱石 (`gold_ore`) によるスキル強化ルートがあります

---

## 注意

- 日本語ファイル名のツールが含まれます
- セーブデータを直接触る場合は `components/data/savefile/` のバックアップ推奨です
- 固定マップ階層やボス周りは、通常階層とは別ルールが混ざるため QA 時は個別確認が安全です
