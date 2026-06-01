# 🎮 Far Far West - Memory Editor

> A modern, user-friendly GUI tool for editing in-game memory values in **Far Far West** — no Cheat Engine knowledge required.

[![Website](https://img.shields.io/badge/🌐_Website-Visit-blue?style=for-the-badge)](https://jlaiii.github.io/far-far-west-memory-editor/)
[![Download](https://img.shields.io/badge/⬇️_Download-Latest-green?style=for-the-badge)](https://github.com/jlaiii/far-far-west-memory-editor/releases/latest)

---

## ✨ Features

- **🟢 Auto-Connect** — Detects the game automatically. No manual attaching needed.
- **📊 Live Value Display** — See your Gold and Souls update in real-time.
- **⚡ One-Click Presets** — Set values instantly with preset buttons (100, 1K, 10K, 50K, 100K, 500K, 999K, 9.9M, 999M).
- **🔒 Freeze Values** — Lock any value so the game can't change it.
- **🛡️ Safety Limits** — Values are clamped to 0–999,999,999 to prevent game crashes.
- **📋 Log Tab** — Built-in debug log for troubleshooting.
- **🎯 Update-Ready** — Pointer chains in JSON config; easy to update after game patches.
- **🖥️ No Console** — Clean GUI only. No terminal windows.

---

## 🚀 Quick Start

### Option 1: Portable (Recommended)

1. **Download** the latest release ZIP from [Releases](https://github.com/jlaiii/far-far-west-memory-editor/releases/latest)
2. **Extract** to any folder
3. **Double-click `run.vbs`** (or `editor.pyw`)
4. **Launch Far Far West** — the editor connects automatically!

### Option 2: From Source

```bash
# Clone the repo
git clone https://github.com/jlaiii/far-far-west-memory-editor.git
cd far-far-west-memory-editor

# Install dependencies
pip install pymem customtkinter psutil

# Run
pythonw editor.pyw
```

---

## 📸 Screenshots

| Connected | Log View |
|-----------|----------|
| Editor showing Gold & Souls values | Debug log with pointer chain info |

---

## 🧩 How It Works

The editor reads and writes memory values in the game process using pointer chains resolved from Cheat Engine. Each value (Gold, Souls) follows a multi-step pointer path:

```
module.exe + base_offset → +offset1 → +offset2 → ... → final_value
```

All configuration is stored in `config.json` — add more values, change presets, or update pointers after game patches without touching code.

---

## 🛠️ Configuration

`config.json`:

```json
{
  "game": {
    "process_name": "FarFarWest-Win64-Shipping.exe",
    "module_name": "FarFarWest-Win64-Shipping.exe",
    "window_title": "Far Far West"
  },
  "pointers": [
    {
      "name": "Gold",
      "base_offset": "0x08E30368",
      "offsets": ["0x98", "0xD8", "0x0", "0x228", "0x3B8", "0x8"],
      "value_type": "int32",
      "min_value": 0,
      "max_value": 999999999,
      "presets": [100, 1000, 10000, 50000, 100000, 500000, 999999, 9999999, 999999999]
    }
  ]
}
```

---

## 📦 Dependencies

| Package | Purpose |
|---------|---------|
| [pymem](https://pypi.org/project/Pymem/) | Windows memory read/write |
| [customtkinter](https://pypi.org/project/customtkinter/) | Modern GUI toolkit |
| [psutil](https://pypi.org/project/psutil/) | Process detection |

---

## ⚠️ Disclaimer

This tool is for **educational purposes only**. Modifying game memory may violate the game's Terms of Service. Use at your own risk.

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

🌐 **Website:** [jlaiii.github.io/far-far-west-memory-editor](https://jlaiii.github.io/far-far-west-memory-editor/)
