#!/usr/bin/env python3
"""
validate-sanitization.py — Pre-flight security & RFC compliance sanitizer for blog posts.

Enforces zero leakage of:
1. Physical locations & street names (e.g. Hildreth, bedroom desktop/VM references).
2. Internal homelab subnets & private host IPs (10.10.152.x, 172.17.48.x, 172.16.15.x, 192.168.1.24).
3. Personal hardware specs & serials (AMD Ryzen 7 5800X, RTX 3080, Dell PowerEdge R630, Toshiba drives).
4. Internal cluster hostnames & daemon IDs (node1, pbs0, HIL-WS-01, WS-01, hildreth-hosting-152).
5. Non-RFC domains (client domains like miraclepaving.com, client-app.com; must use RFC 2606 *.example.com).
6. Live synthetic UUIDs/tokens (must use explicit bracketed placeholders like <YOUR-TUNNEL-UUID>).
7. Internal container IDs & disk allocations (CT 300/301/105, vm-105-disk-0).

Usage:
  python3 scripts/validate-sanitization.py <file.html|file.md>
  cat <file> | python3 scripts/validate-sanitization.py -
"""

import sys
import os
import re

FORBIDDEN_PATTERNS = [
    # 1. Physical location & living spaces
    (r'\bHildreth\b', "Physical location leak ('Hildreth'). Use 'primary site' or generic term."),
    (r'\bbedroom\s+(?:desktop|VM|server|rig|host|lab)\b', "Personal living space reference ('bedroom ...'). Use 'workstation VM' or 'nested desktop VM'."),

    # 2. Private IP subnets & non-documentation IPs
    (r'10\.10\.152\.\d+', "Private homelab IP subnet (10.10.152.x). Use RFC 1918 doc subnet (10.0.10.x)."),
    (r'172\.17\.48\.\d+', "Private hypervisor IP subnet (172.17.48.x). Use RFC 1918 doc subnet (172.16.10.x)."),
    (r'172\.16\.15\.\d+', "Private management subnet (172.16.15.x). Use RFC 1918 doc subnet (10.0.1.x or 10.0.10.x)."),
    (r'192\.168\.1\.24\b', "Specific private host IP (192.168.1.24). Use generic host IP (192.168.1.100)."),

    # 3. Personal hardware specs & chassis models
    (r'\bRyzen\s+7\s+5800X\b', "Specific personal CPU model ('Ryzen 7 5800X'). Use '8-core desktop processor'."),
    (r'\b(?:GeForce\s+)?RTX\s+3080\b', "Specific personal GPU model ('RTX 3080'). Use 'workstation GPU' or generic term."),
    (r'\b(?:Dell\s+)?(?:PowerEdge\s+)?R630\b', "Specific chassis model ('Dell PowerEdge R630'). Use '1U enterprise rack server'."),
    (r'\bToshiba\s+(?:USB|drive|hard drive)\b', "Specific drive brand ('Toshiba USB'). Use 'external 2 TB USB drive'."),

    # 4. Internal hostnames & daemon IDs
    (r'\bHIL-WS-01\b', "Internal legacy hostname ('HIL-WS-01'). Use generic 'workstation host'."),
    (r'\bWS-01\b', "Workstation hostname ('WS-01'). Use 'workstation host' or 'Windows workstation'."),
    (r'\bnode1\b', "Internal cluster node name ('node1'). Use 'pve-node1' or 'primary hypervisor node'."),
    (r'\bpbs0\b', "Internal backup server hostname ('pbs0'). Use 'pbs-storage' or 'pbs-node'."),
    (r'\bhildreth-hosting-\d+\b', "Internal tunnel daemon name. Use RFC/generic 'homelab-ingress'."),

    # 5. Client domains & non-RFC examples
    (r'\bmiraclepaving\.com\b', "Real client domain ('miraclepaving.com'). Use RFC 2606 'client.example.com'."),
    (r'\bclient-app\.com\b', "Non-RFC example domain ('client-app.com'). Use RFC 2606 'client.example.com'."),

    # 6. Internal container IDs and disk volumes
    (r'\bct/(?:300|301|105)\b', "Internal container ID in path (ct/300, 301, 105). Use RFC/doc IDs (ct/100, ct/101)."),
    (r'\bvm-105-disk-\d+\b', "Internal disk volume name ('vm-105-disk-0'). Use generic 'vm-101-disk-0'."),
    (r'\bpct\s+restore\s+(?:300|105)\b', "Internal CTID restore command. Use generic CTID 'pct restore 101'."),
]

def check_sanitization(text, filename="<input>"):
    lines = text.splitlines()
    errors = []

    for line_no, line in enumerate(lines, start=1):
        for pattern, msg in FORBIDDEN_PATTERNS:
            matches = list(re.finditer(pattern, line, re.IGNORECASE))
            for m in matches:
                start = max(0, m.start() - 25)
                end = min(len(line), m.end() + 25)
                snippet = line[start:end].strip()
                errors.append(f"Line {line_no}: {msg}\n    Found: '{m.group(0)}' in snippet: ...{snippet}...")

    # Check for unbracketed live-looking UUIDs in tunnel token or CF contexts
    tunnel_uuid_pattern = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.IGNORECASE)
    for line_no, line in enumerate(lines, start=1):
        if any(term in line.lower() for term in ['tunnel', 'token', 'credentials', 'uuid', 'cloudflared']):
            # Allow pure zeros or example UUIDs
            for m in tunnel_uuid_pattern.finditer(line):
                val = m.group(0)
                if val != '00000000-0000-0000-0000-000000000000':
                    start = max(0, m.start() - 25)
                    end = min(len(line), m.end() + 25)
                    snippet = line[start:end].strip()
                    errors.append(
                        f"Line {line_no}: Raw UUID hex string found in tunnel/token context ('{val}').\n"
                        f"    Must use explicit bracketed placeholder like '<YOUR-TUNNEL-UUID>' in snippet: ...{snippet}..."
                    )

    if errors:
        print(f"\n[SECURITY SANITIZATION FAILURE] {filename} contains {len(errors)} violation(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        print("\nFix all items above according to apps/wordpress-selfhosted/references/post-format.md#rfc-compliant-placeholders--sanitization-sop\n", file=sys.stderr)
        return False

    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/validate-sanitization.py <file.html|file.md>", file=sys.stderr)
        sys.exit(2)

    target = sys.argv[1]
    if target == "-":
        content = sys.stdin.read()
        filename = "<stdin>"
    else:
        if not os.path.exists(target):
            print(f"File not found: {target}", file=sys.stderr)
            sys.exit(2)
        with open(target, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        filename = target

    ok = check_sanitization(content, filename)
    if not ok:
        sys.exit(1)
    
    print(f"[SECURITY SANITIZATION PASSED] {filename} is 100% clean of private infrastructure, personal hardware specs, and location leaks.")
    sys.exit(0)

if __name__ == '__main__':
    main()
