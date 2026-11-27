#!/usr/bin/env python3
"""Validate + compare the Flow.io NX4832K035 6.0.0 -> 7.0.0 HMI.

Uses Nextion2Text (MMMZZZZ/Nextion2Text, MPL-2.0) if --converter is passed.
The converter is NOT redistributed; it is fetched separately at CI runtime.
This check is not a substitute for opening/compiling in Nextion Editor.
"""

from __future__ import annotations

import argparse
import codecs
import contextlib
import difflib
import hashlib
import io
import json
from pathlib import Path
import runpy
import struct
import sys
import traceback

from build_3p5_v7_hmi import commands, components, crc, entries

DEFAULT_V6 = Path('nextion/releases/6.0.0/Flowio_Enhanced_480x320.HMI')
DEFAULT_V7 = Path('nextion/releases/7.0.0/Flowio_Enhanced_480x320_v7.0.0_CRC_FIX.HMI')
EXPECTED_CHANGED_PAGES = {'5.pa': {25}, '19.pa': {14, 21, 27, 29}}


def name_of(component):
    import re
    match = re.search(rb'([\x11-\x1e])\x00{3}objname\x00{9}', component)
    if not match:
        return '<unknown>'
    length = match.group(1)[0] & 15
    return component[match.end():match.end() + length].split(b'\x00')[0].decode('ascii', 'replace')


def fingerprint(path: Path, data: bytes) -> str:
    return f'`{path.as_posix()}`: {len(data):,} bytes; SHA-256 `{hashlib.sha256(data).hexdigest()}`'


def verify_integrity(data: bytes, display: str) -> dict:
    directory = entries(data)  # includes directory CRC, mirror, magic, and bounds checks
    crc_count = 0
    for name, (offset, length) in directory.items():
        if name.endswith('.pa'):
            page = data[offset:offset + length]
            expected = struct.unpack_from('<I', page, 0)[0]
            got = crc(page)
            if expected != got:
                raise ValueError(f'{display}: CRC mismatch in {name}: {got:08x} != {expected:08x}')
            components(page)  # also verifies component table length and bounds
            crc_count += 1
    return {'directory': directory, 'crc_count': crc_count}


def verify_changes(a: bytes, b: bytes, d: dict) -> list[str]:
    if len(a) != len(b):
        raise ValueError('HMI size changed unexpectedly: directory stability cannot be assumed')
    if a[:0x700000] != b[:0x700000]:
        raise ValueError('Reserved header / primary directory / backup directory changed')
    changes: dict[str, set[int]] = {}
    for key, (off, size) in d.items():
        p_old, p_new = a[off:off + size], b[off:off + size]
        if p_old == p_new:
            continue
        if key not in EXPECTED_CHANGED_PAGES:
            raise ValueError(f'Unexpected edited live resource: {key}')
        if len(p_old) != len(p_new):
            raise ValueError(f'Resource length changed: {key}')
        coords_old, coords_new = components(p_old), components(p_new)
        if coords_old != coords_new:
            raise ValueError(f'Component offset/length table changed: {key}')
        modified = set()
        for idx, (start, length) in enumerate(coords_old):
            if p_old[start:start + length] != p_new[start:start + length]:
                modified.add(idx)
        if not modified.issubset(EXPECTED_CHANGED_PAGES[key]):
            raise ValueError(f'Unexpected changed components in {key}: {modified}')
        if modified != EXPECTED_CHANGED_PAGES[key]:
            raise ValueError(f'Expected components not all modified in {key}: {modified}')
        if p_old[4:56] != p_new[4:56]:
            raise ValueError(f'Page metadata changed beyond CRC in {key}')
        changes[key] = modified
    if set(changes) != set(EXPECTED_CHANGED_PAGES):
        raise ValueError(f'Missing expected changed pages: {set(EXPECTED_CHANGED_PAGES)-set(changes)}')

    # Disallow bytes changed in deleted or unreferenced areas, too.
    edited_byte_positions = [idx for idx, (old, new) in enumerate(zip(a, b)) if old != new]
    allowed = [d[key] for key in EXPECTED_CHANGED_PAGES]
    for idx in edited_byte_positions:
        if not any(start <= idx < start + length for start, length in allowed):
            raise ValueError(f'Unexpected byte changed outside live pages: 0x{idx:x}')

    # Make the known date/timer change explicit, including the original event layout.
    st, sz = d['19.pa']
    orig, edited = a[st:st + sz], b[st:st + sz]
    old_parts, new_parts = components(orig), components(edited)
    x, size = new_parts[29]
    import re
    timer = edited[x:x + size]
    m = re.search(rb'\x14\x00{3}tim\x00{13}(.{4})', timer, flags=re.DOTALL)
    # The canonical builder asserts old=5000, new=60000; compare only here if found.
    if m and int.from_bytes(m.group(1), 'little') != 60000:
        raise ValueError('Unexpected timer value after patch')
    x, size = new_parts[27]
    _, lines, _ = commands(edited[x:x + size], 'codesdown')
    if 'sys0=rtc0%100' not in lines or 'covx rtc2,tDate.txt,2,0' not in lines:
        raise ValueError('DD/MM/YY formatting script is missing')
    st2, sz2 = d['5.pa']
    if b'7.0.0' not in b[st2:st2 + sz2]:
        raise ValueError('Version 7.0.0 not found in globals')

    summary = []
    for key in ('5.pa', '19.pa'):
        start, size = d[key]
        pieces = components(a[start:start + size])
        descriptions = [f'{idx} ({name_of(a[start + pieces[idx][0]:start + pieces[idx][0] + pieces[idx][1]])})'
                        for idx in sorted(changes[key])]
        summary.append(f'- **{key}** : composants {", ".join(descriptions)}')
    summary.append(f'- **{len(edited_byte_positions)} octets modifiés** au total (CRC compris)')
    return summary


