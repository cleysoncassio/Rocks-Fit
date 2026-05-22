import flet as ft

# Apply polyfill
for icon_name in ["FINGERPRINT", "LOCK_OPEN", "CLOSE", "REFRESH", "REMOVE", "CROP_SQUARE", "PEOPLE", "VIDEOCAM", "SYNC", "HISTORY", "TROUBLESHOOT", "SETTINGS", "CLOUD_DONE", "CHECK_CIRCLE", "SEARCH", "CALENDAR_MONTH", "PERSON", "LOCK", "ANALYTICS", "MEMORY", "ERROR", "REPLAY"]:
    if not hasattr(ft.icons, icon_name):
        setattr(ft.icons, icon_name, icon_name.lower())

print("FINGERPRINT:", ft.icons.FINGERPRINT)
print("LOCK_OPEN:", ft.icons.LOCK_OPEN)
print("SYNC:", ft.icons.SYNC)
print("PEOPLE:", ft.icons.PEOPLE)
print("VIDEOCAM:", ft.icons.VIDEOCAM)
