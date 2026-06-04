import os
import re
import sys
import difflib

# Regex to match single or double quoted strings
string_literal_re = re.compile(r'f?"[^"\\]*(?:\\.[^"\\]*)*"|f?\'[^\'\\]*(?:\\.[^\'\\]*)*\'')

# Define emoji codepoint checker
def is_emoji(c):
    o = ord(c)
    # Check common emoji blocks:
    if (0x1F300 <= o <= 0x1F9FF) or (0x1F000 <= o <= 0x1FAFF):
        return True
    if (0x2600 <= o <= 0x27BF):
        # Keep standard star U+2605
        if o == 0x2605:
            return False
        return True
    if o == 0xFE0F:
        return True
    return False

def remove_emojis_and_spaces(text):
    result = []
    i = 0
    n = len(text)
    while i < n:
        if is_emoji(text[i]):
            i += 1
            if i < n and text[i] == ' ':
                i += 1
        else:
            result.append(text[i])
            i += 1
    return "".join(result)

def process_text_periods(text):
    skip_chars = set(['"', "'", '」', '』', ')', ']', '}', ' ', '\n', '\r', '\t'])
    
    idx = len(text) - 1
    found_end_period_idx = -1
    while idx >= 0:
        c = text[idx]
        if c in skip_chars:
            idx -= 1
            continue
        elif c == '。':
            found_end_period_idx = idx
            break
        else:
            break
            
    if found_end_period_idx != -1:
        part_before = text[:found_end_period_idx].replace('。', ' ')
        part_after = text[found_end_period_idx+1:]
        return part_before + part_after
    else:
        return text.replace('。', ' ')

def replace_periods_in_string(s):
    stripped = s.strip()
    if (stripped.startswith('"') and stripped.endswith('"')) or (stripped.startswith("'") and stripped.endswith("'")):
        quote_char = stripped[0]
        inner = stripped[1:-1]
        processed_inner = process_text_periods(inner)
        leading_spaces = s[:s.find(quote_char)]
        trailing_spaces = s[s.rfind(quote_char)+1:]
        return f"{leading_spaces}{quote_char}{processed_inner}{quote_char}{trailing_spaces}"
    else:
        return process_text_periods(s)

def split_comment_by_quotes(line):
    spans = []
    for match in string_literal_re.finditer(line):
        spans.append(match.span())
        
    for i, c in enumerate(line):
        if c == '#':
            in_span = False
            for start, end in spans:
                if start <= i < end:
                    in_span = True
                    break
            if not in_span:
                # Require '#' to be at start of line or preceded by whitespace
                if i == 0 or line[i-1].isspace():
                    return line[:i], line[i:]
    return line, ''

def process_yaml_line(line):
    # Split comment
    code_part, comment_part = split_comment_by_quotes(line)
    
    # Remove emojis
    code_part = remove_emojis_and_spaces(code_part)
    comment_part = remove_emojis_and_spaces(comment_part)
    
    stripped = code_part.strip()
    if not stripped:
        return code_part + comment_part
        
    if ':' in code_part:
        key, val = code_part.split(':', 1)
        processed_val = replace_periods_in_string(val)
        return f"{key}:{processed_val}{comment_part}"
    elif code_part.strip().startswith('-'):
        idx_dash = code_part.find('-')
        indent = code_part[:idx_dash]
        val = code_part[idx_dash+1:]
        processed_val = replace_periods_in_string(val)
        return f"{indent}-{processed_val}{comment_part}"
    else:
        return f"{replace_periods_in_string(code_part)}{comment_part}"

def process_python_line(line):
    # Split comment
    code_part, comment_part = split_comment_by_quotes(line)
    
    # Remove emojis
    code_part = remove_emojis_and_spaces(code_part)
    comment_part = remove_emojis_and_spaces(comment_part)
    
    stripped = code_part.strip()
    if not stripped:
        return code_part + comment_part
        
    def repl_func(match):
        raw_str = match.group(0)
        prefix = ""
        if raw_str.startswith('f') or raw_str.startswith('F'):
            prefix = raw_str[0]
            raw_str = raw_str[1:]
        quote_char = raw_str[0]
        inner = raw_str[1:-1]
        processed_inner = process_text_periods(inner)
        return f"{prefix}{quote_char}{processed_inner}{quote_char}"
        
    processed_code = string_literal_re.sub(repl_func, code_part)
    return processed_code + comment_part

def process_file(filepath, dry_run=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    is_yaml = filepath.endswith('.yml') or filepath.endswith('.yaml')
    new_lines = []
    
    for line in lines:
        if is_yaml:
            new_lines.append(process_yaml_line(line))
        else:
            new_lines.append(process_python_line(line))
            
    if lines != new_lines:
        print(f"\n--- {filepath} (modified)")
        diff = difflib.unified_diff(lines, new_lines, fromfile=filepath, tofile=filepath + '.new')
        sys.stdout.writelines(diff)
        
        if not dry_run:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"--> Saved changes to {filepath}")
        return True
    return False

def main():
    dry_run = '--execute' not in sys.argv
    root_dir = '/Users/tj/Desktop/2DGame'
    
    target_files = []
    for root, dirs, files in os.walk(root_dir):
        if any(p in root for p in ['venv', '.git', '.github', '__pycache__', 'scratch', 'tests']):
            continue
        for file in files:
            if file.endswith('.yml') or file.endswith('.yaml'):
                target_files.append(os.path.join(root, file))
            elif file in ['wordings.py', 'ui.py', 'magic_handler.py']:
                target_files.append(os.path.join(root, file))
                
    modified_count = 0
    for path in target_files:
        if process_file(path, dry_run=dry_run):
            modified_count += 1
            
    print(f"\nScan finished. Total modified files: {modified_count}")
    if dry_run:
        print("Note: Running in DRY-RUN mode. Pass '--execute' to actually apply changes.")

if __name__ == '__main__':
    main()