def register_ansi_alias() -> None:
    # The original tool is designed for Windows, where 'ansi' maps to the
    # active Windows codepage. Linux/Python has no such codec by default.
    def lookup(name):
        if name.replace('-', '_') in ('ansi', 'mbcs'):
            return codecs.lookup('cp1252')
        return None
    codecs.register(lookup)


def convert(converter: Path, source: Path, output: Path) -> str:
    """Run unmodified upstream Nextion2Text as a script via runpy."""
    output.mkdir(parents=True, exist_ok=True)
    register_ansi_alias()
    old_argv = sys.argv
    stdout = io.StringIO()
    try:
        sys.argv = [str(converter), '-i', str(source), '-o', str(output),
                    '-p', 'visual', '-j', '-n', '-v']
        with contextlib.redirect_stdout(stdout):
            runpy.run_path(str(converter), run_name='__main__')
    finally:
        sys.argv = old_argv
    return stdout.getvalue()


def diff_exports(left: Path, right: Path, report: Path) -> list[str]:
    left_files = {p.relative_to(left).as_posix(): p for p in left.rglob('*') if p.is_file()}
    right_files = {p.relative_to(right).as_posix(): p for p in right.rglob('*') if p.is_file()}
    if set(left_files) != set(right_files):
        raise ValueError('Nextion2Text exports contain different file sets: '
                         f'{set(left_files) ^ set(right_files)}')
    modified = []
    with report.open('w', encoding='utf-8') as output:
        for name in sorted(left_files):
            old = left_files[name].read_text(encoding='utf-8')
            new = right_files[name].read_text(encoding='utf-8')
            if old == new:
                continue
            modified.append(name)
            output.writelines(difflib.unified_diff(old.splitlines(keepends=True),
                                new.splitlines(keepends=True),
                                fromfile=f'v6/{name}', tofile=f'v7/{name}'))
    return modified


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--v6', type=Path, default=DEFAULT_V6)
    parser.add_argument('--v7', type=Path, default=DEFAULT_V7)
    parser.add_argument('--converter', type=Path, help='Nextion2Text.py (externally fetched)')
    parser.add_argument('--out', type=Path, default=Path('nextion-validation'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    report = ['# Validation HMI Nextion NX4832K035_011 : 6.0.0 → 7.0.0', '']
    state = 'FAILED'
    try:
        a, b = args.v6.read_bytes(), args.v7.read_bytes()
        report += ['## Fichiers', '', fingerprint(args.v6, a), '', fingerprint(args.v7, b), '']
        x, y = verify_integrity(a, '6.0.0'), verify_integrity(b, '7.0.0')
        if x['directory'] != y['directory']:
            raise ValueError('HMI live resource directory has changed')
        report += ['## Vérifications structurelles', '',
                   f'- OK : répertoire / miroir / CRC directory / signature `ver21234`',
                   f'- OK : CRC de **{x["crc_count"]} pages** dans chaque version',
                   '- OK : fichiers de longueur identique, ressources inchangées hors pages autorisées', '']
        report += ['## Composants modifiés attendus', ''] + verify_changes(a, b, x['directory']) + ['']
        if args.converter:
            if not args.converter.is_file():
                raise FileNotFoundError(args.converter)
            original = args.out / 'v6'
            modified = args.out / 'v7'
            log6 = convert(args.converter, args.v6, original)
            log7 = convert(args.converter, args.v7, modified)
            (args.out / 'nextion2text.log').write_text('--- 6.0.0 ---\n' + log6 + '\n--- 7.0.0 ---\n' + log7, encoding='utf-8')
            changed = diff_exports(original, modified, args.out / 'nextion2text.diff')
            if not changed:
                raise ValueError('Nextion2Text detected no changes although HMI was patched')
            # Converter outputs .txt and JSON/; ensure no other pages differ.
            allowed_export_names = {'pageHome', 'globals'}
            unexpected = [name for name in changed if Path(name).stem not in allowed_export_names]
            if unexpected:
                raise ValueError(f'Unexpected edited Nextion2Text page exports: {unexpected}')
            report += ['## Nextion2Text — extraction et comparaison', '',
                       f'- OK : **{len(changed)} fichiers** d’export modifiés : `{", ".join(changed)}`',
                       '- Les scripts et attributs sont disponibles dans `v6/`, `v7/` et `nextion2text.diff`.', '']
        else:
            report += ['## Nextion2Text', '',
                       '- **Non exécuté** : passer `--converter /chemin/Nextion2Text.py` pour le contrôle complet.', '']
        state = 'PASSED' if args.converter else 'STRUCTURAL-ONLY'
    except Exception as exc:
        report += ['## Erreur', '', f'`{type(exc).__name__}: {exc}`', '']
        (args.out / 'error_traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
    finally:
        report += ['## Limites', '',
                   '- Ces contrôles vérifient la structure et les différences exportées, **pas** la compilation dans Nextion Editor.',
                   '- **Le correctif de redessin des jauges au réveil n’est pas contenu dans les modifications HMI vérifiées ici.**',
                   '', f'**Résultat : {state}**', '']
        (args.out / 'VALIDATION.md').write_text('\n'.join(report), encoding='utf-8')
        print('\n'.join(report))
    return 0 if state != 'FAILED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
