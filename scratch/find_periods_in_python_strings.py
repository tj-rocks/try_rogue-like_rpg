import ast
import os

def find_periods_in_ast(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content, filename=filepath)
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
        return []

    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if '。' in node.value:
                found.append((node.lineno, node.value))
    return found

def main():
    root_dir = '/Users/tj/Desktop/2DGame'
    py_files = []
    for root, dirs, files in os.walk(root_dir):
        if any(p in root for p in ['venv', '.git', '.github', '__pycache__', 'scratch', 'tests']):
            continue
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))

    print("=== STRING LITERALS CONTAINING PERIODS ===")
    for filepath in py_files:
        rel_path = os.path.relpath(filepath, root_dir)
        matches = find_periods_in_ast(filepath)
        if matches:
            print(f"\nFile: {rel_path}")
            for lineno, val in matches:
                print(f"  Line {lineno}: {repr(val)}")

if __name__ == '__main__':
    main()
