import os
paths = [
    "media/imagens/rkslogo.png",
    "media/imagens",
    "media"
]
for p in paths:
    print(f"Path '{p}' exists:", os.path.exists(p))
