# 第二滑鼠 (Second Mouse)

一款類似按鍵精靈的滑鼠/鍵盤動作錄製與自動播放工具，使用 Python + tkinter 製作，支援全域熱鍵控制，即使切換到其他視窗也能正常運作。

## ✨ 功能特色

- **錄製** 滑鼠移動、點擊、滾輪與鍵盤輸入
- **播放** 完整重現錄製的動作序列
- **全域熱鍵** 錄製/暫停錄製/執行/停止，切換視窗後仍有效
- **熱鍵自訂** 點擊即可重新綁定，支援 F1–F12 及功能鍵，ESC 或點擊其他地方取消
- **自動存檔** 停止錄製後自動儲存至 `recordings/` 資料夾，並在程式內直接瀏覽、載入、刪除
- **播放速度** 支援滑桿拖曳或直接輸入數值（0.05×–20×）
- **重複播放** 指定次數或無限循環，每輪可設定間隔秒數
- **暫停錄製** 錄製途中可隨時暫停，不記錄該段期間的動作
- **視窗置頂** 可切換，執行時關閉置頂避免擋到要操作的畫面
- **設定記憶** 所有設定（含熱鍵、語言）關閉後自動儲存，下次開啟繼承
- **多語言介面** 繁體中文 / English / 简体中文 / 日本語 / 한국어

## 🖥️ 系統需求

- Python 3.8+（已在 Python 3.14 測試）
- Windows（全域熱鍵與滑鼠控制依賴 pynput，建議以系統管理員身分執行）

## 📦 安裝依賴

```bash
pip install pynput pyautogui
```

## 🚀 啟動方式

```bash
python 第二滑鼠.py
```

## ⌨️ 預設熱鍵

| 熱鍵 | 功能 |
|------|------|
| F8 | 暫停 / 繼續錄製 |
| F9 | 開始 / 停止錄製 |
| F10 | 開始執行 |
| F12 | 強制停止（錄製或播放） |

> 所有熱鍵均可在程式內點擊重新綁定

## 📁 檔案結構

```
第二滑鼠.py        # 主程式
recordings/        # 自動存檔資料夾（自動建立）
config.json        # 設定檔（自動建立）
```

## 📝 存檔格式

錄製結果以 JSON 儲存，可手動編輯或跨裝置移植：

```json
[
  { "type": "move",  "x": 512, "y": 300, "delay": 0.05 },
  { "type": "click", "x": 512, "y": 300, "btn": "Button.left", "pressed": true, "delay": 0.1 },
  { "type": "key",   "key": "a", "pressed": true, "delay": 0.08 }
]
```

# Second Mouse
A mouse/keyboard macro recorder and auto-playback tool similar to AutoHotkey or Mouse Recorder, built with Python + tkinter. Global hotkeys keep working even when the window is out of focus.
## ✨ Features
- **Record** mouse movements, clicks, scroll wheel, and keyboard input
- **Playback** full reproduction of recorded action sequences
- **Global hotkeys** for record/pause/play/stop — work even when another window is focused
- **Rebindable hotkeys** — click any hotkey button to reassign it; press ESC or click elsewhere to cancel
- **Auto-save** — recordings are automatically saved to the `recordings/` folder on stop, and can be browsed, loaded, or deleted directly within the app
- **Playback speed** — drag the slider or type a value directly (0.05×–20×)
- **Loop control** — set a repeat count or loop infinitely, with optional delay between runs
- **Pause recording** — pause and resume mid-recording without capturing the gap
- **Always-on-top toggle** — disable it when you need to click through to another window
- **Persistent settings** — all settings including hotkeys and language are saved on close and restored on next launch
- **Multi-language UI** — English / 繁體中文 / 简体中文 / 日本語 / 한국어

## 🖥️ Requirements

- Python 3.8+ (tested on Python 3.14)
- Windows (global hotkeys and mouse control rely on pynput; run as Administrator if hotkeys don't respond)

## 📦 Install Dependencies

```bash
pip install pynput pyautogui
```

## 🚀 Run

```bash
python second_mouse.py
```

## ⌨️ Default Hotkeys

| Hotkey | Action |
|--------|--------|
| F8 | Pause / Resume recording |
| F9 | Start / Stop recording |
| F10 | Start playback |
| F12 | Force stop (recording or playback) |

> All hotkeys can be rebound inside the app

## 📁 File Structure

```
second_mouse.py    # Main script
recordings/        # Auto-save folder (created automatically)
config.json        # Settings file (created automatically)
```

## 💾 Save Format

Recordings are stored as plain JSON — easy to inspect, edit, or share across machines:

```json
[
  { "type": "move",   "x": 512, "y": 300, "delay": 0.05 },
  { "type": "click",  "x": 512, "y": 300, "btn": "Button.left", "pressed": true,  "delay": 0.1  },
  { "type": "scroll", "x": 512, "y": 300, "dx": 0, "dy": -3,    "delay": 0.2  },
  { "type": "key",    "key": "a",          "pressed": true,       "delay": 0.08 }
]
```
## 📄 License

MIT



