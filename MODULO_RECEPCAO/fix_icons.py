import re

with open('ponte_rocksfit_flet.py', 'r') as f:
    content = f.read()

replacements = [
    (r'ft\.Icon\("wifi"', 'ft.Icon(ft.Icons.WIFI'),
    (r'ft\.Icon\("fingerprint"', 'ft.Icon(ft.Icons.FINGERPRINT'),
    (r'ft\.Icon\("close"', 'ft.Icon(ft.Icons.CLOSE'),
    (r'ft\.Icon\("camera"', 'ft.Icon(ft.Icons.CAMERA'),
    (r'ft\.Icon\("check_circle"', 'ft.Icon(ft.Icons.CHECK_CIRCLE'),
    (r'ft\.Icon\("sync"', 'ft.Icon(ft.Icons.SYNC'),
    (r'ft\.Icon\("analytics"', 'ft.Icon(ft.Icons.ANALYTICS'),
    (r'ft\.Icon\("auto_fix_high"', 'ft.Icon(ft.Icons.AUTO_FIX_HIGH'),
    (r'ft\.Icon\("save"', 'ft.Icon(ft.Icons.SAVE'),
    (r'ft\.Icon\("fitness_center"', 'ft.Icon(ft.Icons.FITNESS_CENTER'),
    (r'ft\.Icon\("check_circle" if is_ok else "error"', 'ft.Icon(ft.Icons.CHECK_CIRCLE if is_ok else ft.Icons.ERROR')
]

for old, new in replacements:
    content = re.sub(old, new, content)

with open('ponte_rocksfit_flet.py', 'w') as f:
    f.write(content)

with open('monitor_aluno.py', 'r') as f:
    monitor_content = f.read()

for old, new in replacements:
    monitor_content = re.sub(old, new, monitor_content)

with open('monitor_aluno.py', 'w') as f:
    f.write(monitor_content)

print("Icons replaced.")
