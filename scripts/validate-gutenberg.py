#!/usr/bin/env python3
"""
validate-gutenberg.py — Gutenberg block delimiter & signature validator.

Verifies that:
1. Every opening <!-- wp:block --> has a matching <!-- /wp:block --> (except self-closing <!-- wp:... /-->).
2. The block stack is completely balanced (no unclosed containers causing innerBlocks cascading).
3. If an AI signature ("Written by") is present, it appears EXACTLY ONCE and is at the footer.

Usage:
  python3 scripts/validate-gutenberg.py <file.html>
  cat <file.html> | python3 scripts/validate-gutenberg.py -
"""

import sys
import re

def validate_gutenberg(content, filename="<input>"):
    lines = content.splitlines(keepends=True)
    
    # Regex to match Gutenberg comments
    # Matches: <!-- wp:name attrs --> or <!-- /wp:name --> or <!-- wp:name /-->
    block_pattern = re.compile(r'<!--\s*(/?wp:[a-z0-9_-]+(?:/[a-z0-9_-]+)?)\s*(.*?)\s*(/)?-->', re.DOTALL)
    
    stack = []
    errors = []
    
    # Helper to find line number from character offset
    line_offsets = []
    cur_offset = 0
    for line in lines:
        line_offsets.append(cur_offset)
        cur_offset += len(line)
        
    def get_line_no(char_pos):
        # binary search or simple scan
        for idx, offset in enumerate(line_offsets):
            if char_pos < offset:
                return idx
        return len(line_offsets)

    block_count = 0
    for m in block_pattern.finditer(content):
        tag = m.group(1)
        attrs = m.group(2).strip()
        is_slash = m.group(3) or attrs.endswith('/')
        char_pos = m.start()
        line_no = get_line_no(char_pos)
        
        # Check if self closing
        if is_slash:
            block_count += 1
            continue
            
        if tag.startswith('/'):
            expected = tag[1:]
            if not stack:
                errors.append(f"Line {line_no}: Unexpected closing tag '{tag}' with empty stack.")
            else:
                popped = stack.pop()
                if popped['tag'] != expected:
                    errors.append(f"Line {line_no}: Mismatched closing tag '{tag}', expected '/{popped['tag']}' (opened at line {popped['line_no']}).")
        else:
            stack.append({
                'tag': tag,
                'line_no': line_no,
                'pos': char_pos,
                'snippet': content[char_pos:min(len(content), char_pos + 60)].replace('\n', ' ')
            })
            block_count += 1

    if stack:
        for item in stack:
            errors.append(f"Line {item['line_no']}: Unclosed block '{item['tag']}' (snippet: {item['snippet']}...)")

    # Signature verification (exclude code blocks / escaped examples)
    sig_matches = []
    in_code = False
    for i, line in enumerate(lines):
        if "<pre" in line or "&lt;pre" in line or "<!-- wp:code" in line:
            in_code = True
        if "Written by" in line and not in_code and "&lt;" not in line:
            sig_matches.append(i + 1)
        if "</pre>" in line or "&lt;/pre&gt;" in line or "<!-- /wp:code" in line:
            in_code = False

    if len(sig_matches) > 1:
        errors.append(f"Multiple AI signatures detected at lines: {sig_matches}. SOP requires signing only once at the end.")
    elif len(sig_matches) == 1:
        sig_line = sig_matches[0]
        # Ensure it's in the last 20 lines of the file
        if sig_line < max(1, len(lines) - 20):
            errors.append(f"Line {sig_line}: AI signature found, but not at the end of the post (total lines: {len(lines)}).")

    if errors:
        print(f"FAILED: {filename} has {len(errors)} Gutenberg validation error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return False

    print(f"PASSED: {filename} is valid Gutenberg markup ({block_count} blocks, stack balanced, signature verified).")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: validate-gutenberg.py <file.html|- >", file=sys.stderr)
        sys.exit(2)
        
    target = sys.argv[1]
    if target == "-":
        content = sys.stdin.read()
        filename = "<stdin>"
    else:
        try:
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
            filename = target
        except Exception as e:
            print(f"Error reading {target}: {e}", file=sys.stderr)
            sys.exit(1)
            
    if not validate_gutenberg(content, filename):
        sys.exit(1)

if __name__ == "__main__":
    main()
