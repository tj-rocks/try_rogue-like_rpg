#!/usr/bin/env python3
import os
import sys
import yaml

def check_referenced_paths(data, yaml_filepath, project_root):
    """YAMLデータ内に記述された画像やマップ等の外部ファイルパスが存在するかをチェックし、警告を出力する"""
    rel_yaml = os.path.relpath(yaml_filepath, project_root)
    warnings = []
    
    def traverse(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    traverse(v)
                elif isinstance(v, str):
                    # 画像パスの検証
                    if k in ("image_path", "base_image_path"):
                        if v.strip():
                            full_path = os.path.join(project_root, v)
                            exists = os.path.exists(full_path)
                            # 拡張子無しのディレクトリ指定に対応
                            if not exists:
                                for ext in (".png", ".jpg", ".jpeg"):
                                    if os.path.exists(full_path + ext):
                                        exists = True
                                        break
                            if not exists:
                                warnings.append(f"[{rel_yaml}] キー '{k}' で参照されているパスが存在しません: '{v}'")
                    
                    # マップファイルの検証
                    elif k == "map" and v.endswith(".txt"):
                        map_path = os.path.join(project_root, "components/data/dungeon", v)
                        if not os.path.exists(map_path):
                            warnings.append(f"[{rel_yaml}] 参照されているマップテキストが存在しません: '{v}' (期待されるパス: components/data/dungeon/{v})")
        elif isinstance(node, list):
            for item in node:
                traverse(item)

    traverse(data)
    return warnings

def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    master_data_dir = os.path.join(project_root, "components/data/master")
    
    print("==================================================")
    print("🔍 YAML マスターデータ バリデーション実行中...")
    print("==================================================")
    
    yaml_files = []
    for root, dirs, files in os.walk(master_data_dir):
        for file in files:
            if file.endswith((".yml", ".yaml")):
                yaml_files.append(os.path.join(root, file))

    if not yaml_files:
        print("❌ エラー: 検証対象のYAMLファイルが見つかりませんでした。")
        sys.exit(1)

    has_error = False
    total_warnings = 0
    total_files = len(yaml_files)
    
    for filepath in sorted(yaml_files):
        rel_path = os.path.relpath(filepath, project_root)
        file_has_error = False
        file_warnings = []
        
        # 1. 物理フォーマットチェック (タブ文字、全角スペースインデント)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for idx, line in enumerate(lines, 1):
                    if "\t" in line:
                        print(f"❌ [FORMAT ERROR] {rel_path}:{idx} - タブ文字(\\t)が検出されました。スペースを使用してください。")
                        file_has_error = True
                        has_error = True
                    
                    stripped = line.lstrip("\n\r")
                    if stripped.startswith("　"):
                        print(f"❌ [FORMAT ERROR] {rel_path}:{idx} - 行頭に全角スペースが使用されています。")
                        file_has_error = True
                        has_error = True
        except Exception as e:
            print(f"❌ [READ ERROR] {rel_path} の読み込みに失敗しました: {e}")
            file_has_error = True
            has_error = True
            continue

        # 2. YAML構文パースチェック
        data = None
        if not file_has_error:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            except Exception as e:
                print(f"❌ [PARSE ERROR] {rel_path} の構文パースに失敗しました:\n{e}")
                file_has_error = True
                has_error = True

        # 3. 参照リンク切れチェック (Warning扱い)
        if not file_has_error and data:
            file_warnings = check_referenced_paths(data, filepath, project_root)
            total_warnings += len(file_warnings)

        # 4. 結果表示
        if file_has_error:
            # 既に個別のエラー詳細が出力されているため、ここではファイル単位の失敗のみ示す
            print(f"🔴 {rel_path}: 失敗 (ERROR)")
        elif file_warnings:
            print(f"⚠️ {rel_path}: パス未存在の警告あり ({len(file_warnings)}件)")
            for w in file_warnings:
                print(f"   [WARNING] {w}")
        else:
            print(f"✅ {rel_path}: 正常 (OK)")

    print("==================================================")
    print("📊 検証完了レポート:")
    print(f"  - 検証ファイル数: {total_files}")
    print(f"  - 警告（警告・パス未存在）: {total_warnings}件")
    
    if has_error:
        print("🔴 結果: 失敗 (構文エラーまたはフォーマットエラーがあります)")
        sys.exit(1)
    else:
        print("💚 結果: 成功 (構文・フォーマットはすべて正常です)")
        sys.exit(0)

if __name__ == "__main__":
    main()
