
# PROTON = [365, 1047]
# CONN = [1061, 182]
# MIN = [1779, 22]

import time
import pyautogui

CLICKS = [[365, 1047], [1061, 182], [1061, 182], [1779, 22]]
WAITS = [1.0, 1.0, 10.0]

def reset_vpn():
    for i, (x, y) in enumerate(CLICKS):
        pyautogui.click(x, y)
        if i < len(WAITS):
            time.sleep(WAITS[i])
            