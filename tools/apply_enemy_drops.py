#!/usr/bin/env python3
"""
CSVファイルから敵のドロップ設定を読み込み、enemies.ymlに反映するツール

使い方:
  1. tools/enemy_drops.csv を編集する（ドロップアイテム欄を埋める）
  2. このスクリプトを実行: ./venv/bin/python tools/apply_enemy_drops.py
  3. YAMLファイルが更新される
"""

import csv
import yaml
import sys
from pathlib import Path

def load_csv(filepath):
    """CSVファイルを読み込む"""
    enemies = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            enemies.append({
                'rank': row['ランク'],
                'key': row['敵キー'],
                'name': row['敵名'],
                'normal': row['ドロップ通常'].strip() if row['ドロップ通常'] else '',
                'rare': row['ドロップレア'].strip() if row['ドロップレア'] else '',
                'boss': row['ボス'].strip(),
                'normal_rate': float(row['通常率']) if row['通常率'] else 0.1,
                'rare_rate': float(row['レア率']) if row['レア率'] else 0.0,
            })
    return enemies

def parse_drop_list(drop_str):
    """ドロップ文字列をリストに変換（空白区切り）"""
    if not drop_str:
        return []
    return [item.strip() for item in drop_str.split() if item.strip()]

def apply_drops_to_yaml(csv_data, yaml_path):
    """CSVデータをYAMLに反映"""
    # YAML読み込み
    with open(yaml_path, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f)
    
    enemy_data = yaml_data.get('ENEMY_DATA', {})
    
    updated_count = 0
    for enemy_info in csv_data:
        key = enemy_info['key']
        if key not in enemy_data:
            print(f"⚠ 警告: enemies.yml に '{key}' が見つかりません")
            continue
        
        enemy = enemy_data[key]
        normal_drops = parse_drop_list(enemy_info['normal'])
        rare_drops = parse_drop_list(enemy_info['rare'])
        
        # ドロップ情報を更新
        if 'drops' not in enemy:
            enemy['drops'] = {}
        
        enemy['drops']['normal'] = normal_drops
        enemy['drops']['rare'] = rare_drops
        enemy['normal_drop_rate'] = enemy_info['normal_rate']
        enemy['rare_drop_rate'] = enemy_info['rare_rate']
        
        updated_count += 1
        print(f"✅ {enemy_info['name']}: {len(normal_drops)}個通常, {len(rare_drops)}個レア")
    
    # YAML保存
    with open(yaml_path, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, allow_unicode=True, sort_keys=False, 
                  default_flow_style=False, indent=2)
    
    print(f"\n📊 更新完了: {updated_count}体の敵を更新しました")
    return updated_count

def main():
    # パス設定
    base_dir = Path(__file__).parent.parent
    csv_path = base_dir / 'tools' / 'enemy_drops.csv'
    yaml_path = base_dir / 'components' / 'data' / 'master' / 'enemies.yml'
    
    # ファイル存在確認
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        sys.exit(1)
    
    if not yaml_path.exists():
        print(f"❌ YAMLファイルが見つかりません: {yaml_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("敵ドロップCSV → YAML 反映ツール")
    print("=" * 60)
    print(f"CSV: {csv_path}")
    print(f"YAML: {yaml_path}")
    print("-" * 60)
    
    # CSV読み込み
    csv_data = load_csv(csv_path)
    print(f"📋 CSVから {len(csv_data)}体の敵を読み込みました\n")
    
    # YAMLに反映
    apply_drops_to_yaml(csv_data, yaml_path)
    
    print("\n✨ 完了！YAMLファイルが更新されました")
    print("⚠️ バリデーションを実行してください:")
    print("  ./venv/bin/python tools/validate_yaml.py")

if __name__ == '__main__':
    main()
