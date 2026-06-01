# Far Far West Memory Editor

A modern GUI tool for editing in-game memory values in **Far Far West** — no Cheat Engine knowledge required.

[![Website](https://img.shields.io/badge/Website-Visit-blue?style=for-the-badge)](https://jlaiii.github.io/far-far-west-memory-editor/)
[![Download](https://img.shields.io/badge/Download-Latest-green?style=for-the-badge)](https://github.com/jlaiii/far-far-west-memory-editor/releases/latest)

---

## Features

- **Auto-Connect** — Detects the game process automatically within seconds. No manual attaching required.
- **Live Value Display** — See Gold and Souls update in real-time.
- **One-Click Presets** — Set values instantly with preset buttons (100, 1K, 10K, 50K, 100K, 500K, 999K, 9.9M, 999M).
- **Freeze Values** — Lock any value so the game cannot change it while you play.
- **Safety Limits** — Values are clamped to 0–999,999,999 to prevent game crashes from overflow.
- **Tabbed Interface** — Clean Editor tab for gameplay, Log tab for diagnostics.
- **Update-Ready** — All pointer chains stored in JSON config; easy to update after game patches without touching code.
- **Silent Launch** — Uses `pythonw.exe` via `run.vbs` for zero console window.

---

## Quick Start

### Portable (Recommended)

1. Download the latest release from [Releases](https://github.com/jlaiii/far-far-west-memory-editor/releases/latest)
2. Extract to any folder
3. Double-click `run.vbs` (or `editor.pyw`)
4. Launch Far Far West — the editor connects automatically

### From Source

```bash
git clone https://github.com/jlaiii/far-far-west-memory-editor.git
cd far-far-west-memory-editor
pip install pymem customtkinter psutil
pythonw editor.pyw
```

---

## How It Works

The editor reads and writes memory values in the game process using pointer chains resolved via `pymem`. Each value (Gold, Souls) follows a multi-step pointer path from a static module base offset through several dereferences to the final value address:

```
module.exe + base_offset  ->  +offset1  ->  +offset2  ->  ...  ->  final value
```

All configuration lives in `config.json` — add more values, change presets, or update pointers after game patches without modifying code.

---

## Configuration

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
    },
    {
      "name": "Souls",
      "base_offset": "0x08E30368",
      "offsets": ["0x98", "0xD8", "0x0", "0x228", "0x3B8", "0x14"],
      "value_type": "int32",
      "min_value": 0,
      "max_value": 999999999,
      "presets": [100, 1000, 10000, 50000, 100000, 500000, 999999, 9999999, 999999999]
    }
  ]
}
```

Supported value types: `int32`, `int64`, `float`, `double`, `bytes2`, `bytes1`.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| [pymem](https://pypi.org/project/Pymem/) | >= 1.13 | Windows process memory read/write |
| [customtkinter](https://pypi.org/project/customtkinter/) | >= 5.2 | Modern dark-themed GUI toolkit |
| [psutil](https://pypi.org/project/psutil/) | >= 5.9 | Process detection and monitoring |

All installable via pip:

```bash
pip install pymem customtkinter psutil
```

---

## Disclaimer

This tool is for educational purposes only. Modifying game memory may violate the game's Terms of Service. Use at your own risk.

---

## License

MIT — see [LICENSE](LICENSE)

---

**Website:** [jlaiii.github.io/far-far-west-memory-editor](https://jlaiii.github.io/far-far-west-memory-editor/)  
**Author:** [jlaiii](https://github.com/jlaiii)
