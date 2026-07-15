"""
滑鼠錄製器 - 滑鼠/鍵盤動作錄製與執行程式
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import json
import os
from datetime import datetime

try:
    from pynput import mouse, keyboard
    from pynput.mouse import Button, Controller as MouseController
    import pyautogui
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput", "pyautogui"])
    from pynput import mouse, keyboard
    from pynput.mouse import Button, Controller as MouseController
    import pyautogui

pyautogui.FAILSAFE = False

# ── 顏色 ──
BG      = "#1a1a2e"
SURFACE = "#16213e"
ACCENT  = "#0f3460"
PINK    = "#e94560"
GREEN   = "#00b894"
YELLOW  = "#fdcb6e"
BLUE    = "#4a9eff"
TEXT    = "#eaeaea"
SUBTEXT = "#a0a0b0"
BORDER  = "#0f3460"

FT  = ("Segoe UI", 18, "bold")
FB  = ("Segoe UI", 10)
FM  = ("Consolas", 9)
FBT = ("Segoe UI", 10, "bold")
FS  = ("Segoe UI", 9)

# ── 熱鍵支援清單 ──
KEY_OPTIONS = [f"F{i}" for i in range(1, 13)] + \
              ["Home", "End", "Insert", "Delete", "PageUp", "PageDown",
               "Pause", "ScrollLock"]

def _key_to_pynput(name):
    mapping = {
        **{f"F{i}": getattr(keyboard.Key, f"f{i}") for i in range(1, 13)},
        "Home": keyboard.Key.home, "End": keyboard.Key.end,
        "Insert": keyboard.Key.insert, "Delete": keyboard.Key.delete,
        "PageUp": keyboard.Key.page_up, "PageDown": keyboard.Key.page_down,
        "Pause": keyboard.Key.pause, "ScrollLock": keyboard.Key.scroll_lock,
    }
    return mapping.get(name)

SAVE_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recordings")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

# ══════════════════════════════════════════════════════════
#  多語言字串定義
# ══════════════════════════════════════════════════════════
LANGS = {
    "繁體中文": {
        "title":            "滑鼠錄製器",
        "pin":              "📌 置頂",
        "status_idle":      "待機中",
        "status_recording": "錄製中…",
        "status_paused":    "錄製已暫停",
        "status_playing":   "執行中…",
        "status_done":      "執行完畢",
        "status_saved":     "✅ 已自動存檔：",
        "status_loaded":    "✅ 已載入：",
        "status_nosave":    "錄製完成（無動作）",
        "status_waiting":   "等待間隔…",
        "btn_start_rec":    "⏺  開始錄製",
        "btn_stop_rec":     "⏹  停止錄製",
        "btn_resume_rec":   "▶  繼續錄製",
        "btn_play":         "▶  執行",
        "btn_stop_play":    "⏹  停止執行",
        "hk_hint":          "點擊按鍵可重新設定熱鍵",
        "hk_rec":           "錄製",
        "hk_pause":         "暫停錄製",
        "hk_play":          "執行",
        "hk_stop":          "停止",
        "hk_waiting":       "按任意鍵…",
        "sec_rec":          "錄製設定",
        "sec_play":         "播放設定",
        "sec_saves":        "存檔記錄",
        "sec_events":       "已錄製動作",
        "chk_clicks":       "滑鼠點擊",
        "chk_moves":        "滑鼠移動",
        "chk_scroll":       "滾輪捲動",
        "chk_keyboard":     "鍵盤輸入",
        "lbl_speed":        "播放速度",
        "lbl_loops":        "重複次數",
        "lbl_infinite":     "無限循環",
        "lbl_interval":     "每輪間隔",
        "lbl_interval2":    "秒（每次執行完後等待）",
        "btn_refresh":      "🔄 重新整理",
        "btn_load":         "📂 載入選取",
        "btn_delete":       "🗑 刪除選取",
        "saves_count":      "共 {n} 個存檔",
        "events_count":     "共 {n} 個動作",
        "btn_clear":        "清除",
        "btn_export":       "匯出",
        "btn_import":       "匯入",
        "ev_move":          "移動",
        "ev_lclick":        "左鍵",
        "ev_rclick":        "右鍵",
        "ev_mclick":        "中鍵",
        "ev_down":          "按下",
        "ev_up":            "放開",
        "ev_scroll":        "滾輪",
        "ev_key":           "鍵盤",
        "msg_no_events":    "尚未錄製任何動作！",
        "msg_no_export":    "沒有可匯出的動作！",
        "msg_select_save":  "請先點選一個存檔！",
        "msg_clear_q":      "確定要清除目前動作？（不影響存檔）",
        "msg_delete_q":     "確定刪除存檔？\n",
        "msg_dup_key":      "「{k}」已經是其他功能的熱鍵了！",
        "msg_saved_to":     "已儲存至\n",
        "dlg_save":         "另存新檔",
        "dlg_open":         "開啟錄製檔案",
        "dlg_export":       "匯出",
        "dlg_clear":        "清除",
        "dlg_delete":       "刪除",
        "dlg_dup":          "重複",
        "lang_label":       "語言",
        "pause_hint":       "按 {k} 繼續",
    },
    "English": {
        "title":            "Second Mouse",
        "pin":              "📌 Pin",
        "status_idle":      "Idle",
        "status_recording": "Recording…",
        "status_paused":    "Recording Paused",
        "status_playing":   "Playing…",
        "status_done":      "Playback Done",
        "status_saved":     "✅ Auto-saved: ",
        "status_loaded":    "✅ Loaded: ",
        "status_nosave":    "Recording done (no events)",
        "status_waiting":   "Waiting…",
        "btn_start_rec":    "⏺  Record",
        "btn_stop_rec":     "⏹  Stop Recording",
        "btn_resume_rec":   "▶  Resume Recording",
        "btn_play":         "▶  Play",
        "btn_stop_play":    "⏹  Stop",
        "hk_hint":          "Click a key to rebind",
        "hk_rec":           "Record",
        "hk_pause":         "Pause Rec",
        "hk_play":          "Play",
        "hk_stop":          "Stop",
        "hk_waiting":       "Press a key…",
        "sec_rec":          "Recording",
        "sec_play":         "Playback",
        "sec_saves":        "Saved Files",
        "sec_events":       "Recorded Events",
        "chk_clicks":       "Mouse Clicks",
        "chk_moves":        "Mouse Moves",
        "chk_scroll":       "Scroll Wheel",
        "chk_keyboard":     "Keyboard",
        "lbl_speed":        "Speed",
        "lbl_loops":        "Repeat",
        "lbl_infinite":     "Infinite",
        "lbl_interval":     "Interval",
        "lbl_interval2":    "sec (wait after each run)",
        "btn_refresh":      "🔄 Refresh",
        "btn_load":         "📂 Load",
        "btn_delete":       "🗑 Delete",
        "saves_count":      "{n} saves",
        "events_count":     "{n} events",
        "btn_clear":        "Clear",
        "btn_export":       "Export",
        "btn_import":       "Import",
        "ev_move":          "Move",
        "ev_lclick":        "L-Btn",
        "ev_rclick":        "R-Btn",
        "ev_mclick":        "M-Btn",
        "ev_down":          "Down",
        "ev_up":            "Up",
        "ev_scroll":        "Scroll",
        "ev_key":           "Key",
        "msg_no_events":    "No events recorded yet!",
        "msg_no_export":    "Nothing to export!",
        "msg_select_save":  "Please select a save file first!",
        "msg_clear_q":      "Clear all recorded events? (saves unaffected)",
        "msg_delete_q":     "Delete this save?\n",
        "msg_dup_key":      "'{k}' is already assigned to another hotkey!",
        "msg_saved_to":     "Saved to\n",
        "dlg_save":         "Save As",
        "dlg_open":         "Open Recording",
        "dlg_export":       "Export",
        "dlg_clear":        "Clear",
        "dlg_delete":       "Delete",
        "dlg_dup":          "Duplicate",
        "lang_label":       "Language",
        "pause_hint":       "Press {k} to resume",
    },
    "简体中文": {
        "title":            "第二鼠标",
        "pin":              "📌 置顶",
        "status_idle":      "待机中",
        "status_recording": "录制中…",
        "status_paused":    "录制已暂停",
        "status_playing":   "执行中…",
        "status_done":      "执行完毕",
        "status_saved":     "✅ 已自动存档：",
        "status_loaded":    "✅ 已载入：",
        "status_nosave":    "录制完成（无动作）",
        "status_waiting":   "等待间隔…",
        "btn_start_rec":    "⏺  开始录制",
        "btn_stop_rec":     "⏹  停止录制",
        "btn_resume_rec":   "▶  继续录制",
        "btn_play":         "▶  执行",
        "btn_stop_play":    "⏹  停止执行",
        "hk_hint":          "点击按键可重新设定热键",
        "hk_rec":           "录制",
        "hk_pause":         "暂停录制",
        "hk_play":          "执行",
        "hk_stop":          "停止",
        "hk_waiting":       "按任意键…",
        "sec_rec":          "录制设定",
        "sec_play":         "播放设定",
        "sec_saves":        "存档记录",
        "sec_events":       "已录制动作",
        "chk_clicks":       "鼠标点击",
        "chk_moves":        "鼠标移动",
        "chk_scroll":       "滚轮滚动",
        "chk_keyboard":     "键盘输入",
        "lbl_speed":        "播放速度",
        "lbl_loops":        "重复次数",
        "lbl_infinite":     "无限循环",
        "lbl_interval":     "每轮间隔",
        "lbl_interval2":    "秒（每次执行完后等待）",
        "btn_refresh":      "🔄 刷新",
        "btn_load":         "📂 载入选取",
        "btn_delete":       "🗑 删除选取",
        "saves_count":      "共 {n} 个存档",
        "events_count":     "共 {n} 个动作",
        "btn_clear":        "清除",
        "btn_export":       "导出",
        "btn_import":       "导入",
        "ev_move":          "移动",
        "ev_lclick":        "左键",
        "ev_rclick":        "右键",
        "ev_mclick":        "中键",
        "ev_down":          "按下",
        "ev_up":            "放开",
        "ev_scroll":        "滚轮",
        "ev_key":           "键盘",
        "msg_no_events":    "尚未录制任何动作！",
        "msg_no_export":    "没有可导出的动作！",
        "msg_select_save":  "请先点选一个存档！",
        "msg_clear_q":      "确定要清除目前动作？（不影响存档）",
        "msg_delete_q":     "确定删除存档？\n",
        "msg_dup_key":      "「{k}」已经是其他功能的热键了！",
        "msg_saved_to":     "已保存至\n",
        "dlg_save":         "另存为",
        "dlg_open":         "打开录制文件",
        "dlg_export":       "导出",
        "dlg_clear":        "清除",
        "dlg_delete":       "删除",
        "dlg_dup":          "重复",
        "lang_label":       "语言",
        "pause_hint":       "按 {k} 继续",
    },
    "日本語": {
        "title":            "セカンドマウス",
        "pin":              "📌 最前面",
        "status_idle":      "待機中",
        "status_recording": "録画中…",
        "status_paused":    "録画一時停止",
        "status_playing":   "再生中…",
        "status_done":      "再生完了",
        "status_saved":     "✅ 自動保存：",
        "status_loaded":    "✅ 読み込み済：",
        "status_nosave":    "録画完了（動作なし）",
        "status_waiting":   "待機中…",
        "btn_start_rec":    "⏺  録画開始",
        "btn_stop_rec":     "⏹  録画停止",
        "btn_resume_rec":   "▶  録画再開",
        "btn_play":         "▶  再生",
        "btn_stop_play":    "⏹  停止",
        "hk_hint":          "クリックでホットキーを変更",
        "hk_rec":           "録画",
        "hk_pause":         "一時停止",
        "hk_play":          "再生",
        "hk_stop":          "停止",
        "hk_waiting":       "キーを押して…",
        "sec_rec":          "録画設定",
        "sec_play":         "再生設定",
        "sec_saves":        "保存ファイル",
        "sec_events":       "録画済み動作",
        "chk_clicks":       "マウスクリック",
        "chk_moves":        "マウス移動",
        "chk_scroll":       "スクロール",
        "chk_keyboard":     "キーボード",
        "lbl_speed":        "再生速度",
        "lbl_loops":        "繰り返し",
        "lbl_infinite":     "無限ループ",
        "lbl_interval":     "間隔",
        "lbl_interval2":    "秒（各実行後に待機）",
        "btn_refresh":      "🔄 更新",
        "btn_load":         "📂 読み込み",
        "btn_delete":       "🗑 削除",
        "saves_count":      "{n} 件",
        "events_count":     "{n} 件の動作",
        "btn_clear":        "クリア",
        "btn_export":       "エクスポート",
        "btn_import":       "インポート",
        "ev_move":          "移動",
        "ev_lclick":        "左クリック",
        "ev_rclick":        "右クリック",
        "ev_mclick":        "中クリック",
        "ev_down":          "押下",
        "ev_up":            "解放",
        "ev_scroll":        "スクロール",
        "ev_key":           "キー",
        "msg_no_events":    "まだ動作が録画されていません！",
        "msg_no_export":    "エクスポートする動作がありません！",
        "msg_select_save":  "ファイルを選択してください！",
        "msg_clear_q":      "現在の動作をクリアしますか？（保存には影響しません）",
        "msg_delete_q":     "このファイルを削除しますか？\n",
        "msg_dup_key":      "「{k}」は既に他の機能に割り当てられています！",
        "msg_saved_to":     "保存先：\n",
        "dlg_save":         "名前を付けて保存",
        "dlg_open":         "録画ファイルを開く",
        "dlg_export":       "エクスポート",
        "dlg_clear":        "クリア",
        "dlg_delete":       "削除",
        "dlg_dup":          "重複",
        "lang_label":       "言語",
        "pause_hint":       "{k} で再開",
    },
    "한국어": {
        "title":            "세컨드 마우스",
        "pin":              "📌 고정",
        "status_idle":      "대기 중",
        "status_recording": "녹화 중…",
        "status_paused":    "녹화 일시정지",
        "status_playing":   "실행 중…",
        "status_done":      "실행 완료",
        "status_saved":     "✅ 자동 저장: ",
        "status_loaded":    "✅ 불러옴: ",
        "status_nosave":    "녹화 완료 (동작 없음)",
        "status_waiting":   "대기 중…",
        "btn_start_rec":    "⏺  녹화 시작",
        "btn_stop_rec":     "⏹  녹화 중지",
        "btn_resume_rec":   "▶  녹화 재개",
        "btn_play":         "▶  실행",
        "btn_stop_play":    "⏹  실행 중지",
        "hk_hint":          "클릭하여 단축키 변경",
        "hk_rec":           "녹화",
        "hk_pause":         "일시정지",
        "hk_play":          "실행",
        "hk_stop":          "중지",
        "hk_waiting":       "키를 누르세요…",
        "sec_rec":          "녹화 설정",
        "sec_play":         "재생 설정",
        "sec_saves":        "저장 파일",
        "sec_events":       "녹화된 동작",
        "chk_clicks":       "마우스 클릭",
        "chk_moves":        "마우스 이동",
        "chk_scroll":       "스크롤",
        "chk_keyboard":     "키보드",
        "lbl_speed":        "재생 속도",
        "lbl_loops":        "반복 횟수",
        "lbl_infinite":     "무한 반복",
        "lbl_interval":     "간격",
        "lbl_interval2":    "초 (실행 후 대기)",
        "btn_refresh":      "🔄 새로 고침",
        "btn_load":         "📂 불러오기",
        "btn_delete":       "🗑 삭제",
        "saves_count":      "{n}개 저장됨",
        "events_count":     "{n}개 동작",
        "btn_clear":        "지우기",
        "btn_export":       "내보내기",
        "btn_import":       "가져오기",
        "ev_move":          "이동",
        "ev_lclick":        "좌클릭",
        "ev_rclick":        "우클릭",
        "ev_mclick":        "중클릭",
        "ev_down":          "누름",
        "ev_up":            "놓음",
        "ev_scroll":        "스크롤",
        "ev_key":           "키보드",
        "msg_no_events":    "아직 녹화된 동작이 없습니다!",
        "msg_no_export":    "내보낼 동작이 없습니다!",
        "msg_select_save":  "먼저 저장 파일을 선택하세요!",
        "msg_clear_q":      "현재 동작을 지우겠습니까? (저장 파일 영향 없음)",
        "msg_delete_q":     "이 파일을 삭제하겠습니까?\n",
        "msg_dup_key":      "'{k}'는 이미 다른 기능에 할당되어 있습니다!",
        "msg_saved_to":     "저장 위치:\n",
        "dlg_save":         "다른 이름으로 저장",
        "dlg_open":         "녹화 파일 열기",
        "dlg_export":       "내보내기",
        "dlg_clear":        "지우기",
        "dlg_delete":       "삭제",
        "dlg_dup":          "중복",
        "lang_label":       "언어",
        "pause_hint":       "{k} 로 재개",
    },
}

LANG_ORDER = ["繁體中文", "English", "简体中文", "日本語", "한국어"]


class SecondMouse:
    def __init__(self):
        self.root = tk.Tk()
        self.root.geometry("540x800")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # ── 深色 ttk 樣式 ──
        style = ttk.Style(self.root)
        style.theme_use("default")
        # Combobox
        style.configure("TCombobox",
                        fieldbackground=ACCENT, background=ACCENT,
                        foreground=TEXT, selectbackground=ACCENT,
                        selectforeground=YELLOW, arrowcolor=YELLOW,
                        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER)
        style.map("TCombobox",
                  fieldbackground=[("readonly", ACCENT)],
                  foreground=[("readonly", TEXT)],
                  selectbackground=[("readonly", ACCENT)],
                  selectforeground=[("readonly", YELLOW)])
        # Scale
        style.configure("TScale",
                        background=SURFACE, troughcolor=BORDER,
                        sliderrelief="flat", sliderlength=14)
        style.map("TScale", background=[("active", SURFACE)])

        # 狀態變數
        self.recording     = False
        self.paused        = False
        self.playing       = False
        self.events        = []
        self.rec_listener  = None
        self.kb_listener   = None
        self.play_thread   = None

        self.loop_count      = tk.IntVar(value=1)
        self.loop_infinite   = tk.BooleanVar(value=False)
        self.play_speed      = tk.DoubleVar(value=1.0)
        self.interval_sec    = tk.DoubleVar(value=0.0)
        self.record_clicks   = tk.BooleanVar(value=True)
        self.record_moves    = tk.BooleanVar(value=True)
        self.record_scroll   = tk.BooleanVar(value=True)
        self.record_keyboard = tk.BooleanVar(value=True)
        self.always_on_top   = tk.BooleanVar(value=False)
        self.lang_var        = tk.StringVar(value="繁體中文")

        self.hotkey_rec   = "F9"
        self.hotkey_pause = "F8"
        self.hotkey_play  = "F10"
        self.hotkey_stop  = "F12"

        self._load_config()
        self._build_ui()
        self._apply_config()
        self._start_hotkey_listener()
        self._refresh_save_list()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 語言捷徑 ──
    @property
    def T(self):
        return LANGS[self.lang_var.get()]

    # ════════════════════════════ UI ════════════════════════════

    def _build_ui(self):
        T = self.T
        self.root.title(T["title"])

        # ── 標題列 ──
        hdr = tk.Frame(self.root, bg=BG, pady=10)
        hdr.pack(fill="x", padx=20)
        tk.Label(hdr, text="🖱  " + T["title"], font=FT, bg=BG, fg=TEXT).pack(side="left")

        # 置頂開關
        self.top_cb = tk.Checkbutton(hdr, text=T["pin"],
                                variable=self.always_on_top,
                                font=FS, bg=BG, fg=YELLOW,
                                activebackground=BG, activeforeground=YELLOW,
                                selectcolor=ACCENT, relief="flat",
                                command=self._toggle_topmost)
        self.top_cb.pack(side="right")

        self.status_dot = tk.Label(hdr, text="●", font=("Segoe UI", 13), bg=BG, fg=SUBTEXT)
        self.status_dot.pack(side="right", padx=4)
        self.status_lbl = tk.Label(hdr, text=T["status_idle"], font=FS, bg=BG, fg=SUBTEXT)
        self.status_lbl.pack(side="right")

        # ── 語言下拉選單（放在標題列右側） ──
        lang_cb = ttk.Combobox(hdr, textvariable=self.lang_var,
                               values=LANG_ORDER, state="readonly",
                               width=10, font=FS)
        lang_cb.pack(side="right", padx=(0, 8))
        tk.Label(hdr, text=T["lang_label"] + ":", font=FS, bg=BG, fg=SUBTEXT).pack(side="right")
        lang_cb.bind("<<ComboboxSelected>>", lambda e: self._switch_lang(self.lang_var.get()))

        # ── 主按鈕 ──
        bf = tk.Frame(self.root, bg=BG)
        bf.pack(fill="x", padx=20, pady=8)
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)
        self.rec_btn  = self._big_btn(bf, T["btn_start_rec"], PINK,  self.toggle_record, 0)
        self.play_btn = self._big_btn(bf, T["btn_play"],      GREEN, self.toggle_play,   1)

        # ── 熱鍵設定 ──
        hk = tk.Frame(self.root, bg=SURFACE)
        hk.pack(fill="x", padx=20, pady=(0, 8))
        hki = tk.Frame(hk, bg=SURFACE, pady=5)
        hki.pack(fill="x", padx=12)
        self.hotkey_btns = {}
        for action, lbl_key in [("rec","hk_rec"),("pause","hk_pause"),("play","hk_play"),("stop","hk_stop")]:
            c = tk.Frame(hki, bg=SURFACE)
            c.pack(side="left", expand=True)
            cur = getattr(self, f"hotkey_{action}")
            btn = tk.Button(c, text=cur, font=("Consolas", 11, "bold"),
                            bg=ACCENT, fg=YELLOW, relief="flat", cursor="hand2",
                            activebackground=ACCENT, activeforeground=YELLOW,
                            width=8, command=lambda a=action: self._start_rebind(a))
            btn.pack()
            tk.Label(c, text=T[lbl_key], font=FS, bg=SURFACE, fg=SUBTEXT).pack()
            self.hotkey_btns[action] = btn
        self.hk_hint_lbl = tk.Label(hk, text=T["hk_hint"], font=FS, bg=SURFACE, fg=SUBTEXT, pady=2)
        self.hk_hint_lbl.pack()

        # ── 錄製設定 ──
        self._section(T["sec_rec"])
        of = tk.Frame(self.root, bg=SURFACE)
        of.pack(fill="x", padx=20, pady=(0, 8))
        oi = tk.Frame(of, bg=SURFACE, pady=7, padx=12)
        oi.pack(fill="x")
        for tkey, v in [("chk_clicks", self.record_clicks),
                        ("chk_moves",  self.record_moves),
                        ("chk_scroll", self.record_scroll),
                        ("chk_keyboard", self.record_keyboard)]:
            self._check(oi, T[tkey], v)

        # ── 播放設定 ──
        self._section(T["sec_play"])
        cf = tk.Frame(self.root, bg=SURFACE)
        cf.pack(fill="x", padx=20, pady=(0, 8))
        ci = tk.Frame(cf, bg=SURFACE, pady=7, padx=12)
        ci.pack(fill="x")

        # 速度
        r1 = tk.Frame(ci, bg=SURFACE); r1.pack(fill="x", pady=2)
        tk.Label(r1, text=T["lbl_speed"], font=FB, bg=SURFACE, fg=TEXT, width=10, anchor="w").pack(side="left")
        self.speed_scale = ttk.Scale(r1, from_=0.25, to=4.0, variable=self.play_speed,
                                     orient="horizontal", length=150)
        self.speed_scale.pack(side="left", padx=6)
        self.speed_entry = tk.Entry(r1, width=5, font=FM, bg=ACCENT, fg=YELLOW,
                                    insertbackground=YELLOW, relief="flat", justify="center")
        self.speed_entry.pack(side="left", padx=(0, 2))
        self.speed_entry.insert(0, "1.0")
        tk.Label(r1, text="×", font=FM, bg=SURFACE, fg=YELLOW).pack(side="left")

        self._speed_updating = False

        def on_scale_change(*_):
            if self._speed_updating: return
            self._speed_updating = True
            v = round(self.play_speed.get(), 2)
            self.speed_entry.delete(0, "end")
            self.speed_entry.insert(0, str(v))
            self._speed_updating = False

        def on_entry_commit(event=None):
            if self._speed_updating: return
            try:
                v = float(self.speed_entry.get())
                v = max(0.05, min(20.0, v))
            except ValueError:
                v = self.play_speed.get()
            self._speed_updating = True
            self.play_speed.set(v)
            self.speed_entry.delete(0, "end")
            self.speed_entry.insert(0, str(round(v, 2)))
            self._speed_updating = False

        self.play_speed.trace_add("write", on_scale_change)
        self.speed_entry.bind("<Return>", on_entry_commit)
        self.speed_entry.bind("<FocusOut>", on_entry_commit)

        # 重複次數
        r2 = tk.Frame(ci, bg=SURFACE); r2.pack(fill="x", pady=2)
        tk.Label(r2, text=T["lbl_loops"], font=FB, bg=SURFACE, fg=TEXT, width=10, anchor="w").pack(side="left")
        self.loop_spin = tk.Spinbox(r2, from_=1, to=9999, textvariable=self.loop_count,
                                    width=6, bg=ACCENT, fg=TEXT, buttonbackground=ACCENT,
                                    insertbackground=TEXT, relief="flat", font=FM)
        self.loop_spin.pack(side="left", padx=6)
        self._check(r2, T["lbl_infinite"], self.loop_infinite, callback=self._toggle_infinite)

        # 每輪間隔
        r3 = tk.Frame(ci, bg=SURFACE); r3.pack(fill="x", pady=2)
        tk.Label(r3, text=T["lbl_interval"], font=FB, bg=SURFACE, fg=TEXT, width=10, anchor="w").pack(side="left")
        tk.Spinbox(r3, from_=0, to=999, increment=0.5, textvariable=self.interval_sec,
                   width=6, bg=ACCENT, fg=TEXT, buttonbackground=ACCENT,
                   insertbackground=TEXT, relief="flat", font=FM, format="%.1f").pack(side="left", padx=6)
        tk.Label(r3, text=T["lbl_interval2"], font=FS, bg=SURFACE, fg=SUBTEXT).pack(side="left")

        # ── 存檔列表 ──
        self._section(T["sec_saves"])
        sf = tk.Frame(self.root, bg=SURFACE)
        sf.pack(fill="x", padx=20, pady=(0, 8))
        si = tk.Frame(sf, bg=SURFACE, padx=6, pady=6)
        si.pack(fill="x")
        sl_scroll = tk.Scrollbar(si, orient="vertical")
        sl_scroll.pack(side="right", fill="y")
        self.save_list = tk.Listbox(si, bg=ACCENT, fg=TEXT, font=FM,
                                    bd=0, relief="flat", selectbackground=BLUE,
                                    yscrollcommand=sl_scroll.set, height=4, cursor="hand2")
        self.save_list.pack(fill="x", expand=True)
        sl_scroll.config(command=self.save_list.yview)
        self.save_list.bind("<Double-Button-1>", self._load_selected_save)

        sb_row = tk.Frame(sf, bg=SURFACE, padx=6, pady=4)
        sb_row.pack(fill="x")
        for tkey, cmd in [("btn_refresh", self._refresh_save_list),
                          ("btn_load",    self._load_selected_save),
                          ("btn_delete",  self._delete_selected_save)]:
            tk.Button(sb_row, text=T[tkey], font=FS, bg=BORDER, fg=TEXT,
                      relief="flat", cursor="hand2", padx=8, pady=3,
                      activebackground=ACCENT, activeforeground=TEXT,
                      command=cmd).pack(side="left", padx=2)
        self.save_count_lbl = tk.Label(sb_row, text="", font=FS, bg=SURFACE, fg=SUBTEXT)
        self.save_count_lbl.pack(side="right", padx=4)

        # ── 已錄製動作 ──
        self._section(T["sec_events"])
        lf = tk.Frame(self.root, bg=SURFACE)
        lf.pack(fill="both", expand=True, padx=20, pady=(0, 8))
        li = tk.Frame(lf, bg=SURFACE, padx=6, pady=6)
        li.pack(fill="both", expand=True)
        ev_scroll = tk.Scrollbar(li)
        ev_scroll.pack(side="right", fill="y")
        self.event_list = tk.Listbox(li, bg=ACCENT, fg=TEXT, font=FM,
                                     bd=0, relief="flat", selectbackground=PINK,
                                     yscrollcommand=ev_scroll.set, height=5)
        self.event_list.pack(fill="both", expand=True)
        ev_scroll.config(command=self.event_list.yview)

        # ── 底部工具列 ──
        tf = tk.Frame(self.root, bg=BG)
        tf.pack(fill="x", padx=20, pady=12)
        for tkey, cmd in [("btn_clear",  self.clear_events),
                          ("btn_export", self.export_events),
                          ("btn_import", self.import_events)]:
            tk.Button(tf, text=T[tkey], font=FS, bg=BORDER, fg=TEXT, relief="flat",
                      cursor="hand2", activebackground=ACCENT, activeforeground=TEXT,
                      command=cmd, padx=10, pady=4).pack(side="left", padx=3)
        self.count_lbl = tk.Label(tf, text=T["events_count"].format(n=0),
                                  font=FS, bg=BG, fg=SUBTEXT)
        self.count_lbl.pack(side="right")

    def _switch_lang(self, lang):
        self.lang_var.set(lang)
        # 重建 UI：清除所有 widget 再重建
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()
        self._apply_config()
        self._refresh_save_list()
        # 重新顯示事件列表
        for ev in self.events:
            self._append_list_row(ev)
        self.count_lbl.config(text=self.T["events_count"].format(n=len(self.events)))

    def _apply_config(self):
        if self.always_on_top.get():
            self.root.attributes("-topmost", True)
        if self.loop_infinite.get():
            self.loop_spin.config(state="disabled")
        self.speed_entry.delete(0, "end")
        self.speed_entry.insert(0, str(round(self.play_speed.get(), 2)))

    def _big_btn(self, parent, text, color, cmd, col):
        btn = tk.Button(parent, text=text, font=FBT, bg=color, fg="white",
                        relief="flat", cursor="hand2",
                        activebackground=color, activeforeground="white",
                        command=cmd, pady=10)
        btn.grid(row=0, column=col, sticky="ew", padx=3)
        return btn

    def _section(self, title):
        f = tk.Frame(self.root, bg=BG)
        f.pack(fill="x", padx=20, pady=(5, 2))
        tk.Label(f, text=title, font=("Segoe UI", 9, "bold"), bg=BG, fg=SUBTEXT).pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=(8, 0), pady=6)

    def _check(self, parent, text, var, callback=None):
        tk.Checkbutton(parent, text=text, variable=var, font=FS,
                       bg=SURFACE, fg=TEXT, activebackground=SURFACE,
                       activeforeground=TEXT, selectcolor=ACCENT, relief="flat",
                       command=callback).pack(side="left", padx=8)

    # ════════════════════════════ 置頂 ════════════════════════════

    def _toggle_topmost(self):
        self.root.attributes("-topmost", self.always_on_top.get())

    # ════════════════════════════ 熱鍵重新設定 ════════════════════════════

    def _start_rebind(self, action):
        btn = self.hotkey_btns[action]
        old_text = btn.cget("text")
        btn.config(text=self.T["hk_waiting"], bg=PINK, fg="white")
        self._rebind_active = action

        def finish():
            self._rebind_active = None
            for attr in ("_rebind_kb_listener", "_rebind_mouse_listener"):
                l = getattr(self, attr, None)
                if l:
                    try: l.stop()
                    except: pass
                    setattr(self, attr, None)

        def cancel():
            finish()
            self.root.after(0, lambda: btn.config(text=old_text, bg=ACCENT, fg=YELLOW))

        def capture_key(key):
            if key == keyboard.Key.esc:
                cancel(); return
            name = next((k for k in KEY_OPTIONS if _key_to_pynput(k) == key), None)
            if name is None: return
            others = {a: getattr(self, f"hotkey_{a}") for a in ("rec","pause","play","stop") if a != action}
            if name in others.values():
                self.root.after(0, lambda: messagebox.showwarning(
                    self.T["dlg_dup"], self.T["msg_dup_key"].format(k=name)))
                self.root.after(0, lambda: btn.config(text=old_text, bg=ACCENT, fg=YELLOW))
            else:
                setattr(self, f"hotkey_{action}", name)
                self.root.after(0, lambda: btn.config(text=name, bg=ACCENT, fg=YELLOW))
            finish()

        def capture_click(x, y, button, pressed):
            if pressed: cancel()

        self._rebind_kb_listener = keyboard.Listener(on_press=capture_key)
        self._rebind_kb_listener.start()
        self._rebind_mouse_listener = mouse.Listener(on_click=capture_click)
        self._rebind_mouse_listener.start()

    # ════════════════════════════ 錄製 ════════════════════════════

    def toggle_record(self):
        if self.playing: return
        self._stop_record() if self.recording else self._start_record()

    def toggle_pause(self):
        if not self.recording: return
        self.paused = not self.paused
        if self.paused:
            self.rec_btn.config(text=self.T["btn_resume_rec"], bg=YELLOW)
            self._set_status(self.T["status_paused"] + "（" +
                             self.T["pause_hint"].format(k=self.hotkey_pause) + "）", SUBTEXT)
        else:
            self.rec_btn.config(text=self.T["btn_stop_rec"], bg="#c0392b")
            self._set_status(self.T["status_recording"], PINK)
            self._last_time = time.time()

    def _start_record(self):
        self.recording = True
        self.paused = False
        self.events = []
        self._last_time = time.time()
        self._set_status(self.T["status_recording"], PINK)
        self.rec_btn.config(text=self.T["btn_stop_rec"], bg="#c0392b")
        self.play_btn.config(state="disabled")
        self.event_list.delete(0, "end")
        self.count_lbl.config(text=self.T["events_count"].format(n=0))

        def on_move(x, y):
            if self.paused: return
            if self.record_moves.get(): self._add_event("move", x, y)

        def on_click(x, y, button, pressed):
            if self.paused: return
            if self.record_clicks.get():
                self._add_event("click", x, y, extra={"btn": str(button), "pressed": pressed})

        def on_scroll(x, y, dx, dy):
            if self.paused: return
            if self.record_scroll.get():
                self._add_event("scroll", x, y, extra={"dx": dx, "dy": dy})

        def on_key_press(key):
            if self.paused: return
            if not self.record_keyboard.get(): return
            for hk in (self.hotkey_rec, self.hotkey_pause, self.hotkey_play, self.hotkey_stop):
                if key == _key_to_pynput(hk): return
            self._add_key_event(key, pressed=True)

        def on_key_release(key):
            if self.paused: return
            if not self.record_keyboard.get(): return
            for hk in (self.hotkey_rec, self.hotkey_pause, self.hotkey_play, self.hotkey_stop):
                if key == _key_to_pynput(hk): return
            self._add_key_event(key, pressed=False)

        self.rec_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
        self.rec_listener.start()
        self.rec_kb_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
        self.rec_kb_listener.start()

    def _stop_record(self):
        self.recording = False
        self.paused = False
        if self.rec_listener:
            self.rec_listener.stop(); self.rec_listener = None
        if getattr(self, "rec_kb_listener", None):
            self.rec_kb_listener.stop(); self.rec_kb_listener = None
        self.rec_btn.config(text=self.T["btn_start_rec"], bg=PINK)
        self.play_btn.config(state="normal")
        self._auto_save()

    def _add_event(self, kind, x, y, extra=None):
        now = time.time()
        delay = now - self._last_time
        self._last_time = now
        ev = {"type": kind, "x": x, "y": y, "delay": round(delay, 4)}
        if extra: ev.update(extra)
        self.events.append(ev)
        self._append_list_row(ev)

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
        self._append_list_row(ev)

    def _append_list_row(self, ev):
        T = self.T
        kind  = ev["type"]
        delay = ev.get("delay", 0)
        if kind == "key":
            act   = T["ev_down"] if ev.get("pressed") else T["ev_up"]
            label = f"  {T['ev_key']}{act}  {ev.get('key','?'):<20}   +{delay:.3f}s"
        else:
            x, y = ev["x"], ev["y"]
            if kind == "move":
                label = f"  {T['ev_move']}     ({x:5d}, {y:5d})   +{delay:.3f}s"
            elif kind == "click":
                bn = T["ev_lclick"] if "left" in ev.get("btn","") else \
                     T["ev_rclick"] if "right" in ev.get("btn","") else T["ev_mclick"]
                act = T["ev_down"] if ev.get("pressed") else T["ev_up"]
                label = f"  {bn}{act}  ({x:5d}, {y:5d})   +{delay:.3f}s"
            else:
                label = f"  {T['ev_scroll']}     ({x:5d}, {y:5d}) dy={ev.get('dy',0):+d}   +{delay:.3f}s"
        self.root.after(0, lambda l=label: (
            self.event_list.insert("end", l),
            self.event_list.yview("end"),
            self.count_lbl.config(text=T["events_count"].format(n=len(self.events)))
        ))

    # ════════════════════════════ 播放 ════════════════════════════

    def toggle_play(self):
        if self.recording: return
        self._stop_play() if self.playing else self._start_play()

    def _start_play(self):
        if not self.events:
            messagebox.showinfo(self.T["title"], self.T["msg_no_events"])
            return
        self.playing = True
        self._set_status(self.T["status_playing"], GREEN)
        self.play_btn.config(text=self.T["btn_stop_play"], bg="#c0392b")
        self.rec_btn.config(state="disabled")
        total    = 0 if self.loop_infinite.get() else self.loop_count.get()
        speed    = self.play_speed.get()
        interval = self.interval_sec.get()
        self.play_thread = threading.Thread(
            target=self._play_loop, args=(total, speed, interval), daemon=True)
        self.play_thread.start()

    def _play_loop(self, total, speed, interval):
        mc = MouseController()
        kc = keyboard.Controller()

        def _play_key(ev):
            key_str = ev.get("key", "")
            if key_str.startswith("Key."):
                try: key = getattr(keyboard.Key, key_str[4:])
                except AttributeError: return
            elif len(key_str) == 1:
                key = key_str
            else:
                return
            kc.press(key) if ev.get("pressed") else kc.release(key)

        i = 0
        while self.playing:
            for ev in self.events:
                if not self.playing: break
                delay = ev["delay"] / speed
                if delay > 0: time.sleep(delay)
                kind = ev["type"]
                if kind == "key":
                    _play_key(ev)
                else:
                    x, y = ev["x"], ev["y"]
                    if kind == "move":
                        mc.position = (x, y)
                    elif kind == "click":
                        mc.position = (x, y)
                        btn = Button.left  if "left"  in ev.get("btn","") else \
                              Button.right if "right" in ev.get("btn","") else Button.middle
                        mc.press(btn) if ev.get("pressed") else mc.release(btn)
                    elif kind == "scroll":
                        mc.position = (x, y)
                        mc.scroll(ev.get("dx", 0), ev.get("dy", 0))
            i += 1
            if total > 0 and i >= total:
                break
            if self.playing and interval > 0:
                self.root.after(0, lambda n=i, t=total: self._set_status(
                    f"{self.T['status_waiting']} ({n}{'/' + str(t) if t else ''})", YELLOW))
                waited = 0.0
                while self.playing and waited < interval:
                    time.sleep(0.05); waited += 0.05

        self.root.after(0, self._play_done)

    def _play_done(self):
        self.playing = False
        self._set_status(self.T["status_done"], YELLOW)
        self.play_btn.config(text=self.T["btn_play"], bg=GREEN)
        self.rec_btn.config(state="normal")

    def _stop_play(self):
        self.playing = False
        try:
            kc = keyboard.Controller()
            for k in [keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
                      keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
                      keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
                      keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r,
                      keyboard.Key.caps_lock]:
                try: kc.release(k)
                except: pass
        except: pass

    # ════════════════════════════ 存檔 ════════════════════════════

    def _auto_save(self):
        if not self.events:
            self._set_status(self.T["status_nosave"], SUBTEXT); return
        os.makedirs(SAVE_DIR, exist_ok=True)
        filename = datetime.now().strftime("rec_%Y%m%d_%H%M%S.json")
        path = os.path.join(SAVE_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.events, f, ensure_ascii=False, indent=2)
        self._set_status(self.T["status_saved"] + filename, GREEN)
        self.count_lbl.config(text=self.T["events_count"].format(n=len(self.events)))
        self._refresh_save_list()

    def _refresh_save_list(self):
        self.save_list.delete(0, "end")
        os.makedirs(SAVE_DIR, exist_ok=True)
        files = sorted([f for f in os.listdir(SAVE_DIR) if f.endswith(".json")], reverse=True)
        for f in files:
            try:
                data = json.load(open(os.path.join(SAVE_DIR, f), encoding="utf-8"))
                count = len(data)
            except: count = "?"
            try:
                dt = datetime.strptime(f, "rec_%Y%m%d_%H%M%S.json")
                label = f"  {dt.strftime('%Y/%m/%d  %H:%M:%S')}    {count} "
            except:
                label = f"  {f}   {count} "
            self.save_list.insert("end", label)
        self._files = files
        self.save_count_lbl.config(text=self.T["saves_count"].format(n=len(files)))

    def _load_selected_save(self, event=None):
        sel = self.save_list.curselection()
        if not sel:
            messagebox.showinfo(self.T["title"], self.T["msg_select_save"]); return
        fname = self._files[sel[0]]
        with open(os.path.join(SAVE_DIR, fname), encoding="utf-8") as f:
            self.events = json.load(f)
        self.event_list.delete(0, "end")
        for ev in self.events:
            self._append_list_row(ev)
        self.count_lbl.config(text=self.T["events_count"].format(n=len(self.events)))
        self._set_status(self.T["status_loaded"] + fname, BLUE)

    def _delete_selected_save(self):
        sel = self.save_list.curselection()
        if not sel:
            messagebox.showinfo(self.T["title"], self.T["msg_select_save"]); return
        fname = self._files[sel[0]]
        if messagebox.askyesno(self.T["dlg_delete"], self.T["msg_delete_q"] + fname):
            os.remove(os.path.join(SAVE_DIR, fname))
            self._refresh_save_list()

    # ════════════════════════════ 工具列 ════════════════════════════

    def clear_events(self):
        if messagebox.askyesno(self.T["dlg_clear"], self.T["msg_clear_q"]):
            self.events = []
            self.event_list.delete(0, "end")
            self.count_lbl.config(text=self.T["events_count"].format(n=0))
            self._set_status(self.T["status_idle"], SUBTEXT)

    def export_events(self):
        if not self.events:
            messagebox.showinfo(self.T["dlg_export"], self.T["msg_no_export"]); return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")], title=self.T["dlg_save"])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.events, f, ensure_ascii=False, indent=2)
            messagebox.showinfo(self.T["dlg_export"], self.T["msg_saved_to"] + path)

    def import_events(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")], title=self.T["dlg_open"])
        if path:
            with open(path, encoding="utf-8") as f:
                self.events = json.load(f)
            self.event_list.delete(0, "end")
            for ev in self.events: self._append_list_row(ev)
            self.count_lbl.config(text=self.T["events_count"].format(n=len(self.events)))
            self._set_status(self.T["status_loaded"] + os.path.basename(path), YELLOW)

    # ════════════════════════════ 工具 ════════════════════════════

    def _set_status(self, text, color):
        self.status_lbl.config(text=text, fg=color)
        self.status_dot.config(fg=color)

    def _toggle_infinite(self):
        self.loop_spin.config(state="disabled" if self.loop_infinite.get() else "normal")

    def _start_hotkey_listener(self):
        def on_press(key):
            if getattr(self, "_rebind_active", None): return
            if key == _key_to_pynput(self.hotkey_rec):
                self.root.after(0, self.toggle_record)
            elif key == _key_to_pynput(self.hotkey_pause):
                if self.recording: self.root.after(0, self.toggle_pause)
            elif key == _key_to_pynput(self.hotkey_play):
                self.root.after(0, self.toggle_play)
            elif key == _key_to_pynput(self.hotkey_stop):
                if self.recording: self.root.after(0, self._stop_record)
                if self.playing:   self.root.after(0, self._stop_play)
        self.kb_listener = keyboard.Listener(on_press=on_press)
        self.kb_listener.daemon = True
        self.kb_listener.start()

    def _save_config(self):
        cfg = {
            "loop_count":      self.loop_count.get(),
            "loop_infinite":   self.loop_infinite.get(),
            "play_speed":      self.play_speed.get(),
            "interval_sec":    self.interval_sec.get(),
            "record_clicks":   self.record_clicks.get(),
            "record_moves":    self.record_moves.get(),
            "record_scroll":   self.record_scroll.get(),
            "record_keyboard": self.record_keyboard.get(),
            "always_on_top":   self.always_on_top.get(),
            "hotkey_rec":      self.hotkey_rec,
            "hotkey_pause":    self.hotkey_pause,
            "hotkey_play":     self.hotkey_play,
            "hotkey_stop":     self.hotkey_stop,
            "lang":            self.lang_var.get(),
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

    def _load_config(self):
        if not os.path.exists(CONFIG_FILE): return
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                cfg = json.load(f)
            self.loop_count.set(cfg.get("loop_count", 1))
            self.loop_infinite.set(cfg.get("loop_infinite", False))
            self.play_speed.set(cfg.get("play_speed", 1.0))
            self.interval_sec.set(cfg.get("interval_sec", 0.0))
            self.record_clicks.set(cfg.get("record_clicks", True))
            self.record_moves.set(cfg.get("record_moves", True))
            self.record_scroll.set(cfg.get("record_scroll", True))
            self.record_keyboard.set(cfg.get("record_keyboard", True))
            self.always_on_top.set(cfg.get("always_on_top", False))
            self.hotkey_rec   = cfg.get("hotkey_rec",   self.hotkey_rec)
            self.hotkey_pause = cfg.get("hotkey_pause", self.hotkey_pause)
            self.hotkey_play  = cfg.get("hotkey_play",  self.hotkey_play)
            self.hotkey_stop  = cfg.get("hotkey_stop",  self.hotkey_stop)
            lang = cfg.get("lang", "繁體中文")
            if lang in LANGS: self.lang_var.set(lang)
        except: pass

    def _on_close(self):
        self._save_config()
        self.playing = self.recording = False
        if self.rec_listener: self.rec_listener.stop()
        if getattr(self, "rec_kb_listener", None): self.rec_kb_listener.stop()
        if self.kb_listener: self.kb_listener.stop()
        for attr in ("_rebind_kb_listener", "_rebind_mouse_listener"):
            l = getattr(self, attr, None)
            if l:
                try: l.stop()
                except: pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    try:
        app = SecondMouse()
        app.run()
    except Exception:
        import traceback
        print("\n======= 錯誤訊息 =======")
        traceback.print_exc()
        print("========================")
        input("\n按 Enter 關閉...")
