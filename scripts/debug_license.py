import os
import sqlite3
from pathlib import Path

paths = [
    Path('data/yalda.db').resolve(),
    Path(os.environ.get('APPDATA', '')) / 'YaldaGym' / 'data' / 'yalda.db',
    Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'YaldaGym' / 'data' / 'yalda.db'
]

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
