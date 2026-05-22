import re

with open("monitor_aluno.py", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(
    r'transparent_pixel = "/9j/',
    r'transparent_pixel = "data:image/jpeg;base64,/9j/',
    content
)

with open("monitor_aluno.py", "w", encoding="utf-8") as f:
    f.write(content)
