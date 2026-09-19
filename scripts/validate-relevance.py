#!/usr/bin/env python3
"""
validate-relevance.py — Pre-flight Critic Agent & GEO Validator.

Automates the empirical relevance engineering gates established in
"Autonomous AI Agent Architectures in Search Systems and Relevance Engineering":

Gate 1: Title Length Gate (Strictly <= 50 characters to prevent SERP/answer card truncation, Duet benchmark)
Gate 2: Semantic Section Anchor IDs Gate (100% of H2/H3 headings have kebab-case anchor IDs for passage retrieval)
Gate 3: Empirical Statistics & Telemetry Density (Asserts >= 4 hard metrics and >= 1 structured data table, GEO-BENCH +33% lift)
Gate 4: Authoritative Quotations & Citations (Asserts >= 1 official blockquote with attribution, GEO-BENCH +40% lift)
Gate 5: Scaled Content Abuse & Fluff Filter (Blocks AI filler phrases; asserts presence of technical CLI/code blocks)
Gate 6: Zero-Leakage Privacy Gate (Enforces RFC compliance, no internal hostnames, IPs, or location leaks)

Usage:
  python3 scripts/validate-relevance.py <file.md|file.html>
  python3 scripts/validate-relevance.py <file1> <file2> ...
"""

import sys
import os
import re
import argparse
from html.parser import HTMLParser

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# --- GATE DEFINITIONS ---

MAX_TITLE_CHARS = 50
MIN_STATS_COUNT = 4
MIN_QUOTES_COUNT = 1
MIN_TABLES_COUNT = 1

# Fluff / Boilerplate patterns indicating ungrounded AI generation
AI_FLUFF_PATTERNS = [
    (r"\bIn today's (?:fast-paced|rapidly evolving|digital) (?:world|landscape|age)\b", "Generic AI opening cliché"),
    (r"\bIt is important to remember that\b", "Unnecessary throat-clearing fluff"),
    (r"\bIn conclusion,\b", "Formulaic high-school conclusion marker"),
    (r"\bLet's dive (?:right )?in\b", "Overused conversational filler"),
    (r"\bdelve(?:s|d)? into\b", "Common AI hallmark verb ('delve')"),
    (r"\btapestry of\b", "High-probability LLM hallucination artifact ('tapestry')"),
    (r"\bplays a crucial role in\b", "Generic padding phrase"),
    (r"\ba testament to\b", "Generic marketing fluff"),
    (r"\bIn this blog post,? we will (?:explore|discuss|examine)\b", "Meta-narrative padding"),
    (r"\bNeedless to say,\b", "Filler phrase"),
    (r"\bAt the end of the day,\b", "Conversational cliché"),
]

# Privacy / Zero-leakage patterns (matching validate-sanitization.py)
PRIVACY_PATTERNS = [
    (r'\bHildreth\b', "Physical location leak ('Hildreth'). Use 'primary site' or generic term."),
    (r'\bbedroom\s+(?:desktop|VM|server|rig|host|lab)\b', "Personal living space reference ('bedroom ...'). Use 'workstation VM'."),
    (r'10\.10\.152\.\d+', "Private homelab IP subnet (10.10.152.x). Use RFC 1918 doc subnet (10.0.10.x)."),
    (r'172\.17\.48\.\d+', "Private hypervisor IP subnet (172.17.48.x). Use RFC 1918 doc subnet (172.16.10.x)."),
    (r'172\.16\.15\.\d+', "Private management subnet (172.16.15.x). Use RFC 1918 doc subnet (10.0.1.x or 10.0.10.x)."),
    (r'192\.168\.1\.24\b', "Specific private host IP (192.168.1.24). Use generic host IP (192.168.1.100)."),
    (r'\bRyzen\s+7\s+5800X\b', "Specific personal CPU model ('Ryzen 7 5800X'). Use '8-core desktop processor'."),
    (r'\b(?:GeForce\s+)?RTX\s+3080\b', "Specific personal GPU model ('RTX 3080'). Use 'workstation GPU'."),
    (r'\b(?:Dell\s+)?(?:PowerEdge\s+)?R630\b', "Specific chassis model ('Dell PowerEdge R630'). Use '1U enterprise rack server'."),
    (r'\bToshiba\s+(?:USB|drive|hard drive)\b', "Specific drive brand ('Toshiba USB'). Use 'external 2 TB USB drive'."),
    (r'\bHIL-WS-01\b', "Internal legacy hostname ('HIL-WS-01'). Use generic 'workstation host'."),
    (r'\bWS-01\b', "Workstation hostname ('WS-01'). Use 'workstation host'."),
    (r'\bnode1\b', "Internal cluster node name ('node1'). Use 'primary hypervisor node'."),
    (r'\bpbs0\b', "Internal backup server hostname ('pbs0'). Use 'pbs-storage' or 'pbs-node'."),
    (r'\bmiraclepaving\.com\b', "Real client domain ('miraclepaving.com'). Use RFC 2606 'client.example.com'."),
    (r'\bct/(?:300|301|105)\b', "Internal container ID in path (ct/300, 301, 105). Use RFC/doc IDs (ct/100, ct/101)."),
]

