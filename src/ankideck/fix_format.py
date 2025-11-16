#!/usr/bin/env python3
"""
fix_format.py

Usage:
  python fix_format.py input.csv [output.csv] [--find CHAR] [--second-semicolon]

If output.csv is omitted, a file named input_fixed.csv will be created next to input.
Use --inplace to replace the input file (will create a backup with .bak extension).

Behavior:
  Default mode:
  - For each row, keep only the first occurrence of the specified delimiter (default: comma).
  - Replace any other occurrences of that delimiter with tab characters.
  - If a row has no delimiter, a trailing delimiter is appended to make it two columns.
  
  Second semicolon mode (--second-semicolon):
  - Replace only the second semicolon in each line with a tab character.
  - Leave the first semicolon and all other characters unchanged.

Examples:
  # Keep first comma, replace others with tabs (default behavior)
  python fix_format.py input.csv

  # Keep first semicolon, replace others with tabs
  python fix_format.py input.csv --find ';'

  # Replace only the second semicolon with tab
  python fix_format.py input.csv --second-semicolon

  # Keep first pipe, replace others with tabs  
  python fix_format.py input.csv --find '|'
"""
import argparse
from pathlib import Path
import sys
import shutil

def fix_line(line: str, find_char: str = ',', replace_char: str = '\t') -> str:
    # Preserve newline at end, if any
    nl = ''
    if line.endswith('\n'):
        nl = '\n'
        line = line[:-1]

    idx = line.find(find_char)
    if idx == -1:
        # no delimiter found: append trailing delimiter to make two columns
        return line + find_char + nl
    left = line[:idx]
    right = line[idx+1:]
    # replace all occurrences of find_char in the right side with replace_char
    right_fixed = right.replace(find_char, replace_char)
    return left + find_char + right_fixed + nl


def fix_line_second_semicolon(line: str) -> str:
    """Replace only the second semicolon in a line with a tab character."""
    # Preserve newline at end, if any
    nl = ''
    if line.endswith('\n'):
        nl = '\n'
        line = line[:-1]
    
    # Find the first semicolon
    first_idx = line.find(';')
    if first_idx == -1:
        # No semicolon found, return as is
        return line + nl
    
    # Find the second semicolon
    second_idx = line.find(';', first_idx + 1)
    if second_idx == -1:
        # Only one semicolon found, return as is
        return line + nl
    
    # Replace only the second semicolon with tab
    result = line[:second_idx] + '\t' + line[second_idx + 1:]
    return result + nl


def process_file(input_path: Path, output_path: Path, find_char: str = ',', replace_char: str = '\t') -> dict:
    counts = {
        'lines': 0,
        'no_delimiter': 0,
        'changed': 0,
    }
    with input_path.open('r', encoding='utf-8', errors='replace') as r, \
         output_path.open('w', encoding='utf-8', newline='') as w:
        for line in r:
            counts['lines'] += 1
            if find_char not in line:
                counts['no_delimiter'] += 1
            fixed = fix_line(line, find_char, replace_char)
            if fixed != line:
                counts['changed'] += 1
            w.write(fixed)
    return counts


def process_file_second_semicolon(input_path: Path, output_path: Path) -> dict:
    """Process file to replace only the second semicolon with tab."""
    counts = {
        'lines': 0,
        'no_second_semicolon': 0,
        'changed': 0,
    }
    with input_path.open('r', encoding='utf-8', errors='replace') as r, \
         output_path.open('w', encoding='utf-8', newline='') as w:
        for line in r:
            counts['lines'] += 1
            # Count lines that don't have a second semicolon
            first_idx = line.find(';')
            if first_idx == -1 or line.find(';', first_idx + 1) == -1:
                counts['no_second_semicolon'] += 1
            
            fixed = fix_line_second_semicolon(line)
            if fixed != line:
                counts['changed'] += 1
            w.write(fixed)
    return counts


def main(argv=None):
    p = argparse.ArgumentParser(description='Keep only first occurrence of a delimiter per row and replace later occurrences with tab characters.')
    p.add_argument('input', help='Input CSV file path')
    p.add_argument('output', nargs='?', help='Output CSV file path (optional)')
    p.add_argument('--inplace', action='store_true', help='Replace the input file in-place (backup created with .bak)')
    p.add_argument('--find', default=',', help='Character to find and keep only the first occurrence (default: ",")')
    p.add_argument('--second-semicolon', action='store_true', help='Replace only the second semicolon with tab (ignores --find option)')
    args = p.parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"Input file does not exist: {input_path}", file=sys.stderr)
        return 2

    if args.inplace:
        backup = input_path.with_suffix(input_path.suffix + '.bak')
        shutil.copy2(str(input_path), str(backup))
        tmp_out = input_path.with_suffix(input_path.suffix + '.tmp')
        
        if args.second_semicolon:
            counts = process_file_second_semicolon(input_path, tmp_out)
        else:
            counts = process_file(input_path, tmp_out, args.find, '\t')
        
        # replace original
        tmp_out.replace(input_path)
        print(f"In-place update done. Backup created: {backup}")
    else:
        if args.output:
            output_path = Path(args.output).expanduser().resolve()
        else:
            output_path = input_path.with_name(input_path.stem + '_fixed' + input_path.suffix)
        
        if args.second_semicolon:
            counts = process_file_second_semicolon(input_path, output_path)
        else:
            counts = process_file(input_path, output_path, args.find, '\t')
        
        print(f"Output written to: {output_path}")

    print(f"Lines processed: {counts['lines']}")
    
    if args.second_semicolon:
        print(f"Lines with no second semicolon: {counts['no_second_semicolon']}")
    else:
        print(f"Lines with no {args.find} (added trailing {args.find}): {counts['no_delimiter']}")
    
    print(f"Lines changed: {counts['changed']}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
