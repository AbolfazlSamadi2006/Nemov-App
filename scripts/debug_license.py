import os
import sqlite3
from pathlib import Path

paths = [
    Path('data/nemov.db').resolve(),
    Path('data/yalda.db').resolve(),
    Path(os.environ.get('APPDATA', '')) / 'Nemov' / 'data' / 'nemov.db',
    Path(os.environ.get('APPDATA', '')) / 'Nemov' / 'data' / 'yalda.db',
    Path(os.environ.get('APPDATA', '')) / 'YaldaGym' / 'data' / 'yalda.db',
    Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Nemov' / 'data' / 'nemov.db',
    Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'YaldaGym' / 'data' / 'yalda.db'
]

# Deduplicate paths preserving priority order
seen_paths = set()
unique_paths = []
for p in paths:
    if p not in seen_paths:
        seen_paths.add(p)
        unique_paths.append(p)
paths = unique_paths

for p in paths:
    print('--- Path:', p)
    if p.exists():
        print('  Exists: True, mtime:', p.stat().st_mtime)
        try:
            conn = sqlite3.connect(p)
            c = conn.cursor()
            c.execute("SELECT key, value FROM system_settings")
            for k, v in c.fetchall():
                if 'license' in k or 'hwid' in k:
                    print(f'    {k} = {v}')
            conn.close()
        except Exception as e:
            print('  Error reading DB:', e)
    else:
        print('  Exists: False')
