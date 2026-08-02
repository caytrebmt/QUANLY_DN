#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Translation Management Utility for ERPACC

Usage:
    python manage_translations.py extract    # Extract strings from code to .pot
    python manage_translations.py update      # Update .po files from .pot
    python manage_translations.py compile     # Compile .po to .mo
    python manage_translations.py missing     # Show strings missing translations
    python manage_translations.py stats       # Show translation statistics
"""
import os
import sys
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
TRANSLATIONS_DIR = PROJECT_ROOT / 'translations'
POT_FILE = TRANSLATIONS_DIR / 'messages.pot'
LANGUAGES = ['vi', 'en']

SCAN_DIRS = [
    PROJECT_ROOT / 'app',
    PROJECT_ROOT / 'templates',
    PROJECT_ROOT / 'domains',
]


def _ensure_translations_dir():
    TRANSLATIONS_DIR.mkdir(parents=True, exist_ok=True)
    for lang in LANGUAGES:
        (TRANSLATIONS_DIR / lang / 'LC_MESSAGES').mkdir(parents=True, exist_ok=True)


def _extract_from_py(content):
    results = []
    for m in re.finditer(r'''_(?:\s)*\((["'])(.*?)\1''', content, re.DOTALL):
        text = m.group(2)
        if text:
            results.append(text)
    for m in re.finditer(r'''gettext(?:_lazy)?(?:\s)*\((["'])(.*?)\1''', content, re.DOTALL):
        text = m.group(2)
        if text:
            results.append(text)
    for m in re.finditer(r'''ngettext(?:_lazy)?(?:\s)*\((["'])(.*?)\1,\s*(["'])(.*?)\3''', content, re.DOTALL):
        singular = m.group(2)
        plural = m.group(4)
        if singular:
            results.append(singular)
        if plural:
            results.append(plural)
    return results


def _extract_from_html(content):
    results = []
    for m in re.finditer(r"\{\{[\s_]*[a-zA-Z_]+[\s_]*\([\s_]*['\"](?:#[^'\"]*['\"][\s,]*)*([^'\"]*?)['\"][\s)]*\}", content):
        results.append(m.group(1))
    for m in re.finditer(r"\{%[\s]*trans[\s]*%\}(.*?)\{%[\s]*endtrans[\s]*%\}", content, re.DOTALL | re.IGNORECASE):
        text = m.group(1).strip()
        if text:
            results.append(text)
    return results


def _extract_from_js(content):
    results = []
    for m in re.finditer(r"gettext(?:_lazy)?(?:\s)*(?:\.)*(?:[^(\s]*)(?:\s)*\((?:\s)*['\"]([^'\"]*?)['\"]", content):
        results.append(m.group(1))
    return results


def extract_strings():
    print("[**] Extracting translatable strings...")
    _ensure_translations_dir()

    catalog = {}
    files_scanned = 0
    strings_found = 0

    for base_dir in SCAN_DIRS:
        if not base_dir.exists():
            continue
        for path in sorted(base_dir.rglob('*')):
            if not path.is_file():
                continue
            if path.suffix not in {'.py', '.html', '.js'}:
                continue
            name = path.name
            if 'venv' in str(path) or '__pycache__' in str(path) or name.startswith('.'):
                continue
            if name.startswith('react-') and path.suffix == '.js':
                continue
            try:
                content = path.read_text(encoding='utf-8', errors='ignore')
                if not content.strip():
                    continue
                rel = path.relative_to(PROJECT_ROOT)
                key = str(rel)
                texts = []
                if path.suffix == '.py':
                    texts = _extract_from_py(content)
                elif path.suffix == '.html':
                    texts = _extract_from_html(content)
                elif path.suffix == '.js':
                    texts = _extract_from_js(content)
                if texts:
                    catalog[key] = texts
                    strings_found += len(set(texts))
                files_scanned += 1
            except Exception:
                pass

    unique = sorted({text for texts in catalog.values() for text in texts})
    _write_pot(unique)
    print(f"  [OK] Scanned {files_scanned} files")
    print(f"  [OK] Extracted {len(unique)} unique strings -> {POT_FILE}")
    return True


def _write_pot(texts):
    now = datetime.now().strftime('%Y-%m-%d %H:%M+0000')
    lines = [
        '# Translations for ERPACC',
        '# Copyright (C) 2026 ORGANIZATION',
        '# This file is distributed under the same license as the ERPACC project.',
        '#',
        'msgid ""',
        'msgstr ""',
        '"Project-Id-Version: ERPACC\\n"',
        '"Report-Msgid-Bugs-To: EMAIL@ADDRESS\\n"',
        f'"POT-Creation-Date: {now}\\n"',
        f'"PO-Revision-Date: {now}\\n"',
        '"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"',
        '"Language: vi\\n"',
        '"Language-Team: vi <LL@li.org>\\n"',
        '"Plural-Forms: nplurals=1; plural=0;\\n"',
        '"MIME-Version: 1.0\\n"',
        '"Content-Type: text/plain; charset=utf-8\\n"',
        '"Content-Transfer-Encoding: 8bit\\n"',
        '"Generated-By: manage_translations.py\\n"',
        '',
    ]
    for text in texts:
        lines.append(f'msgid "{text}"')
        lines.append('msgstr ""')
        lines.append('')
    POT_FILE.write_text('\n'.join(lines), encoding='utf-8')


def update_po_files():
    print("[**] Updating .po files...")
    if not POT_FILE.exists():
        print("  [ERROR] messages.pot not found. Run 'extract' first.")
        return False

    _ensure_translations_dir()

    try:
        from babel.messages import pofile
        from babel.messages.catalog import Catalog, Message
        with open(POT_FILE, 'rb') as f:
            pot_catalog = pofile.read_po(f)
    except Exception as e:
        print(f"  [ERROR] Failed to read POT: {e}")
        return False

    for lang in LANGUAGES:
        po_path = TRANSLATIONS_DIR / lang / 'LC_MESSAGES' / 'messages.po'
        po_catalog = Catalog(locale=lang)
        if po_path.exists():
            try:
                with open(po_path, 'rb') as f:
                    existing = pofile.read_po(f)
                for m in existing:
                    if m.id and m.string and m.string.strip():
                        po_catalog[m.id] = Message(m.id, m.string)
            except Exception as e:
                print(f"  [WARN] Could not preserve existing {lang} translations: {e}")
        for m in pot_catalog:
            if m.id and m.id not in po_catalog:
                po_catalog.add(m.id)
        with open(po_path, 'wb') as f:
            pofile.write_po(f, po_catalog)
        print(f"  [OK] Updated {po_path}")

    return True


def compile_mo_files():
    print("[**] Compiling .mo files...")
    _ensure_translations_dir()
    try:
        from babel.messages import pofile, mofile
    except ImportError:
        print("  [ERROR] Babel not installed. pip install Babel")
        return False

    for lang in LANGUAGES:
        po_path = TRANSLATIONS_DIR / lang / 'LC_MESSAGES' / 'messages.po'
        mo_path = TRANSLATIONS_DIR / lang / 'LC_MESSAGES' / 'messages.mo'
        if not po_path.exists():
            print(f"  [SKIP] {po_path} not found")
            continue
        try:
            with open(po_path, 'rb') as f:
                catalog = pofile.read_po(f)
            with open(mo_path, 'wb') as f:
                mofile.write_mo(f, catalog)
            print(f"  [OK] Compiled {po_path}")
        except Exception as e:
            print(f"  [ERROR] {e}")
    return True


def show_missing():
    print("[**] Checking for missing translations...")
    _ensure_translations_dir()
    try:
        from babel.messages import pofile
    except ImportError:
        print("  [ERROR] Babel not installed. pip install Babel")
        return False

    for lang in LANGUAGES:
        po_path = TRANSLATIONS_DIR / lang / 'LC_MESSAGES' / 'messages.po'
        if not po_path.exists():
            print(f"  [SKIP] {po_path} not found")
            continue
        try:
            with open(po_path, 'rb') as f:
                catalog = pofile.read_po(f)
            missing = [m.id for m in catalog if m.id and not m.string.strip()]
            if missing:
                print(f"\n  Language: {lang} -- {len(missing)} missing")
                for mid in missing[:15]:
                    print(f"    - {mid}")
                if len(missing) > 15:
                    print(f"    ... and {len(missing) - 15} more")
            else:
                print(f"  Language: {lang} -- All translated")
        except Exception as e:
            print(f"  [ERROR] {e}")
    return True


def show_stats():
    print("[**] Translation statistics...")
    _ensure_translations_dir()
    try:
        from babel.messages import pofile
    except ImportError:
        print("  [ERROR] Babel not installed. pip install Babel")
        return False

    for lang in LANGUAGES:
        po_path = TRANSLATIONS_DIR / lang / 'LC_MESSAGES' / 'messages.po'
        if not po_path.exists():
            print(f"  [SKIP] {po_path} not found")
            continue
        try:
            with open(po_path, 'rb') as f:
                catalog = pofile.read_po(f)
            total = sum(1 for m in catalog if m.id and not str(m.id).startswith('"""'))
            translated = sum(1 for m in catalog if m.string and m.string.strip())
            pct = (translated / total * 100) if total else 0
            print(f"\n  Language: {lang}")
            print(f"    Total strings: {total}")
            print(f"    Translated: {translated} ({pct:.1f}%)")
            print(f"    Missing: {total - translated}")
        except Exception as e:
            print(f"  [ERROR] {e}")
    return True


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()
    dispatch = {
        'extract': extract_strings,
        'update': update_po_files,
        'compile': compile_mo_files,
        'missing': show_missing,
        'stats': show_stats,
    }
    fn = dispatch.get(command)
    if not fn:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
    ok = fn()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
