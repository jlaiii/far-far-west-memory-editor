"""
Far Far West - Gold & Soul Editor
====================================
A Python GUI tool to read, write, and freeze Gold and Souls
in-game memory values using Cheat Engine pointer chains.

How to use:
  1. Launch the game first, then run this script.
  2. Or run this script first — it will wait for the game to appear.
  3. Click [Attach] to connect to the game process.
  4. Read / edit / freeze / apply presets.

Dependencies (all installed via pip):
  - pymem       (memory read/write via Win32 API)
  - customtkinter (modern GUI toolkit)
  - psutil      (process detection)
"""

from __future__ import annotations

import json
import struct
import threading
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk
import psutil
import webbrowser

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"

# ---------------------------------------------------------------------------
# Map value-type names to pymem read/write methods
# ---------------------------------------------------------------------------
TYPE_MAP = {
    "int32":  {"read": "read_int",     "write": "write_int",     "size": 4, "label": "4-Byte Int"},
    "int64":  {"read": "read_longlong","write": "write_longlong","size": 8, "label": "8-Byte Int"},
    "float":  {"read": "read_float",   "write": "write_float",   "size": 4, "label": "Float"},
    "double": {"read": "read_double",  "write": "write_double",  "size": 8, "label": "Double"},
    "bytes2": {"read": "read_short",   "write": "write_short",   "size": 2, "label": "2-Byte Int"},
    "bytes1": {"read": "read_char",    "write": "write_char",    "size": 1, "label": "1-Byte Int"},
}


# ---------------------------------------------------------------------------
# Memory engine
# ---------------------------------------------------------------------------

class MemoryEngine:
    """Resolves pointer chains and reads/writes memory via pymem."""

    def __init__(self, process_name: str, module_name: str) -> None:
        self.process_name = process_name
        self.module_name = module_name
        self.pm: "pymem.Pymem | None" = None
        self.module_base: int = 0
        self._lock = threading.Lock()
        self.log: Callable[[str], None] | None = None

    def _emit(self, msg: str) -> None:
        if self.log:
            self.log(msg)

    # -- process detection --------------------------------------------------

    @staticmethod
    def is_process_running(process_name: str) -> bool:
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == process_name.lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def get_process_pid(self) -> int | None:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == self.process_name.lower():
                    return proc.info["pid"]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    # -- attach / detach ----------------------------------------------------

    def attach(self) -> bool:
        import pymem
        import pymem.process

        pid = self.get_process_pid()
        if pid is None:
            return False

        try:
            self.pm = pymem.Pymem()
            self.pm.open_process_from_id(pid)
            module = pymem.process.module_from_name(
                self.pm.process_handle, self.module_name
            )
            self.module_base = module.lpBaseOfDll
            self._emit(f"Attached to {self.process_name} (PID {pid}, base {hex(self.module_base)})")
            return True
        except Exception as e:
            self._emit(f"Attach failed: {e}")
            self.pm = None
            self.module_base = 0
            return False

    def detach(self) -> None:
        if self.pm is not None:
            try:
                self.pm.close_process()
                self._emit("Detached from process.")
            except Exception:
                pass
            self.pm = None
            self.module_base = 0

    @property
    def is_attached(self) -> bool:
        return self.pm is not None and self.module_base != 0

    def is_process_alive(self) -> bool:
        """Check that the game process is still actually running."""
        if self.pm is None:
            return False
        try:
            self.pm.read_bytes(self.module_base, 1)
            return True
        except Exception:
            return False

    # -- pointer chain resolution -------------------------------------------

    def _read_ptr(self, address: int, pointer_size: int = 8) -> int:
        if pointer_size == 4:
            raw = self.pm.read_bytes(address, 4)
            return struct.unpack("<I", raw)[0]
        else:
            return self.pm.read_longlong(address)

    def resolve_address(
        self, base_offset: int, offsets: list[int], pointer_size: int = 8,
        verbose: bool = False,
    ) -> int:
        if self.pm is None:
            raise RuntimeError("Not attached to process")

        addr0 = self.module_base + base_offset
        with self._lock:
            cur = self._read_ptr(addr0, pointer_size)
            if verbose:
                self._emit(f"  [ptr] module+{hex(base_offset)} ({hex(addr0)}) -> {hex(cur)}")
            for off in offsets[:-1]:
                cur = self._read_ptr(cur + off, pointer_size)
                if verbose:
                    self._emit(f"  [ptr] +{hex(off)} -> {hex(cur)}")
            final = cur + offsets[-1]
            if verbose:
                self._emit(f"  [ptr] +{hex(offsets[-1])} = {hex(final)} (final)")
            return final

    def type_label(self, value_type: str) -> str:
        return TYPE_MAP.get(value_type, {}).get("label", value_type)

    def read_value(
        self, base_offset: int, offsets: list[int],
        value_type: str, pointer_size: int = 8, verbose: bool = False,
    ) -> int | float:
        addr = self.resolve_address(base_offset, offsets, pointer_size, verbose=verbose)
        method = TYPE_MAP[value_type]["read"]
        with self._lock:
            val = getattr(self.pm, method)(addr)
        if verbose:
            self._emit(f"  Read {self.type_label(value_type)} @ {hex(addr)} = {val}")
        return val

    def read_value_safe(
        self, base_offset: int, offsets: list[int],
        value_type: str, pointer_size: int = 8,
    ) -> int | float | None:
        try:
            return self.read_value(base_offset, offsets, value_type, pointer_size)
        except Exception:
            return None

    def write_value(
        self, base_offset: int, offsets: list[int],
        value_type: str, value: int | float, pointer_size: int = 8,
        quiet: bool = False,
    ) -> None:
        addr = self.resolve_address(base_offset, offsets, pointer_size)
        method = TYPE_MAP[value_type]["write"]
        with self._lock:
            getattr(self.pm, method)(addr, value)
        if not quiet:
            self._emit(f"  Wrote {self.type_label(value_type)} @ {hex(addr)} = {value}")


