"""
第二滑鼠 - 使用者介面
功能：錄製/播放、自動存檔、讀取存檔、間隔時間、置頂開關、
      定時啟動（啟動下方選取的腳本）、動作編輯器（新增/編輯/刪除/排序/原始碼編輯）
所有不涉及 UI 的邏輯都放在 mouse_engine.py，這裡只負責畫面與事件串接。
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime

import mouse_engine as eng
from pynput import keyboard, mouse

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
BORDER  = "#2d2d4e"

FT = ("Segoe UI", 18, "bold")
FB = ("Segoe UI", 10)
FM = ("Consolas", 9)
FBT = ("Segoe UI", 10, "bold")
FS = ("Segoe UI", 9)


class SecondMouse:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("第二滑鼠")
        self.root.geometry("560x960")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # 事件資料（單一真實來源，錄製/讀檔/編輯都操作這份清單）
        self.events = []

        # 引擎物件
        self.recorder = eng.MacroRecorder(on_event=self._on_event_recorded)
        self.player = eng.MacroPlayer(on_wait=self._on_play_wait, on_finished=self._on_play_finished)
        self.scheduler = eng.Scheduler(on_tick=self._on_schedule_tick,
                                        on_trigger=self._on_schedule_trigger,
                                        on_cancel=self._on_schedule_cancel)

        # UI 狀態變數
        self.loop_count    = tk.IntVar(value=1)
        self.loop_infinite = tk.BooleanVar(value=False)
        self.play_speed    = tk.DoubleVar(value=1.0)
        self.interval_sec  = tk.DoubleVar(value=0.0)
        self.record_clicks   = tk.BooleanVar(value=True)
        self.record_moves    = tk.BooleanVar(value=True)
        self.record_scroll   = tk.BooleanVar(value=True)
        self.record_keyboard = tk.BooleanVar(value=True)
        self.always_on_top = tk.BooleanVar(value=False)

        self.hotkey_rec   = "F9"
        self.hotkey_pause = "F8"
        self.hotkey_play  = "F10"
        self.hotkey_stop  = "F12"

        self.schedule_hour   = tk.StringVar(value="09")
        self.schedule_minute = tk.StringVar(value="00")
        self._scheduled_save_filename = None   # 開始排程當下所選的存檔檔名

        self._load_config()
        self._build_ui()
        self._apply_config()
        self._start_hotkey_listener()
        self._refresh_save_list()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ════════════════════════════ UI 建構 ════════════════════════════

    def _build_ui(self):
        hdr = tk.Frame(self.root, bg=BG, pady=10)
        hdr.pack(fill="x", padx=20)
        tk.Label(hdr, text="🖱  第二滑鼠", font=FT, bg=BG, fg=TEXT).pack(side="left")

        top_cb = tk.Checkbutton(hdr, text="📌 置頂", variable=self.always_on_top,
                                 font=FS, bg=BG, fg=YELLOW,
                                 activebackground=BG, activeforeground=YELLOW,
                                 selectcolor=ACCENT, relief="flat",
                                 command=self._toggle_topmost)
        top_cb.pack(side="right")

        self.status_dot = tk.Label(hdr, text="●", font=("Segoe UI", 13), bg=BG, fg=SUBTEXT)
        self.status_dot.pack(side="right", padx=4)
        self.status_lbl = tk.Label(hdr, text="待機中", font=FS, bg=BG, fg=SUBTEXT)
        self.status_lbl.pack(side="right")

        # ── 主按鈕 ──
        bf = tk.Frame(self.root, bg=BG)
        bf.pack(fill="x", padx=20, pady=8)
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)
        self.rec_btn  = self._big_btn(bf, "⏺  開始錄製", PINK, self.toggle_record, 0)
        self.play_btn = self._big_btn(bf, "▶  執行", GREEN, self.toggle_play, 1)

        # ── 熱鍵設定 ──
        hk = tk.Frame(self.root, bg=SURFACE)
        hk.pack(fill="x", padx=20, pady=8)
        hki = tk.Frame(hk, bg=SURFACE, pady=5)
        hki.pack(fill="x", padx=12)
        self.hotkey_btns = {}
        for action, lbl in [("rec", "錄製"), ("pause", "暫停錄製"), ("play", "執行"), ("stop", "停止")]:
            c = tk.Frame(hki, bg=SURFACE)
            c.pack(side="left", expand=True)
            cur = getattr(self, f"hotkey_{action}")
            btn = tk.Button(c, text=cur, font=("Consolas", 11, "bold"),
                             bg=ACCENT, fg=YELLOW, relief="flat", cursor="hand2",
                             activebackground=ACCENT, activeforeground=YELLOW,
                             width=8, command=lambda a=action: self._start_rebind(a))
            btn.pack()
            tk.Label(c, text=lbl, font=FS, bg=SURFACE, fg=SUBTEXT).pack()
            self.hotkey_btns[action] = btn
        tk.Label(hk, text="點擊按鍵可重新設定熱鍵", font=FS, bg=SURFACE, fg=SUBTEXT, pady=2).pack()

        # ── 錄製設定 ──
        self._section("錄製設定")
        of = tk.Frame(self.root, bg=SURFACE)
        of.pack(fill="x", padx=20, pady=8)
        oi = tk.Frame(of, bg=SURFACE, pady=7, padx=12)
        oi.pack(fill="x")
        for t, v in [("滑鼠點擊", self.record_clicks), ("滑鼠移動", self.record_moves),
                     ("滾輪捲動", self.record_scroll), ("鍵盤輸入", self.record_keyboard)]:
            self._check(oi, t, v)

        # ── 播放設定 ──
        self._section("播放設定")
        cf = tk.Frame(self.root, bg=SURFACE)
        cf.pack(fill="x", padx=20, pady=8)
        ci = tk.Frame(cf, bg=SURFACE, pady=7, padx=12)
        ci.pack(fill="x")

        r1 = tk.Frame(ci, bg=SURFACE); r1.pack(fill="x", pady=2)
        tk.Label(r1, text="播放速度", font=FB, bg=SURFACE, fg=TEXT, width=10, anchor="w").pack(side="left")
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

        r2 = tk.Frame(ci, bg=SURFACE); r2.pack(fill="x", pady=2)
        tk.Label(r2, text="重複次數", font=FB, bg=SURFACE, fg=TEXT, width=10, anchor="w").pack(side="left")
        self.loop_spin = tk.Spinbox(r2, from_=1, to=9999, textvariable=self.loop_count,
                                     width=6, bg=ACCENT, fg=TEXT, buttonbackground=ACCENT,
                                     insertbackground=TEXT, relief="flat", font=FM)
        self.loop_spin.pack(side="left", padx=6)
        self._check(r2, "無限循環", self.loop_infinite, callback=self._toggle_infinite)

        r3 = tk.Frame(ci, bg=SURFACE); r3.pack(fill="x", pady=2)
        tk.Label(r3, text="每輪間隔", font=FB, bg=SURFACE, fg=TEXT, width=10, anchor="w").pack(side="left")
        tk.Spinbox(r3, from_=0, to=999, increment=0.5, textvariable=self.interval_sec,
                   width=6, bg=ACCENT, fg=TEXT, buttonbackground=ACCENT,
                   insertbackground=TEXT, relief="flat", font=FM, format="%.1f").pack(side="left", padx=6)
        tk.Label(r3, text="秒（每次執行完後等待）", font=FS, bg=SURFACE, fg=SUBTEXT).pack(side="left")

        # ── 定時啟動（啟動下方選取的腳本） ──
        self._section("定時啟動")
        sch = tk.Frame(self.root, bg=SURFACE)
        sch.pack(fill="x", padx=20, pady=8)
        schi = tk.Frame(sch, bg=SURFACE, pady=7, padx=12)
        schi.pack(fill="x")

        sr1 = tk.Frame(schi, bg=SURFACE); sr1.pack(fill="x", pady=2)
        tk.Label(sr1, text="時間", font=FB, bg=SURFACE, fg=TEXT, width=10, anchor="w").pack(side="left")
        tk.Spinbox(sr1, from_=0, to=23, textvariable=self.schedule_hour, width=3,
                   bg=ACCENT, fg=TEXT, buttonbackground=ACCENT, insertbackground=TEXT,
                   relief="flat", font=FM, format="%02.0f").pack(side="left")
        tk.Label(sr1, text=":", font=FM, bg=SURFACE, fg=TEXT).pack(side="left")
        tk.Spinbox(sr1, from_=0, to=59, textvariable=self.schedule_minute, width=3,
                   bg=ACCENT, fg=TEXT, buttonbackground=ACCENT, insertbackground=TEXT,
                   relief="flat", font=FM, format="%02.0f").pack(side="left")

        sr4 = tk.Frame(schi, bg=SURFACE); sr4.pack(fill="x", pady=6)
        self.schedule_start_btn = tk.Button(sr4, text="⏱ 開始排程", font=FS, bg=BORDER, fg=TEXT,
                                             relief="flat", cursor="hand2", padx=8, pady=3,
                                             activebackground=ACCENT, activeforeground=TEXT,
                                             command=self._start_schedule)
        self.schedule_start_btn.pack(side="left", padx=2)
        self.schedule_cancel_btn = tk.Button(sr4, text="✕ 取消排程", font=FS, bg=BORDER, fg=TEXT,
                                              relief="flat", cursor="hand2", padx=8, pady=3,
                                              activebackground=ACCENT, activeforeground=TEXT,
                                              state="disabled", command=self._cancel_schedule)
        self.schedule_cancel_btn.pack(side="left", padx=2)
        self.schedule_status_lbl = tk.Label(sr4, text="尚未排程", font=FS, bg=SURFACE, fg=SUBTEXT)
        self.schedule_status_lbl.pack(side="left", padx=8)

        # ── 存檔列表 ──
        self._section("存檔記錄")
        sf = tk.Frame(self.root, bg=SURFACE)
        sf.pack(fill="x", padx=20, pady=8)
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
        tk.Button(sb_row, text="🔄 重新整理", font=FS, bg=BORDER, fg=TEXT, relief="flat",
                  cursor="hand2", padx=8, pady=3, activebackground=ACCENT, activeforeground=TEXT,
                  command=self._refresh_save_list).pack(side="left", padx=2)
        tk.Button(sb_row, text="📂 載入選取", font=FS, bg=BORDER, fg=TEXT, relief="flat",
                  cursor="hand2", padx=8, pady=3, activebackground=ACCENT, activeforeground=TEXT,
                  command=self._load_selected_save).pack(side="left", padx=2)
        tk.Button(sb_row, text="✎ 重新命名", font=FS, bg=BORDER, fg=TEXT, relief="flat",
                  cursor="hand2", padx=8, pady=3, activebackground=ACCENT, activeforeground=TEXT,
                  command=self._rename_selected_save).pack(side="left", padx=2)
        tk.Button(sb_row, text="🗑 刪除選取", font=FS, bg=BORDER, fg=TEXT, relief="flat",
                  cursor="hand2", padx=8, pady=3, activebackground=ACCENT, activeforeground=TEXT,
                  command=self._delete_selected_save).pack(side="left", padx=2)
        self.save_count_lbl = tk.Label(sb_row, text="", font=FS, bg=SURFACE, fg=SUBTEXT)
        self.save_count_lbl.pack(side="right", padx=4)

        # ── 已錄製動作（可編輯） ──
        sec = tk.Frame(self.root, bg=BG)
        sec.pack(fill="x", padx=20, pady=2)
        tk.Label(sec, text="已錄製動作（雙擊可編輯）", font=("Segoe UI", 9, "bold"), bg=BG, fg=SUBTEXT).pack(side="left")
        tk.Button(sec, text="📝 編輯腳本", font=FS, bg=BORDER, fg=TEXT, relief="flat",
                  cursor="hand2", activebackground=ACCENT, activeforeground=TEXT,
                  command=self._open_script_editor, padx=6, pady=1).pack(side="left", padx=8)
        tk.Frame(sec, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=0, pady=6)

        lf = tk.Frame(self.root, bg=SURFACE)
        lf.pack(fill="both", expand=True, padx=20, pady=8)
        li = tk.Frame(lf, bg=SURFACE, padx=6, pady=6)
        li.pack(fill="both", expand=True)
        ev_scroll = tk.Scrollbar(li)
        ev_scroll.pack(side="right", fill="y")
        self.event_list = tk.Listbox(li, bg=ACCENT, fg=TEXT, font=FM,
                                      bd=0, relief="flat", selectbackground=PINK,
                                      yscrollcommand=ev_scroll.set, height=6)
        self.event_list.pack(fill="both", expand=True)
        ev_scroll.config(command=self.event_list.yview)
        self.event_list.bind("<Double-Button-1>", lambda e: self._edit_selected_event())

        # ── 底部工具列 ──
        tf = tk.Frame(self.root, bg=BG)
        tf.pack(fill="x", padx=20, pady=12)
        for t, cmd in [("清除", self.clear_events), ("匯出", self.export_events), ("匯入", self.import_events)]:
            tk.Button(tf, text=t, font=FS, bg=BORDER, fg=TEXT, relief="flat",
                      cursor="hand2", activebackground=ACCENT, activeforeground=TEXT,
                      command=cmd, padx=10, pady=4).pack(side="left", padx=3)
        self.count_lbl = tk.Label(tf, text="共 0 個動作", font=FS, bg=BG, fg=SUBTEXT)
        self.count_lbl.pack(side="right")

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
        f.pack(fill="x", padx=20, pady=2)
        tk.Label(f, text=title, font=("Segoe UI", 9, "bold"), bg=BG, fg=SUBTEXT).pack(side="left")
        tk.Frame(f, bg=BORDER, height=1).pack(side="left", fill="x", expand=True, padx=0, pady=6)

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
        btn.config(text="按任意鍵…", bg=PINK, fg="white")
        self._rebind_active = action

        def finish():
            self._rebind_active = None
            if getattr(self, "_rebind_kb_listener", None):
                try: self._rebind_kb_listener.stop()
                except Exception: pass
                self._rebind_kb_listener = None
            if getattr(self, "_rebind_mouse_listener", None):
                try: self._rebind_mouse_listener.stop()
                except Exception: pass
                self._rebind_mouse_listener = None

        def cancel():
            finish()
            self.root.after(0, lambda: btn.config(text=old_text, bg=ACCENT, fg=YELLOW))

        def capture_key(key):
            if key == keyboard.Key.esc:
                cancel()
                return
            name = None
            for k in eng.KEY_OPTIONS:
                if eng.key_to_pynput(k) == key:
                    name = k
                    break
            if name is None:
                return
            others = {a: getattr(self, f"hotkey_{a}") for a in ("rec", "pause", "play", "stop") if a != action}
            if name in others.values():
                self.root.after(0, lambda: messagebox.showwarning("重複", f"「{name}」已經是其他功能的熱鍵了！"))
                self.root.after(0, lambda: btn.config(text=old_text, bg=ACCENT, fg=YELLOW))
            else:
                setattr(self, f"hotkey_{action}", name)
                self.root.after(0, lambda: btn.config(text=name, bg=ACCENT, fg=YELLOW))
            finish()

        def capture_click(x, y, button, pressed):
            if pressed:
                cancel()

        self._rebind_kb_listener = keyboard.Listener(on_press=capture_key)
        self._rebind_kb_listener.start()
        self._rebind_mouse_listener = mouse.Listener(on_click=capture_click)
        self._rebind_mouse_listener.start()

    # ════════════════════════════ 錄製 ════════════════════════════

    def toggle_record(self):
        if self.player.playing: return
        self._stop_record() if self.recorder.recording else self._start_record()

    def toggle_pause(self):
        if not self.recorder.recording: return
        paused = self.recorder.toggle_pause()
        if paused:
            self.rec_btn.config(text="▶  繼續錄製", bg=YELLOW)
            self._set_status(f"錄製已暫停（按 {self.hotkey_pause} 繼續）", SUBTEXT)
        else:
            self.rec_btn.config(text="⏹  停止錄製", bg="#c0392b")
            self._set_status("錄製中…", PINK)

    def _start_record(self):
        self.recorder.record_clicks = self.record_clicks.get()
        self.recorder.record_moves = self.record_moves.get()
        self.recorder.record_scroll = self.record_scroll.get()
        self.recorder.record_keyboard = self.record_keyboard.get()
        self.recorder.ignored_keys = {self.hotkey_rec, self.hotkey_pause, self.hotkey_play, self.hotkey_stop}

        self.events = []
        self.event_list.delete(0, "end")
        self.count_lbl.config(text="共 0 個動作")
        self._set_status("錄製中…", PINK)
        self.rec_btn.config(text="⏹  停止錄製", bg="#c0392b")
        self.play_btn.config(state="disabled")
        self.recorder.start()

    def _on_event_recorded(self, ev):
        # 由監聽執行緒呼叫，須切回主執行緒更新畫面
        self.root.after(0, lambda: self._append_recorded_row(ev))

    def _append_recorded_row(self, ev):
        self.events.append(ev)
        self.event_list.insert("end", eng.format_event_label(ev))
        self.event_list.yview("end")
        self.count_lbl.config(text=f"共 {len(self.events)} 個動作")

    def _stop_record(self):
        self.recorder.stop()
        self.rec_btn.config(text="⏺  開始錄製", bg=PINK)
        self.play_btn.config(state="normal")
        self._auto_save()

    # ════════════════════════════ 播放 ════════════════════════════

    def toggle_play(self):
        if self.recorder.recording: return
        self._stop_play() if self.player.playing else self._start_play()

    def _start_play(self):
        if not self.events:
            messagebox.showinfo("第二滑鼠", "尚未錄製任何動作！")
            return
        total = 0 if self.loop_infinite.get() else self.loop_count.get()
        speed = self.play_speed.get()
        interval = self.interval_sec.get()
        if self.player.play(self.events, total, speed, interval):
            self._set_status("執行中…", GREEN)
            self.play_btn.config(text="⏹  停止執行", bg="#c0392b")
            self.rec_btn.config(state="disabled")

    def _on_play_wait(self, i, total):
        self.root.after(0, lambda: self._set_status(
            f"等待間隔… (第{i}輪{'/' + str(total) if total else ''})", YELLOW))

    def _on_play_finished(self):
        self.root.after(0, self._play_done)

    def _play_done(self):
        self._set_status("執行完畢", YELLOW)
        self.play_btn.config(text="▶  執行", bg=GREEN)
        self.rec_btn.config(state="normal")

    def _stop_play(self):
        self.player.stop()

    # ════════════════════════════ 定時啟動（排程） ════════════════════════════

    def _start_schedule(self):
        sel = self.save_list.curselection()
        if not sel:
            messagebox.showinfo("定時啟動", "請先在下方「存檔記錄」點選要到時間啟動的腳本！")
            return
        self._scheduled_save_filename = self._files[sel[0]]
        try:
            hour = int(self.schedule_hour.get())
            minute = int(self.schedule_minute.get())
        except ValueError:
            messagebox.showwarning("定時啟動", "時間格式錯誤，請輸入 0-23 時、0-59 分。")
            return
        target = self.scheduler.start(hour, minute)
        self.schedule_status_lbl.config(
            text=f"排程於 {target.strftime('%Y/%m/%d %H:%M')} 執行「{self._scheduled_save_filename}」", fg=BLUE)
        self.schedule_start_btn.config(state="disabled")
        self.schedule_cancel_btn.config(state="normal")

    def _cancel_schedule(self):
        self.scheduler.cancel()

    def _on_schedule_tick(self, remaining):
        h = int(remaining // 3600)
        m = int((remaining % 3600) // 60)
        s = int(remaining % 60)
        self.root.after(0, lambda: self.schedule_status_lbl.config(
            text=f"倒數 {h:02d}:{m:02d}:{s:02d}", fg=BLUE))

    def _on_schedule_trigger(self):
        self.root.after(0, self._fire_schedule)

    def _fire_schedule(self):
        self.schedule_start_btn.config(state="normal")
        self.schedule_cancel_btn.config(state="disabled")
        fname = self._scheduled_save_filename
        if not fname:
            self.schedule_status_lbl.config(text="排程失敗：找不到選取的腳本", fg=PINK)
            return
        try:
            scheduled_events = eng.load_events(os.path.join(eng.SAVE_DIR, fname))
        except Exception as e:
            messagebox.showerror("啟動失敗", f"讀取「{fname}」失敗：{e}")
            self.schedule_status_lbl.config(text="啟動失敗", fg=PINK)
            return
        total = 0 if self.loop_infinite.get() else self.loop_count.get()
        speed = self.play_speed.get()
        interval = self.interval_sec.get()
        if self.player.play(scheduled_events, total, speed, interval):
            self.schedule_status_lbl.config(text=f"⏱ 時間到，開始執行「{fname}」", fg=GREEN)
            self._set_status("執行中…", GREEN)
            self.play_btn.config(text="⏹  停止執行", bg="#c0392b")
            self.rec_btn.config(state="disabled")
        else:
            self.schedule_status_lbl.config(text="無法啟動（可能正在錄製或播放中）", fg=PINK)

    def _on_schedule_cancel(self):
        self.root.after(0, lambda: (
            self.schedule_status_lbl.config(text="已取消排程", fg=SUBTEXT),
            self.schedule_start_btn.config(state="normal"),
            self.schedule_cancel_btn.config(state="disabled"),
        ))

    # ════════════════════════════ 動作編輯器 ════════════════════════════

    def _refresh_event_list(self):
        self.event_list.delete(0, "end")
        for ev in self.events:
            self.event_list.insert("end", eng.format_event_label(ev))
        self.count_lbl.config(text=f"共 {len(self.events)} 個動作")

    def _add_new_event(self):
        self._open_event_editor(index=None)

    def _edit_selected_event(self):
        sel = self.event_list.curselection()
        if not sel:
            messagebox.showinfo("編輯動作", "請先在清單中點選一個動作！")
            return
        self._open_event_editor(index=sel[0])

    def _delete_selected_event(self):
        sel = self.event_list.curselection()
        if not sel:
            messagebox.showinfo("刪除動作", "請先在清單中點選一個動作！")
            return
        del self.events[sel[0]]
        self._refresh_event_list()

    def _move_selected_event(self, direction):
        sel = self.event_list.curselection()
        if not sel: return
        i = sel[0]
        j = i + direction
        if j < 0 or j >= len(self.events): return
        self.events[i], self.events[j] = self.events[j], self.events[i]
        self._refresh_event_list()
        self.event_list.selection_set(j)

    def _open_event_editor(self, index=None):
        """開啟編輯視窗：index=None 表示新增，否則編輯 self.events[index]"""
        editing = index is not None
        ev = dict(self.events[index]) if editing else {
            "type": "move", "x": 0, "y": 0, "delay": 0.5,
            "btn": "left", "pressed": True, "dx": 0, "dy": 0, "key": "",
        }

        win = tk.Toplevel(self.root)
        win.title("編輯動作" if editing else "新增動作")
        win.configure(bg=SURFACE)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        pad = {"padx": 12, "pady": 6}
        row = 0

        type_var = tk.StringVar(value=ev.get("type", "move"))
        x_var = tk.IntVar(value=ev.get("x", 0))
        y_var = tk.IntVar(value=ev.get("y", 0))
        delay_var = tk.DoubleVar(value=ev.get("delay", 0.0))
        btn_var = tk.StringVar(value=ev.get("btn", "left").replace("Button.", "") or "left")
        pressed_var = tk.BooleanVar(value=bool(ev.get("pressed", True)))
        dx_var = tk.IntVar(value=ev.get("dx", 0))
        dy_var = tk.IntVar(value=ev.get("dy", 0))
        key_var = tk.StringVar(value=ev.get("key", ""))

        def field_row(label_text):
            nonlocal row
            f = tk.Frame(win, bg=SURFACE)
            f.grid(row=row, column=0, columnspan=2, sticky="w", **pad)
            tk.Label(f, text=label_text, font=FB, bg=SURFACE, fg=TEXT, width=10, anchor="w").pack(side="left")
            row += 1
            return f

        type_frame = field_row("類型")
        type_menu = ttk.Combobox(type_frame, textvariable=type_var, values=eng.EVENT_TYPES,
                                  state="readonly", width=10)
        type_menu.pack(side="left")

        delay_frame = field_row("延遲(秒)")
        tk.Spinbox(delay_frame, from_=0, to=999, increment=0.05, textvariable=delay_var,
                   width=8, bg=ACCENT, fg=TEXT, buttonbackground=ACCENT,
                   insertbackground=TEXT, relief="flat", font=FM, format="%.3f").pack(side="left")
        tk.Label(delay_frame, text="與上一個動作間隔的秒數", font=FS, bg=SURFACE, fg=SUBTEXT).pack(side="left", padx=6)

        xy_frame = field_row("座標 X, Y")
        tk.Entry(xy_frame, textvariable=x_var, width=7, font=FM, bg=ACCENT, fg=TEXT,
                  insertbackground=TEXT, relief="flat").pack(side="left")
        tk.Entry(xy_frame, textvariable=y_var, width=7, font=FM, bg=ACCENT, fg=TEXT,
                  insertbackground=TEXT, relief="flat").pack(side="left", padx=4)

        btn_frame = field_row("滑鼠按鈕")
        btn_menu = ttk.Combobox(btn_frame, textvariable=btn_var, values=eng.MOUSE_BUTTONS,
                                 state="readonly", width=10)
        btn_menu.pack(side="left")

        scroll_frame = field_row("捲動 dx, dy")
        tk.Entry(scroll_frame, textvariable=dx_var, width=7, font=FM, bg=ACCENT, fg=TEXT,
                  insertbackground=TEXT, relief="flat").pack(side="left")
        tk.Entry(scroll_frame, textvariable=dy_var, width=7, font=FM, bg=ACCENT, fg=TEXT,
                  insertbackground=TEXT, relief="flat").pack(side="left", padx=4)

        key_frame = field_row("按鍵")
        tk.Entry(key_frame, textvariable=key_var, width=14, font=FM, bg=ACCENT, fg=TEXT,
                  insertbackground=TEXT, relief="flat").pack(side="left")
        tk.Label(key_frame, text="例：a 或 Key.ctrl_l", font=FS, bg=SURFACE, fg=SUBTEXT).pack(side="left", padx=6)

        pressed_frame = field_row("狀態")
        tk.Checkbutton(pressed_frame, text="按下（取消勾選＝放開）", variable=pressed_var, font=FS,
                        bg=SURFACE, fg=TEXT, activebackground=SURFACE, activeforeground=TEXT,
                        selectcolor=ACCENT, relief="flat").pack(side="left")

        def refresh_visible_fields(*_):
            kind = type_var.get()
            xy_frame.grid_remove(); btn_frame.grid_remove()
            scroll_frame.grid_remove(); key_frame.grid_remove()
            if kind in ("move", "click", "scroll"):
                xy_frame.grid()
            if kind == "click":
                btn_frame.grid()
            if kind == "scroll":
                scroll_frame.grid()
            if kind == "key":
                key_frame.grid()

        type_var.trace_add("write", refresh_visible_fields)
        refresh_visible_fields()

        def on_save():
            kind = type_var.get()
            new_ev = {"type": kind, "delay": round(max(0.0, delay_var.get()), 4)}
            if kind in ("move", "click", "scroll"):
                new_ev["x"] = x_var.get()
                new_ev["y"] = y_var.get()
            else:
                new_ev["x"] = 0
                new_ev["y"] = 0
            if kind == "click":
                new_ev["btn"] = btn_var.get()
                new_ev["pressed"] = pressed_var.get()
            if kind == "scroll":
                new_ev["dx"] = dx_var.get()
                new_ev["dy"] = dy_var.get()
            if kind == "key":
                if not key_var.get().strip():
                    messagebox.showwarning("編輯動作", "請輸入按鍵名稱！", parent=win)
                    return
                new_ev["key"] = key_var.get().strip()
                new_ev["pressed"] = pressed_var.get()

            if editing:
                self.events[index] = new_ev
            else:
                insert_at = (index if index is not None else len(self.events))
                self.events.append(new_ev)
            self._refresh_event_list()
            win.destroy()

        btn_row = tk.Frame(win, bg=SURFACE)
        btn_row.grid(row=row, column=0, columnspan=2, pady=12)
        tk.Button(btn_row, text="儲存", font=FBT, bg=GREEN, fg="white", relief="flat",
                  cursor="hand2", padx=14, pady=4, command=on_save).pack(side="left", padx=6)
        tk.Button(btn_row, text="取消", font=FBT, bg=BORDER, fg=TEXT, relief="flat",
                  cursor="hand2", padx=14, pady=4, command=win.destroy).pack(side="left", padx=6)

    def _open_script_editor(self):
        """開啟原始碼編輯視窗：以 JSON 文字顯示目前腳本的所有動作，可直接編輯後存回"""
        win = tk.Toplevel(self.root)
        win.title("編輯腳本原始碼")
        win.configure(bg=SURFACE)
        win.geometry("560x600")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="直接編輯下方 JSON 內容，儲存後會取代目前的動作清單",
                 font=FS, bg=SURFACE, fg=SUBTEXT).pack(anchor="w", padx=12, pady=(10, 4))

        text_frame = tk.Frame(win, bg=SURFACE)
        text_frame.pack(fill="both", expand=True, padx=12, pady=4)
        scroll = tk.Scrollbar(text_frame)
        scroll.pack(side="right", fill="y")
        text = tk.Text(text_frame, font=FM, bg=ACCENT, fg=TEXT, insertbackground=TEXT,
                        relief="flat", wrap="none", undo=True, yscrollcommand=scroll.set)
        text.pack(fill="both", expand=True)
        scroll.config(command=text.yview)

        text.insert("1.0", json.dumps(self.events, ensure_ascii=False, indent=2))

        def on_save():
            raw = text.get("1.0", "end-1c")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                messagebox.showerror("格式錯誤", f"JSON 解析失敗：{e}", parent=win)
                return
            if not isinstance(parsed, list) or not all(isinstance(ev, dict) and "type" in ev for ev in parsed):
                messagebox.showerror("格式錯誤", "內容必須是一個陣列，且每個動作都要有 \"type\" 欄位。", parent=win)
                return
            self.events = parsed
            self._refresh_event_list()
            win.destroy()

        btn_row = tk.Frame(win, bg=SURFACE)
        btn_row.pack(fill="x", padx=12, pady=10)
        tk.Button(btn_row, text="儲存", font=FBT, bg=GREEN, fg="white", relief="flat",
                  cursor="hand2", padx=14, pady=4, command=on_save).pack(side="left", padx=6)
        tk.Button(btn_row, text="取消", font=FBT, bg=BORDER, fg=TEXT, relief="flat",
                  cursor="hand2", padx=14, pady=4, command=win.destroy).pack(side="left", padx=6)

    # ════════════════════════════ 存檔 ════════════════════════════

    def _auto_save(self):
        if not self.events:
            self._set_status("錄製完成（無動作）", SUBTEXT)
            return
        path = eng.save_events(self.events)
        self._set_status(f"✅ 已自動存檔：{os.path.basename(path)}", GREEN)
        self.count_lbl.config(text=f"共 {len(self.events)} 個動作")
        self._refresh_save_list()

    def _refresh_save_list(self):
        self.save_list.delete(0, "end")
        files = eng.list_saves()
        for f in files:
            path = os.path.join(eng.SAVE_DIR, f)
            try:
                count = len(eng.load_events(path))
            except Exception:
                count = "?"
            try:
                dt = datetime.strptime(f, "rec_%Y%m%d_%H%M%S.json")
                label = f"  {dt.strftime('%Y/%m/%d  %H:%M:%S')}    {count} 個動作"
            except Exception:
                label = f"  {f}   {count} 個動作"
            self.save_list.insert("end", label)
        self._files = files
        self.save_count_lbl.config(text=f"共 {len(files)} 個存檔")

    def _load_selected_save(self, event=None):
        sel = self.save_list.curselection()
        if not sel:
            messagebox.showinfo("提示", "請先點選一個存檔！")
            return
        fname = self._files[sel[0]]
        self.events = eng.load_events(os.path.join(eng.SAVE_DIR, fname))
        self._refresh_event_list()
        self._set_status(f"✅ 已載入：{fname}", BLUE)

    def _rename_selected_save(self):
        sel = self.save_list.curselection()
        if not sel:
            messagebox.showinfo("提示", "請先點選一個存檔！")
            return
        fname = self._files[sel[0]]
        default_name = fname[:-5] if fname.lower().endswith(".json") else fname
        new_name = simpledialog.askstring("重新命名", "輸入新的腳本名稱：",
                                           initialvalue=default_name, parent=self.root)
        if not new_name:
            return
        try:
            eng.rename_save(fname, new_name)
        except Exception as e:
            messagebox.showerror("重新命名失敗", str(e))
            return
        self._refresh_save_list()

    def _delete_selected_save(self):
        sel = self.save_list.curselection()
        if not sel:
            messagebox.showinfo("提示", "請先點選一個存檔！")
            return
        fname = self._files[sel[0]]
        if messagebox.askyesno("刪除", f"確定刪除存檔？\n{fname}"):
            eng.delete_save(fname)
            self._refresh_save_list()

    # ════════════════════════════ 工具列 ════════════════════════════

    def clear_events(self):
        if messagebox.askyesno("清除", "確定要清除目前動作？（不影響存檔）"):
            self.events = []
            self._refresh_event_list()
            self._set_status("待機中", SUBTEXT)

    def export_events(self):
        if not self.events:
            messagebox.showinfo("匯出", "沒有可匯出的動作！"); return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON 檔案", "*.json")], title="另存新檔")
        if path:
            eng.save_events(self.events, path)
            messagebox.showinfo("匯出", f"已儲存至\n{path}")

    def import_events(self):
        path = filedialog.askopenfilename(filetypes=[("JSON 檔案", "*.json")], title="開啟錄製檔案")
        if path:
            self.events = eng.load_events(path)
            self._refresh_event_list()
            self._set_status(f"已載入 {len(self.events)} 個動作", YELLOW)

    # ════════════════════════════ 工具 ════════════════════════════

    def _set_status(self, text, color):
        self.status_lbl.config(text=text, fg=color)
        self.status_dot.config(fg=color)

    def _toggle_infinite(self):
        self.loop_spin.config(state="disabled" if self.loop_infinite.get() else "normal")

    def _start_hotkey_listener(self):
        def on_press(key):
            if getattr(self, "_rebind_active", None):
                return
            if key == eng.key_to_pynput(self.hotkey_rec):
                self.root.after(0, self.toggle_record)
            elif key == eng.key_to_pynput(self.hotkey_pause):
                if self.recorder.recording: self.root.after(0, self.toggle_pause)
            elif key == eng.key_to_pynput(self.hotkey_play):
                self.root.after(0, self.toggle_play)
            elif key == eng.key_to_pynput(self.hotkey_stop):
                if self.recorder.recording: self.root.after(0, self._stop_record)
                if self.player.playing: self.root.after(0, self._stop_play)
        self.kb_listener = keyboard.Listener(on_press=on_press)
        self.kb_listener.daemon = True
        self.kb_listener.start()

    def _save_config(self):
        cfg = {
            "loop_count": self.loop_count.get(), "loop_infinite": self.loop_infinite.get(),
            "play_speed": self.play_speed.get(), "interval_sec": self.interval_sec.get(),
            "record_clicks": self.record_clicks.get(), "record_moves": self.record_moves.get(),
            "record_scroll": self.record_scroll.get(), "record_keyboard": self.record_keyboard.get(),
            "always_on_top": self.always_on_top.get(),
            "hotkey_rec": self.hotkey_rec, "hotkey_pause": self.hotkey_pause,
            "hotkey_play": self.hotkey_play, "hotkey_stop": self.hotkey_stop,
            "schedule_hour": self.schedule_hour.get(), "schedule_minute": self.schedule_minute.get(),
        }
        eng.save_config(cfg)

    def _load_config(self):
        cfg = eng.load_config()
        self.loop_count.set(cfg.get("loop_count", 1))
        self.loop_infinite.set(cfg.get("loop_infinite", False))
        self.play_speed.set(cfg.get("play_speed", 1.0))
        self.interval_sec.set(cfg.get("interval_sec", 0.0))
        self.record_clicks.set(cfg.get("record_clicks", True))
        self.record_moves.set(cfg.get("record_moves", True))
        self.record_scroll.set(cfg.get("record_scroll", True))
        self.record_keyboard.set(cfg.get("record_keyboard", True))
        self.always_on_top.set(cfg.get("always_on_top", False))
        self.hotkey_rec = cfg.get("hotkey_rec", self.hotkey_rec)
        self.hotkey_pause = cfg.get("hotkey_pause", self.hotkey_pause)
        self.hotkey_play = cfg.get("hotkey_play", self.hotkey_play)
        self.hotkey_stop = cfg.get("hotkey_stop", self.hotkey_stop)
        self.schedule_hour.set(str(cfg.get("schedule_hour", "09")).zfill(2))
        self.schedule_minute.set(str(cfg.get("schedule_minute", "00")).zfill(2))

    def _on_close(self):
        self._save_config()
        self.scheduler.cancel()
        self.player.stop()
        if self.recorder.recording:
            self.recorder.stop()
        if getattr(self, "kb_listener", None):
            self.kb_listener.stop()
        if getattr(self, "_rebind_kb_listener", None):
            try: self._rebind_kb_listener.stop()
            except Exception: pass
        if getattr(self, "_rebind_mouse_listener", None):
            try: self._rebind_mouse_listener.stop()
            except Exception: pass
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