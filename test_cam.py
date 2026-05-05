import cv2
print("Testing cameras...")
for backend in [cv2.CAP_V4L2, cv2.CAP_DSHOW, cv2.CAP_ANY]:
    print(f"Backend {backend}")
    for idx in [0, 1, 2]:
        print(f"Idx {idx}")
        cap = cv2.VideoCapture(idx, backend)
        print(f"Opened? {cap.isOpened()}")
        if cap.isOpened(): cap.release()
print("Done")
