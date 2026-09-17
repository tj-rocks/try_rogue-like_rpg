# ギルドとダンジョン 〜父の軌跡〜

Pygameで制作している、物語重視の2DローグライクRPGです。

行方不明になった父の足跡を追い、冒険者ギルドで依頼をこなしながら、全99階層のダンジョン最深部を目指します。装備収集・鍛冶・ランク昇格・状態異常などを活用し、その場の状況に合わせて進むターン制ゲームです。

## ゲームの特徴

- ギルドの依頼を達成して冒険者ランクを上げ、より深い階層へ挑戦
- 通常フロアは自動生成され、10階ごとに休憩地点や固定マップが登場
- 武器・防具・盾・指輪・杖・鉱石など、多様なアイテムを収集
- 鍛冶屋で装備を強化し、通常鉱石と黄金鉱石を使い分けて育成
- 毒・麻痺・混乱・封印などの状態異常、罠、モンスター大量発生、特殊行動を持つ敵
- 「転移の石」や「復活のお守り」など、探索を支えるレアアイテム
- 地下50階の父親イベント、地下99階の最終ボス、選択によって変化するエンディング
- セーブ／ロード、ロード中のプログレスバー、キー連打を抑制するUI入力制御

## 基本操作

| キー | 操作 |
| --- | --- |
| 矢印キー | 移動／カーソル移動 |
| Space | 攻撃／決定／調べる |
| X | キャンセル／前の画面へ戻る |
| M | メインメニューを開く |
| I | アイテム画面を開く |
| S | ステータス画面を開く |
| Tab | マップ表示の切り替え |
| Shift＋矢印キー | 移動せずに向きを変える |
| F12 | デバッグログの表示切り替え |

タイトル画面や一部の会話では、EnterまたはZでも文章を進められます。

## 起動方法

Python 3と、`requirements.txt`に記載されたライブラリが必要です。

```bash
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python main.py
```

主な依存ライブラリは次の2つです。

- pygame
- PyYAML

## ゲーム進行

ギルドランクによって、挑戦できる最深階が決まります。

| ランク | 到達可能階層 |
| --- | ---: |
| 無所属 | 地下0階 |
| F | 地下11階 |
| E | 地下21階 |
| D | 地下30階 |
| C | 地下40階 |
| B | 地下55階 |
| A | 地下70階 |
| S／SS | 地下99階 |

ギルドの説明文や依頼目標も、この階層設定に合わせて管理しています。

## データとバランス調整

敵・アイテム・依頼・会話・バランス値などはYAMLに分離しており、プログラムを大きく変更せずに調整できます。

| ファイル | 内容 |
| --- | --- |
| `components/data/master/balance.yml` | 戦闘、成長、階層、UI入力間隔などの共通バランス |
| `components/data/master/enemies.yml` | 敵の能力値・分類・見た目 |
| `components/data/master/skills.yml` | 敵を含む各種スキル |
| `components/data/master/enemy_attack_effects.yml` | 敵の通常攻撃に付随する効果 |
| `components/data/master/items.yml` | 消耗品、鉱石、レア度、効果 |
| `components/data/master/equipments/` | 武器・防具・盾・装飾品 |
| `components/data/master/quests.yml` | ギルド依頼 |
| `components/data/master/guild.yml` | ランクと到達可能階層 |
| `components/data/master/story.yml` | ストーリーと会話イベント |
| `components/data/master/restpoint/` | 休憩地点などの固定マップ |
| `components/data/master/ui.yml` | 表示文言やUI設定 |
| `components/data/master/village.yml` | 村の施設設定 |

現在、敵の攻撃力は `balance.yml` の共通倍率で調整しています。

- 近距離攻撃：`0.70`
- 遠距離攻撃：`0.60`

## 主なディレクトリ

```text
2DGame/
├── main.py                 # エントリーポイント
├── constants.py            # 共通定数とマスターデータ読み込み
├── components/sprites/     # プレイヤー・敵・NPCなど
├── components/data/master/ # YAMLマスターデータ
├── components/data/savefile/ # セーブデータ
├── components/pictures/    # 画像素材
├── components/sounds/      # BGM・効果音
├── systems/                # 戦闘・ダンジョン・ギルド・UIなど
├── tools/                  # 編集・検証・バランス調整ツール
└── tests/                  # 自動テスト
```

## テスト

正式テストランナーは、各テストを独立プロセスで実行します。テスト用フラグとセーブデータの退避・復元も自動で行われます。

```bash
# 全テスト
bash tests/run_tests.sh all

# 変更ファイルに関係するテスト
bash tests/run_tests.sh changed

# 単体テスト
./venv/bin/python tests/test_master_data.py
```

2026年8月30日時点で、正式テストスイートは **46 / 46件成功** です。詳しい使い方は [tests/README.md](tests/README.md) を参照してください。

## 開発方針

- ゲームデータと処理を分離し、YAML中心で調整できる構成にする
- 自動テストで既存挙動を保護しながら変更する
- 戦闘ログは自然で読みやすい日本語にする
- フォント、画像、音声をキャッシュし、探索中の負荷を抑える
- キー入力に短い受付間隔を設け、連打やキーリピートによる画面遷移の暴発を防ぐ

詳細な設計思想と世界観は [philosophy_and_lore.md](philosophy_and_lore.md) にまとめています。

## 開発補助ツール

- `tools/settings_editor.py`：設定編集
- `tools/validate_yaml.py`：YAML検証
- `tools/verify_combat_balance.py`：戦闘バランス検証
- `tools/戦闘バランス調整.py`：戦闘パラメーター調整
- `tools/村作りツール.py`：村データ編集
- `tools/装備位置調整.py`：装備画像の位置調整
- `tools/web/`：ブラウザで使用する各種編集・調整画面

## 最近の主な改善

- ダンジョン素材読み込み中のプログレスバーを追加
- メニュー操作に入力間隔を設け、連続入力によるフリーズや誤操作を抑制
- 敵の近距離・遠距離攻撃倍率を一か所で調整できるよう変更
- プレイヤー行動ログから不自然な「自分 は」を削除
- 商人と鍛冶屋を行き来した際に古い確認処理が残る問題を修正
- ギルドのボス出現階層と説明文を実際の設定に統一
- 「転移の石」と「復活のお守り」のレア度を調整
