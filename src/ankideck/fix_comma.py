#!/usr/bin/env python3
"""
fix_comma.py

Usage:
  python fix_comma.py input.csv [output.csv]

If output.csv is omitted, a file named input_fixed.csv will be created next to input.
Use --inplace to replace the input file (will create a backup with .bak extension).

Behavior:
  - For each row, keep only the first comma as the column separator.
  - Replace any other commas in the rest of the row with semicolons.
  - If a row has no comma, a trailing comma is appended to make it two columns.
"""
import argparse
from pathlib import Path
import sys
import shutil

def fix_line(line: str) -> str:
    # Preserve newline at end, if any
    nl = ''
    if line.endswith('\n'):
        nl = '\n'
        line = line[:-1]

    idx = line.find(',')
    if idx == -1:
        # no comma: append trailing comma to make two columns
        return line + ',' + nl
    left = line[:idx]
    right = line[idx+1:]
    # replace all commas in the right side with semicolons
    right_fixed = right.replace(',', ';')
    return left + ',' + right_fixed + nl


def process_file(input_path: Path, output_path: Path) -> dict:
    counts = {
        'lines': 0,
        'no_comma': 0,
        'changed': 0,
    }
    with input_path.open('r', encoding='utf-8', errors='replace') as r, \
         output_path.open('w', encoding='utf-8', newline='') as w:
        for line in r:
            counts['lines'] += 1
            if ',' not in line:
                counts['no_comma'] += 1
            fixed = fix_line(line)
            if fixed != line:
                counts['changed'] += 1
            w.write(fixed)
    return counts


def main(argv=None):
    p = argparse.ArgumentParser(description='Keep only first comma per row and replace later commas with semicolons.')
    p.add_argument('input', help='Input CSV file path')
    p.add_argument('output', nargs='?', help='Output CSV file path (optional)')
    p.add_argument('--inplace', action='store_true', help='Replace the input file in-place (backup created with .bak)')
    args = p.parse_args(argv)

    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"Input file does not exist: {input_path}", file=sys.stderr)
        return 2

    if args.inplace:
        backup = input_path.with_suffix(input_path.suffix + '.bak')
        shutil.copy2(str(input_path), str(backup))
        tmp_out = input_path.with_suffix(input_path.suffix + '.tmp')
        counts = process_file(input_path, tmp_out)
        # replace original
        tmp_out.replace(input_path)
        print(f"In-place update done. Backup created: {backup}")
    else:
        if args.output:
            output_path = Path(args.output).expanduser().resolve()
        else:
            output_path = input_path.with_name(input_path.stem + '_fixed' + input_path.suffix)
        counts = process_file(input_path, output_path)
        print(f"Output written to: {output_path}")

    print(f"Lines processed: {counts['lines']}")
    print(f"Lines with no comma (added trailing comma): {counts['no_comma']}")
    print(f"Lines changed: {counts['changed']}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