# ---------------------------------------------------------------------------
# Pointer card
# ---------------------------------------------------------------------------

class PointerCard(ctk.CTkFrame):

    def __init__(self, master, engine: MemoryEngine, pointer_cfg: dict, **kwargs) -> None:
        super().__init__(master, corner_radius=10, fg_color=("gray90", "gray17"), **kwargs)
        self.engine = engine
        self.cfg = pointer_cfg

        self.name: str = pointer_cfg["name"]
        self.base_offset: int = int(pointer_cfg["base_offset"], 16)
        self.offsets: list[int] = [int(o, 16) for o in pointer_cfg["offsets"]]
        self.value_type: str = pointer_cfg["value_type"]
        self.type_info = TYPE_MAP[self.value_type]
        self.pointer_size: int = pointer_cfg.get("pointer_size", 8)

        self._freeze_active = False
        self._freeze_value: int | float = 0
        self._freeze_thread: threading.Thread | None = None
        self._freeze_event = threading.Event()
        self._first_read_done = False

        self._build_ui()

    # -- UI -----------------------------------------------------------------

    def _build_ui(self) -> None:
        # Single compact row: [name] [value] [entry] [Set] [Freeze]
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=4, pady=2)

        ctk.CTkLabel(
            row, text=self.name, font=ctk.CTkFont(size=14, weight="bold"), width=60,
        ).pack(side="left", padx=(0, 6))

        self.value_label = ctk.CTkLabel(
            row, text="--", font=ctk.CTkFont(size=20, weight="bold"), width=100,
            text_color=("#2B7A4B", "#4ADE80"), anchor="w",
        )
        self.value_label.pack(side="left", padx=(0, 6))

        self.entry_var = ctk.StringVar()
        self.entry = ctk.CTkEntry(
            row, textvariable=self.entry_var, height=32, width=120,
            placeholder_text="amount...", font=ctk.CTkFont(size=13),
        )
        self.entry.pack(side="left", padx=(0, 4))
        self.entry.bind("<Return>", lambda _e: self.set_value())

        self.set_btn = ctk.CTkButton(
            row, text="Set", width=50, height=32, font=ctk.CTkFont(size=13),
            command=self.set_value,
        )
        self.set_btn.pack(side="left", padx=(0, 4))

        self.freeze_btn = ctk.CTkButton(
            row, text="Freeze", width=56, height=32, font=ctk.CTkFont(size=12),
            fg_color="transparent", border_width=1,
            command=self.toggle_freeze,
        )
        self.freeze_btn.pack(side="left")

        # Preset row
        presets = self.cfg.get("presets", [])
        if presets:
            preset_row = ctk.CTkFrame(self, fg_color="transparent")
            preset_row.pack(fill="x", padx=4, pady=(2, 2))
            for i, amount in enumerate(presets):
                label = self._fmt_preset(amount)
                btn = ctk.CTkButton(
                    preset_row, text=label, height=26, width=0,
                    font=ctk.CTkFont(size=12),
                    fg_color=("gray85", "gray25"),
                    text_color=("gray25", "gray85"),
                    hover_color=("#2B7A4B", "#4ADE80"),
                    command=lambda a=amount: self._apply_preset(a),
                )
                btn.pack(side="left", padx=(0 if i == 0 else 3, 0), pady=2)

    @staticmethod
    def _fmt_preset(n: int) -> str:
        if n >= 1_000_000_000:
            return f"{n // 1_000_000_000}B"
        if n >= 1_000_000:
            return f"{n // 1_000_000}M"
        if n >= 1_000:
            return f"{n // 1_000}K"
        return f"{n:,}"

    # -- actions ------------------------------------------------------------

    def _apply_preset(self, amount: int) -> None:
        lo = self.cfg.get("min_value", 0)
        hi = self.cfg.get("max_value", 999_999_999)
        if amount < lo or amount > hi:
            messagebox.showerror(
                "Unsafe preset",
                f"Preset {amount:,} is outside the safe range ({lo:,}–{hi:,}).",
            )
            return
        self.entry_var.set(str(amount))
        self.set_value()

    def refresh_value(self) -> None:
        if not self.engine.is_attached:
            self.value_label.configure(text="--", text_color="gray")
            return

        verbose = not self._first_read_done
        if verbose:
            self.engine._emit(f"--- [{self.name}] Refreshing ---")

        try:
            val = self.engine.read_value(
                self.base_offset, self.offsets, self.value_type,
                pointer_size=self.pointer_size, verbose=verbose,
            )
            self._first_read_done = True
            self.value_label.configure(
                text=str(val), text_color=("#2B7A4B", "#4ADE80"),
            )
        except Exception as e:
            self.engine._emit(f"  !! Read error: {e}")
            self.value_label.configure(text="ERR", text_color=("red", "#FF4444"))

    def _validate_value(self, raw: str) -> int | float | None:
        if raw == "":
            return None

        try:
            if self.value_type in ("float", "double"):
                value = float(raw)
            else:
                value = int(float(raw))
        except ValueError:
            messagebox.showerror("Invalid input", f"'{raw}' is not a valid number.")
            return None

        lo = self.cfg.get("min_value", 0)
        hi = self.cfg.get("max_value", 999_999_999)

        if value < lo:
            messagebox.showerror(
                "Invalid value",
                f"Value must be {lo:,} or higher.\nNegative balances are not allowed.",
            )
            return None

        if value > hi:
            messagebox.showerror(
                "Invalid value",
                f"Value must be {hi:,} or lower.\nHigher values may crash or corrupt the game.",
            )
            return None

        return value

    def set_value(self) -> None:
        if not self.engine.is_attached:
            messagebox.showwarning("Not attached", "Attach to the game process first.")
            return

        value = self._validate_value(self.entry_var.get().strip())
        if value is None:
            return

        self.engine._emit(f"--- [{self.name}] Setting value to {value} ---")
        try:
            self.engine.write_value(
                self.base_offset, self.offsets, self.value_type, value,
                pointer_size=self.pointer_size,
            )
            self.refresh_value()
        except Exception as exc:
            self.engine._emit(f"  !! Write error: {exc}")
            messagebox.showerror("Write failed", str(exc))

    def toggle_freeze(self) -> None:
        if self._freeze_active:
            self._stop_freeze()
        else:
            self._start_freeze()

    def _start_freeze(self) -> None:
        if not self.engine.is_attached:
            messagebox.showwarning("Not attached", "Attach to the game process first.")
            return

        raw = self.entry_var.get().strip()
        if raw == "":
            try:
                self._freeze_value = self.engine.read_value(
                    self.base_offset, self.offsets, self.value_type,
                    pointer_size=self.pointer_size,
                )
                lo = self.cfg.get("min_value", 0)
                hi = self.cfg.get("max_value", 999_999_999)
                if self._freeze_value < lo or self._freeze_value > hi:
                    messagebox.showerror(
                        "Unsafe value",
                        f"Current value ({self._freeze_value}) is outside the safe range ({lo:,}–{hi:,}).\n"
                        "Type a safe value in the entry box first.",
                    )
                    return
            except Exception as exc:
                messagebox.showerror("Read failed", str(exc))
                return
        else:
            value = self._validate_value(raw)
            if value is None:
                return
            self._freeze_value = value

        self._freeze_active = True
        self._freeze_event.clear()
        self.freeze_btn.configure(text="Unfreeze", fg_color=("#E53E3E", "#C53030"))
        self.engine._emit(f"--- [{self.name}] Freeze ON (value={self._freeze_value}) ---")
        self._freeze_thread = threading.Thread(target=self._freeze_loop, daemon=True)
        self._freeze_thread.start()

    def _stop_freeze(self) -> None:
        self._freeze_active = False
        self._freeze_event.set()
        self.freeze_btn.configure(text="Freeze", fg_color="transparent")
        self.engine._emit(f"--- [{self.name}] Freeze OFF ---")

    def _freeze_loop(self) -> None:
        while not self._freeze_event.is_set():
            try:
                if self.engine.is_attached:
                    self.engine.write_value(
                        self.base_offset, self.offsets,
                        self.value_type, self._freeze_value,
                        pointer_size=self.pointer_size,
                        quiet=True,  # don't flood the log
                    )
            except Exception:
                pass
            self._freeze_event.wait(0.05)

    def stop_all(self) -> None:
        if self._freeze_active:
            self._stop_freeze()


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class MemoryEditorApp(ctk.CTk):

    SCAN_INTERVAL_MS = 2000
    ANIM_INTERVAL_MS = 150  # smooth ~6.6 fps

    # ASCII-only spinner — guaranteed monospace, no Unicode glitches
    SPINNER = ["|", "/", "-", "\\"]

    def __init__(self, config: dict) -> None:
        super().__init__()

        self.config = config
        self.title(f"{config['game'].get('window_title', 'Far Far West')} - Gold & Soul Editor")
        self.geometry("560x380")
        self.minsize(440, 300)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.engine = MemoryEngine(
            config["game"]["process_name"],
            config["game"]["module_name"],
        )
        self.engine.log = self._log_line

        self.pointer_cards: list[PointerCard] = []
        self._was_ever_attached = False
        self._anim_tick = 0
        self._attach_attempts = 0
        self._refresh_count = 0
        self._start_time = datetime.now()
        self._anim_job: str | None = None   # after() job id for clean cancellation

        self._build_ui()
        self._log_line("═" * 42)
        self._log_line("  Gold & Soul Editor started")
        self._log_line(f"  Game:  {config['game']['process_name']}")
        self._log_line(f"  Module: {config['game']['module_name']}")
        self._log_line("  Waiting for game to launch...")
        self._log_line("═" * 42)
        self._start_auto_refresh()

    # -- UI -----------------------------------------------------------------

    def _build_ui(self) -> None:
        # -- Top bar --
        top = ctk.CTkFrame(self, corner_radius=6)
        top.pack(fill="x", padx=6, pady=(6, 2))

        # Fixed-width indicator so text changes never shift layout
        self.status_indicator = ctk.CTkLabel(
            top, text=" ", font=ctk.CTkFont(size=18), width=24, anchor="center",
        )
        self.status_indicator.pack(side="left", padx=(8, 4))

        self.status_label = ctk.CTkLabel(
            top, text="Scanning...", font=ctk.CTkFont(size=13), width=90, anchor="w",
        )
        self.status_label.pack(side="left")

        self.process_info = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray50"),
        )
        self.process_info.pack(side="left", padx=10)

        # -- Author bar (always visible, below status) --
        author_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        author_frame.pack(fill="x", padx=16, pady=(4, 0))

        author_link = ctk.CTkLabel(
            author_frame, text="Made by jlaiii",
            font=ctk.CTkFont(size=12, underline=True),
            text_color=("#3B82F6", "#60A5FA"), cursor="hand2",
        )
        author_link.pack(side="left")
        author_link.bind("<Button-1>", lambda _e: webbrowser.open(
            "https://jlaiii.github.io/far-far-west-memory-editor/"
        ))

        # -- Tab view --
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        self.main_tab = self.tab_view.add("Gold & Soul")
        self.log_tab = self.tab_view.add("Log")

        # -- Main tab content --
        # Waiting overlay
        self.waiting_frame = ctk.CTkFrame(self.main_tab, fg_color="transparent")

        # Use a CTkProgressBar for smooth, native animation — no text glitches
        self.waiting_title = ctk.CTkLabel(
            self.waiting_frame,
            text="Waiting for Far Far West...",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("gray55", "gray65"),
        )
        self.waiting_title.pack(pady=(18, 4))

        self.waiting_sub = ctk.CTkLabel(
            self.waiting_frame,
            text="Launch the game — editor will auto-connect.",
            font=ctk.CTkFont(size=13),
            text_color=("gray55", "gray55"),
        )
        self.waiting_sub.pack()

        self.waiting_status = ctk.CTkLabel(
            self.waiting_frame,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        )
        self.waiting_status.pack(pady=(10, 4))

        self.waiting_timer = ctk.CTkLabel(
            self.waiting_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray58"),
        )
        self.waiting_timer.pack(pady=(2, 4))

        # Smooth indeterminate progress bar instead of jittery text spinner
        self.waiting_bar = ctk.CTkProgressBar(
            self.waiting_frame,
            width=260,
            height=6,
            mode="indeterminate",
            progress_color=("#D69E2E", "#F6E05E"),
            fg_color=("gray80", "gray25"),
        )
        self.waiting_bar.pack(pady=(8, 14))
        self.waiting_bar.start()

        # Card area
        self.card_area = ctk.CTkScrollableFrame(self.main_tab, fg_color="transparent")

        for ptr_cfg in self.config.get("pointers", []):
            card = PointerCard(self.card_area, self.engine, ptr_cfg)
            card.pack(fill="x", pady=2)
            self.pointer_cards.append(card)

        # Start with waiting overlay
        self.waiting_frame.pack(fill="x", padx=4, pady=4)

        # -- Log tab content --
        self.log_text = ctk.CTkTextbox(
            self.log_tab, font=ctk.CTkFont(size=12), wrap="word",
        )
        self.log_text.pack(fill="both", expand=True, padx=2, pady=2)

    # -- log ----------------------------------------------------------------

    def _log_line(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # -- polling ------------------------------------------------------------

    def _start_auto_refresh(self) -> None:
        self._poll_and_auto_attach()
        self._refresh_all_cards()
        self._start_animation()
        self.after(self.SCAN_INTERVAL_MS, self._start_auto_refresh)

    def _poll_and_auto_attach(self) -> None:
        game_running = self.engine.is_process_running(self.engine.process_name)
        process_alive = (
            self.engine.is_process_alive() if self.engine.is_attached else False
        )

        # -- Process died — clean up -----------------------------------------
        if self.engine.is_attached and not process_alive:
            self.engine.detach()
            for card in self.pointer_cards:
                card.stop_all()
            self._show_waiting()
            self._was_ever_attached = False
            self._attach_attempts = 0
            self._log_line("WARN  Game process closed — watching for restart...")

        attached = self.engine.is_attached

        # -- Connected --------------------------------------------------------
        if attached:
            if not self._was_ever_attached:
                self._was_ever_attached = True
                self._show_cards()
                pid = self.engine.get_process_pid()
                self._log_line(f"OK    Connected — PID {pid}, base {hex(self.engine.module_base)}")
                self._log_line(f"      Reading Gold & Souls values live...")

            # Static checkmark — no jittery pulse animation
            self.status_indicator.configure(
                text="*", text_color=("#2B7A4B", "#4ADE80"),
            )
            self.status_label.configure(
                text="Live", text_color=("#2B7A4B", "#4ADE80"),
            )
            pid = self.engine.get_process_pid()
            self.process_info.configure(text=f"PID {pid}" if pid else "")

        # -- Game found, attaching -------------------------------------------
        elif game_running:
            self._attach_attempts += 1
            self.status_label.configure(
                text="Attaching", text_color=("#D69E2E", "#F6E05E"),
            )
            self.process_info.configure(text=self.engine.process_name)
            self._do_attach()

        # -- Scanning for game -----------------------------------------------
        else:
            self.status_label.configure(
                text="Scanning", text_color=("#D69E2E", "#F6E05E"),
            )
            self.process_info.configure(text=f"Looking for {self.engine.process_name}...")

    # -- animation (single loop — no competing after() chains) --------------

    def _start_animation(self) -> None:
        """Kick off the animation loop. Safe to call multiple times."""
        self._anim_tick += 1
        frame = self._anim_tick % len(self.SPINNER)

        if self.engine.is_attached:
            # Subtle blinking dot on the indicator to show "alive"
            dot = "." if (self._anim_tick % 6 < 3) else " "
            self.status_indicator.configure(
                text=dot, text_color=("#2B7A4B", "#4ADE80"),
            )
        elif self.waiting_frame.winfo_ismapped():
            # ASCII spinner in top bar — always monospace, no glitch
            self.status_indicator.configure(
                text=self.SPINNER[frame], text_color=("#D69E2E", "#F6E05E"),
            )
            self._update_waiting_status()

        # Cancel previous and reschedule — prevents callback buildup
        if self._anim_job is not None:
            self.after_cancel(self._anim_job)
        self._anim_job = self.after(self.ANIM_INTERVAL_MS, self._start_animation)

    def _update_waiting_status(self) -> None:
        """Cycle waiting detail text — no text-swapping in the spinner itself."""
        elapsed = (datetime.now() - self._start_time).seconds

        if elapsed < 10:
            detail = "Warming up..."
        elif elapsed < 30:
            detail = "Still watching for game..."
        elif elapsed < 60:
            detail = "Make sure the game is running"
        elif elapsed < 120:
            detail = "Waiting — editor will connect automatically"
        else:
            mins = elapsed // 60
            detail = f"Listening... ({mins} min elapsed — game not detected yet)"

        self.waiting_status.configure(text=detail)

        if elapsed < 60:
            self.waiting_timer.configure(text=f"elapsed: {elapsed}s")
        else:
            m, s = divmod(elapsed, 60)
            self.waiting_timer.configure(text=f"elapsed: {m}m {s}s")

    # -- card refresh -------------------------------------------------------

    def _refresh_all_cards(self) -> None:
        if not self.engine.is_attached:
            return
        self._refresh_count += 1
        for card in self.pointer_cards:
            card.refresh_value()

    # -- view switching -----------------------------------------------------

    def _show_cards(self) -> None:
        self.waiting_bar.stop()
        self.waiting_frame.pack_forget()
        self.card_area.pack(fill="both", expand=True, padx=2, pady=2)

    def _show_waiting(self) -> None:
        self.card_area.pack_forget()
        self.waiting_frame.pack(fill="x", padx=4, pady=4)
        self.waiting_bar.start()

    # -- attach / detach ----------------------------------------------------

    def _do_attach(self) -> None:
        success = self.engine.attach()
        if success:
            self._refresh_all_cards()
        else:
            # Only log on first attempt and every 5th thereafter
            if self._attach_attempts <= 1 or self._attach_attempts % 5 == 0:
                self._log_line(f"RETRY Attach attempt #{self._attach_attempts}...")

    def _do_detach(self) -> None:
        for card in self.pointer_cards:
            card.stop_all()
        self.engine.detach()
        self._show_waiting()

    # -- shutdown -----------------------------------------------------------

    def _on_close(self) -> None:
        # Clean up animation timer
        if self._anim_job is not None:
            self.after_cancel(self._anim_job)
        self._log_line("═" * 42)
        self._log_line("  Closing Gold & Soul Editor — goodbye!")
        self._log_line("═" * 42)
        for card in self.pointer_cards:
            card.stop_all()
        self.engine.detach()
        self.destroy()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as fh:
                return json.load(fh)
        except Exception:
            pass
    default = {
        "game": {
            "process_name": "FarFarWest-Win64-Shipping.exe",
            "module_name": "FarFarWest-Win64-Shipping.exe",
            "window_title": "Far Far West",
        },
        "pointers": [],
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(default, fh, indent=2)
    return default


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    config = load_config()
    app = MemoryEditorApp(config)
    app.mainloop()


if __name__ == "__main__":
    main()