# Telemetry & numerical metric pattern (GB, MB/s, ms, %, mins, hours, etc.)
TELEMETRY_PATTERN = re.compile(
    r'\b(?:\d+(?:\.\d+)?\s*(?:GiB|GB|MiB|MB|KB|TB|MB/s|GB/s|ms|µs|ns|%|cores?|mins?|hours?|nodes?|packets?|ports?)|(?:\d+x\b)|(?:[A-Z0-9_-]+\s*:\s*\d+))\b',
    re.IGNORECASE
)


class ContentCritic:
    def __init__(self, raw_text, filepath="<input>", explicit_title=None):
        self.raw_text = raw_text
        self.filepath = filepath
        self.explicit_title = explicit_title
        self.is_html = self._detect_html()
        self.errors = []
        self.warnings = []
        self.metrics = {}

    def _detect_html(self):
        sample = self.raw_text[:1000]
        return bool(re.search(r'<(?:h[1-6]|p|div|table|blockquote)\b', sample, re.IGNORECASE))

    def evaluate(self):
        title = self.explicit_title or self._extract_title()
        headings = self._extract_headings()
        quotes = self._extract_quotes()
        tables = self._extract_tables()
        code_blocks = self._extract_code_blocks()
        telemetry_matches = list(set(TELEMETRY_PATTERN.findall(self.raw_text)))

        self.metrics["title"] = title
        self.metrics["title_length"] = len(title) if title else 0
        self.metrics["headings_total"] = len(headings)
        self.metrics["headings_with_id"] = sum(1 for h in headings if h["id"])
        self.metrics["quotes_count"] = len(quotes)
        self.metrics["tables_count"] = len(tables)
        self.metrics["code_blocks_count"] = len(code_blocks)
        self.metrics["telemetry_count"] = len(telemetry_matches)

        # Gate 1: Title Length (Strictly <= 50 chars)
        if not title:
            self.errors.append("Gate 1 (Title): No title detected (missing H1, title tag, or --title argument).")
        elif len(title) > MAX_TITLE_CHARS:
            self.errors.append(
                f"Gate 1 (Title): Title length ({len(title)} chars) exceeds {MAX_TITLE_CHARS} chars! "
                f"Truncates on mobile/desktop SERPs. Current: '{title}'"
            )

        # Gate 2: Heading Anchor IDs (100% of H2/H3 must have IDs)
        missing_ids = [h for h in headings if not h["id"]]
        if missing_ids:
            missing_titles = [f"H{h['level']}: {h['text']}" for h in missing_ids[:5]]
            detail = f"{len(missing_ids)}/{len(headings)} headings lack semantic anchor IDs (e.g. {', '.join(missing_titles)})."
            if self.is_html:
                self.errors.append(f"Gate 2 (Semantic IDs): {detail}")
            else:
                self.warnings.append(f"Gate 2 (Semantic IDs): Markdown lacks explicit HTML IDs. Ensure renderer generates deterministic IDs.")

        # Gate 3: Empirical Statistics & Tables
        if len(telemetry_matches) < MIN_STATS_COUNT:
            self.errors.append(
                f"Gate 3 (Empirical Data): Only {len(telemetry_matches)} numeric/telemetry metrics found (minimum {MIN_STATS_COUNT} required). "
                f"Inject hard numbers (benchmarks, latencies, sizes, throughput)."
            )
        if len(tables) < MIN_TABLES_COUNT:
            self.errors.append(
                f"Gate 3 (Structured Data): Zero data tables found (minimum {MIN_TABLES_COUNT} required). "
                f"Embed an empirical comparison or telemetry benchmark table (+33% GEO lift)."
            )

        # Gate 4: Authoritative Quotations & Citations
        if len(quotes) < MIN_QUOTES_COUNT:
            self.errors.append(
                f"Gate 4 (Authoritative Citations): Zero blockquotes found (minimum {MIN_QUOTES_COUNT} required). "
                f"Add direct citations from official docs (Proxmox, Cloudflare, Linux Kernel) for +40% GEO citation lift."
            )

        # Gate 5: Fluff Filter & Code Blocks
        fluff_hits = []
        for pat, desc in AI_FLUFF_PATTERNS:
            found = re.findall(pat, self.raw_text, re.IGNORECASE)
            if found:
                fluff_hits.append(f"'{found[0]}' ({desc})")
        if fluff_hits:
            self.errors.append(f"Gate 5 (Content Quality): Detected AI filler phrases: {'; '.join(fluff_hits)}.")
        if len(code_blocks) == 0:
            self.warnings.append("Gate 5 (Content Depth): No technical CLI/code blocks found. First-hand engineering evidence required.")

        # Gate 6: Zero-Leakage Privacy Gate
        privacy_leaks = []
        for pat, desc in PRIVACY_PATTERNS:
            found = re.findall(pat, self.raw_text, re.IGNORECASE)
            if found:
                privacy_leaks.append(f"{desc} (matched: {set(found)})")
        if privacy_leaks:
            self.errors.append(f"Gate 6 (Zero-Leakage Privacy): CRITICAL PRIVACY LEAK detected: {'; '.join(privacy_leaks)}.")

        return len(self.errors) == 0

    def _extract_title(self):
        if self.is_html:
            m_html = re.search(r'<h1[^>]*>(.*?)</h1>', self.raw_text, re.IGNORECASE | re.DOTALL)
            if m_html:
                return re.sub(r'<[^>]+>', '', m_html.group(1)).strip()
            m_title = re.search(r'<title[^>]*>(.*?)</title>', self.raw_text, re.IGNORECASE | re.DOTALL)
            if m_title:
                return re.sub(r'<[^>]+>', '', m_title.group(1)).strip()
            return ""

        # For markdown: remove code blocks before finding H1
        clean_md = re.sub(r'```.*?```', '', self.raw_text, flags=re.DOTALL)
        m_md = re.search(r'^#\s+(.+)$', clean_md, re.MULTILINE)
        if m_md:
            return m_md.group(1).strip()
        return ""

    def _extract_headings(self):
        headings = []
        if self.is_html:
            # Matches <h2 ...>text</h2> and <h3 ...>text</h3>
            pattern = re.compile(r'<(h[23])([^>]*)>(.*?)</\1>', re.IGNORECASE | re.DOTALL)
            for m in pattern.finditer(self.raw_text):
                level = int(m.group(1)[1])
                attrs = m.group(2)
                text = re.sub(r'<[^>]+>', '', m.group(3)).strip()
                id_m = re.search(r'\bid=["\']([^"\']+)["\']', attrs, re.IGNORECASE)
                anchor_id = id_m.group(1) if id_m else None
                headings.append({"level": level, "text": text, "id": anchor_id})
        else:
            # Matches ## Heading {#id} or ## Heading
            pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)
            for m in pattern.finditer(self.raw_text):
                level = len(m.group(1))
                full_text = m.group(2).strip()
                # check for {#id}
                id_m = re.search(r'\{#([a-zA-Z0-9_-]+)\}', full_text)
                if id_m:
                    anchor_id = id_m.group(1)
                    text = re.sub(r'\{#([a-zA-Z0-9_-]+)\}', '', full_text).strip()
                else:
                    anchor_id = None
                    text = full_text
                headings.append({"level": level, "text": text, "id": anchor_id})
        return headings

    def _extract_quotes(self):
        quotes = []
        if self.is_html:
            pattern = re.compile(r'<blockquote\b[^>]*>(.*?)</blockquote>', re.IGNORECASE | re.DOTALL)
            quotes = pattern.findall(self.raw_text)
        else:
            pattern = re.compile(r'^\s*>\s*(.+)$', re.MULTILINE)
            quotes = pattern.findall(self.raw_text)
        return quotes

    def _extract_tables(self):
        tables = []
        if self.is_html:
            tables = re.findall(r'<table\b[^>]*>', self.raw_text, re.IGNORECASE)
        else:
            # Markdown table header separator |---|---|
            tables = re.findall(r'\|(?:\s*:?---+:?\s*\|)+', self.raw_text)
        return tables

    def _extract_code_blocks(self):
        code_blocks = []
        if self.is_html:
            code_blocks = re.findall(r'<pre\b[^>]*>', self.raw_text, re.IGNORECASE)
        else:
            code_blocks = re.findall(r'```[a-zA-Z0-9_-]*\n', self.raw_text)
        return code_blocks

    def print_report(self):
        filename = os.path.basename(self.filepath)
        print("=" * 72)
        print(f" PRE-FLIGHT CRITIC VALIDATION REPORT: {filename}")
        print("=" * 72)
        print(f"• Document Type:       {'HTML (Gutenberg)' if self.is_html else 'Markdown'}")
        print(f"• Title:               '{self.metrics.get('title')}'")
        title_len = self.metrics.get('title_length', 0)
        title_status = "PASS (<= 50 chars)" if 0 < title_len <= MAX_TITLE_CHARS else f"FAIL ({title_len} chars > 50)"
        print(f"• Title Length:        {title_len} chars [{title_status}]")
        print(f"• Headings (H2/H3):    {self.metrics.get('headings_total')} total ({self.metrics.get('headings_with_id')} with semantic IDs)")
        print(f"• Citations / Quotes:  {self.metrics.get('quotes_count')} blockquotes")
        print(f"• Structured Tables:   {self.metrics.get('tables_count')} tables")
        print(f"• Code / CLI Blocks:   {self.metrics.get('code_blocks_count')} blocks")
        print(f"• Telemetry Metrics:   {self.metrics.get('telemetry_count')} distinct quantitative data points")
        print("-" * 72)

        if self.errors:
            print(f"[FAIL] REJECTED BY CRITIC GATE ({len(self.errors)} Blocking Errors):")
            for idx, err in enumerate(self.errors, 1):
                print(f"  [{idx}] {err}")
        else:
            print("[PASS] ALL CRITICAL RELEVANCE & GEO GATES PASSED")

        if self.warnings:
            print(f"\n[WARN] WARNINGS ({len(self.warnings)} Non-blocking suggestions):")
            for idx, warn in enumerate(self.warnings, 1):
                print(f"  [{idx}] {warn}")

        print("=" * 72 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Pre-flight Critic Agent for SEO Relevance & GEO compliance.")
    parser.add_argument("files", nargs="+", help="Path to markdown or HTML files to evaluate.")
    parser.add_argument("--title", help="Explicit title string if validating raw HTML snippet without H1/title tag.")
    args = parser.parse_args()

    overall_success = True
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            overall_success = False
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        critic = ContentCritic(content, filepath=file_path, explicit_title=args.title)
        passed = critic.evaluate()
        critic.print_report()
        if not passed:
            overall_success = False

    sys.exit(0 if overall_success else 1)


if __name__ == "__main__":
    main()
