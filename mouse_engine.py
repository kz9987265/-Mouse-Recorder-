"""
第二滑鼠 - 核心引擎模組（無 UI）
負責：熱鍵鍵名對應、事件錄製、事件播放、排程觸發、存檔/讀檔、設定檔讀寫
可被 mouse_gui.py 匯入，也可單獨被其他程式重複使用。
"""

import time
import json
import os
import sys
import threading
import subprocess
from datetime import datetime, timedelta

def _ensure_dependencies():
    """
    確保 pynput / pyautogui 可用。
    直接 import 失敗時才嘗試自動安裝；安裝失敗則印出清楚的中文說明並結束，
    避免使用者看到一堆看不懂的 traceback 或程式閃退。
    """
    missing = []
    for pkg in ("pynput", "pyautogui"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if not missing:
        return

    print(f"偵測到缺少必要套件：{', '.join(missing)}，嘗試自動安裝中，請稍候…")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", *missing])
    except Exception as e:
        print("\n======= 自動安裝套件失敗 =======")
        print(f"錯誤訊息：{e}")
        print("\n請手動開啟命令提示字元 / 終端機，輸入以下指令安裝後再執行本程式：")
        print(f"    {sys.executable} -m pip install {' '.join(missing)}")
        print("=================================")
        if sys.stdin and sys.stdin.isatty():
            input("\n按 Enter 關閉...")
        sys.exit(1)

    # 安裝後重新嘗試 import，仍失敗就給出明確錯誤而不是讓後面的 import 語句直接炸掉
    for pkg in missing:
        try:
            __import__(pkg)
        except ImportError as e:
            print(f"\n安裝後仍無法載入 {pkg}：{e}")
            print(f"請手動執行：{sys.executable} -m pip install {pkg}")
            if sys.stdin and sys.stdin.isatty():
                input("\n按 Enter 關閉...")
            sys.exit(1)


_ensure_dependencies()

from pynput import mouse, keyboard
from pynput.mouse import Button, Controller as MouseController
import pyautogui

pyautogui.FAILSAFE = False

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR    = os.path.join(BASE_DIR, "recordings")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# 支援設為熱鍵的按鍵（功能鍵 + 常用鍵）
KEY_OPTIONS = [f"F{i}" for i in range(1, 13)] + \
              ["Home", "End", "Insert", "Delete", "PageUp", "PageDown",
               "Pause", "ScrollLock"]

# 動作編輯器可選的動作類型 / 滑鼠按鈕
EVENT_TYPES = ["move", "click", "scroll", "key"]
MOUSE_BUTTONS = ["left", "right", "middle"]


def key_to_pynput(name):
    """把熱鍵字串名稱（例如 'F9'）轉成 pynput 的 Key 物件"""
    mapping = {
        **{f"F{i}": getattr(keyboard.Key, f"f{i}") for i in range(1, 13)},
        "Home": keyboard.Key.home, "End": keyboard.Key.end,
        "Insert": keyboard.Key.insert, "Delete": keyboard.Key.delete,
        "PageUp": keyboard.Key.page_up, "PageDown": keyboard.Key.page_down,
        "Pause": keyboard.Key.pause, "ScrollLock": keyboard.Key.scroll_lock,
    }
    return mapping.get(name)


def event_key_to_pynput(key_str):
    """把存檔中的按鍵字串（'a' 或 'Key.ctrl_l'）還原成 pynput 可用的物件"""
    if not key_str:
        return None
    if key_str.startswith("Key."):
        attr = key_str[4:]
        return getattr(keyboard.Key, attr, None)
    if len(key_str) == 1:
        return key_str
    return None


def format_event_label(ev):
    """把單一事件轉成人類看得懂的一行文字（給列表框顯示用）"""
    kind  = ev.get("type")
    delay = ev.get("delay", 0)
    if kind == "key":
        key = ev.get("key", "?")
        act = "按下" if ev.get("pressed") else "放開"
        return f"  鍵盤{act}  {key:<20}   +{delay:.3f}s"
    x, y = ev.get("x", 0), ev.get("y", 0)
    if kind == "move":
        return f"  移動     ({x:5d}, {y:5d})   +{delay:.3f}s"
    if kind == "click":
        btn = ev.get("btn", "")
        btn_name = "左鍵" if "left" in btn else "右鍵" if "right" in btn else "中鍵"
        act = "按下" if ev.get("pressed") else "放開"
        return f"  {btn_name}{act}  ({x:5d}, {y:5d})   +{delay:.3f}s"
    if kind == "scroll":
        return f"  滾輪     ({x:5d}, {y:5d}) dy={ev.get('dy', 0):+d}   +{delay:.3f}s"
    return f"  {kind}   +{delay:.3f}s"


class MacroRecorder:
    """負責錄製滑鼠/鍵盤事件，透過 callback 即時回報事件給上層"""

    def __init__(self, on_event=None):
        self.events = []
        self.recording = False
        self.paused = False
        self._last_time = 0.0
        self.on_event = on_event          # callback(event_dict) — 每次新事件時呼叫

        self.record_clicks = True
        self.record_moves = True
        self.record_scroll = True
        self.record_keyboard = True
        self.ignored_keys = set()         # 熱鍵字串集合，錄製時忽略這些按鍵

        self._mouse_listener = None
        self._kb_listener = None

    def start(self):
        self.events = []
        self.recording = True
        self.paused = False
        self._last_time = time.time()

        def on_move(x, y):
            if self.paused or not self.record_moves:
                return
            self._add_event("move", x, y)

        def on_click(x, y, button, pressed):
            if self.paused or not self.record_clicks:
                return
            self._add_event("click", x, y, extra={"btn": str(button), "pressed": pressed})

        def on_scroll(x, y, dx, dy):
            if self.paused or not self.record_scroll:
                return
            self._add_event("scroll", x, y, extra={"dx": dx, "dy": dy})

        def on_key_press(key):
            if self.paused or not self.record_keyboard or self._is_ignored(key):
                return
            self._add_key_event(key, pressed=True)

        def on_key_release(key):
            if self.paused or not self.record_keyboard or self._is_ignored(key):
                return
            self._add_key_event(key, pressed=False)

        self._mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
        self._mouse_listener.start()
        self._kb_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
        self._kb_listener.start()

    def _is_ignored(self, key):
        return any(key == key_to_pynput(hk) for hk in self.ignored_keys)

    def toggle_pause(self):
        if self.recording:
            self.paused = not self.paused
            if not self.paused:
                self._last_time = time.time()
        return self.paused

    def stop(self):
        self.recording = False
        self.paused = False
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None
        return self.events

    def _add_event(self, kind, x, y, extra=None):
        now = time.time()
        delay = now - self._last_time
        self._last_time = now
        ev = {"type": kind, "x": x, "y": y, "delay": round(delay, 4)}
        if extra:
            ev.update(extra)
        self.events.append(ev)
        if self.on_event:
            self.on_event(ev)

    def _add_key_event(self, key, pressed):
        now = time.time()
        delay = now - self._last_time
        self._last_time = now
        try:
            key_str = key.char
        except AttributeError:
            key_str = str(key)
        ev = {"type": "key", "key": key_str, "pressed": pressed,
              "delay": round(delay, 4), "x": 0, "y": 0}
        self.events.append(ev)
        if self.on_event:
            self.on_event(ev)


class MacroPlayer:
    """負責在背景執行緒播放事件序列：可設定速度、重複次數、每輪間隔"""

    def __init__(self, on_wait=None, on_finished=None):
        self.playing = False
        self._thread = None
        self.on_wait = on_wait          # callback(round_index, total) — 開始等待間隔時呼叫
        self.on_finished = on_finished  # callback() — 全部播放完畢時呼叫

    def play(self, events, total_loops, speed, interval):
        if not events or self.playing:
            return False
        self.playing = True
        self._thread = threading.Thread(
            target=self._loop, args=(list(events), total_loops, speed, interval), daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self.playing = False
        self._release_modifiers()

    @staticmethod
    def _release_modifiers():
        """強制放開所有修飾鍵，避免中途停止造成鍵盤卡住"""
        try:
            kc = keyboard.Controller()
            for k in [keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                      keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
                      keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
                      keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r,
                      keyboard.Key.caps_lock]:
                try:
                    kc.release(k)
                except Exception:
                    pass
        except Exception:
            pass

    def _loop(self, events, total, speed, interval):
        mc = MouseController()
        kc = keyboard.Controller()

        def play_key(ev):
            key = event_key_to_pynput(ev.get("key", ""))
            if key is None:
                return
            if ev.get("pressed"):
                kc.press(key)
            else:
                kc.release(key)

        i = 0
        while self.playing:
            for ev in events:
                if not self.playing:
                    break
                delay = ev.get("delay", 0) / speed
                if delay > 0:
                    time.sleep(delay)
                kind = ev.get("type")
                if kind == "key":
                    play_key(ev)
                else:
                    x, y = ev.get("x", 0), ev.get("y", 0)
                    if kind == "move":
                        mc.position = (x, y)
                    elif kind == "click":
                        mc.position = (x, y)
                        btn_str = ev.get("btn", "")
                        btn = Button.left if "left" in btn_str else \
                              Button.right if "right" in btn_str else Button.middle
                        mc.press(btn) if ev.get("pressed") else mc.release(btn)
                    elif kind == "scroll":
                        mc.position = (x, y)
                        mc.scroll(ev.get("dx", 0), ev.get("dy", 0))

            i += 1
            if total > 0 and i >= total:
                break
            if self.playing and interval > 0:
                if self.on_wait:
                    self.on_wait(i, total)
                waited = 0.0
                while self.playing and waited < interval:
                    time.sleep(0.05)
                    waited += 0.05

        self.playing = False
        if self.on_finished:
            self.on_finished()


class Scheduler:
    """在指定的「時:分」到達時觸發一次回呼（可用來執行動作或啟動外部程式）"""

    def __init__(self, on_tick=None, on_trigger=None, on_cancel=None):
        self.active = False
        self._thread = None
        self.target_time = None       # datetime
        self.on_tick = on_tick        # callback(remaining_seconds) — 每 0.5 秒回報一次
        self.on_trigger = on_trigger  # callback() — 時間到時呼叫
        self.on_cancel = on_cancel    # callback() — 被取消時呼叫

    def start(self, hour, minute):
        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)   # 今天此時間已過，排到明天同一時間
        self.target_time = target
        self.active = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return target

    def cancel(self):
        was_active = self.active
        self.active = False
        if was_active and self.on_cancel:
            self.on_cancel()

    def _run(self):
        while self.active:
            remaining = (self.target_time - datetime.now()).total_seconds()
            if remaining <= 0:
                self.active = False
                if self.on_trigger:
                    self.on_trigger()
                return
            if self.on_tick:
                self.on_tick(remaining)
            time.sleep(0.5)


# ── 存檔 / 讀檔 ──

def save_events(events, path=None):
    os.makedirs(SAVE_DIR, exist_ok=True)
    if path is None:
        filename = datetime.now().strftime("rec_%Y%m%d_%H%M%S.json")
        path = os.path.join(SAVE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    return path


def load_events(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_saves():
    os.makedirs(SAVE_DIR, exist_ok=True)
    return sorted([f for f in os.listdir(SAVE_DIR) if f.endswith(".json")], reverse=True)


def delete_save(filename):
    os.remove(os.path.join(SAVE_DIR, filename))


def rename_save(old_filename, new_name):
    """把存檔重新命名成 new_name（可不含副檔名，會自動補上 .json）"""
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("名稱不可為空")
    for ch in '<>:"/\\|?*':
        new_name = new_name.replace(ch, "")
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("名稱不可包含無效字元")
    if not new_name.lower().endswith(".json"):
        new_name += ".json"

    old_path = os.path.join(SAVE_DIR, old_filename)
    new_path = os.path.join(SAVE_DIR, new_name)
    if os.path.abspath(new_path) != os.path.abspath(old_path) and os.path.exists(new_path):
        raise FileExistsError(f"已經有同名的存檔：{new_name}")
    os.rename(old_path, new_path)
    return new_name


# ── 設定檔 ──

DEFAULT_CONFIG = {
    "loop_count": 1, "loop_infinite": False, "play_speed": 1.0, "interval_sec": 0.0,
    "record_clicks": True, "record_moves": True, "record_scroll": True, "record_keyboard": True,
    "always_on_top": False,
    "hotkey_rec": "F9", "hotkey_pause": "F8", "hotkey_play": "F10", "hotkey_stop": "F12",
    "schedule_hour": "09", "schedule_minute": "00",
}


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass  # 設定損壞就用預設值
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
