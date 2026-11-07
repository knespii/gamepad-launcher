#!/usr/bin/env python3
"""Gamepad launcher: press the controller's Home button to pick Steam or Heroic.

Reads gamepads straight from /dev/input (user must be in the 'input' group),
shows a fullscreen GTK menu and launches the chosen app in Big Picture /
fullscreen mode. No extra Python packages needed.
"""
import fcntl
import glob
import os
import struct
import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk  # noqa: E402

# --- Launchers -----------------------------------------------------------
ENTRIES = [
    {
        "name": "Steam",
        "icon": "steam",
        "cmd": ["steam", "-bigpicture"],
    },
    {
        "name": "Heroic",
        "icon": "com.heroicgameslauncher.hgl",
        "cmd": ["flatpak", "run", "com.heroicgameslauncher.hgl", "--fullscreen"],
    },
    {
        "name": "Vypnout",
        "icon": "system-shutdown",
        "cmd": ["systemctl", "poweroff"],
        "confirm": "Opravdu vypnout?",
    },
]

# --- evdev constants -----------------------------------------------------
EV_KEY, EV_ABS = 0x01, 0x03
BTN_SOUTH, BTN_EAST, BTN_MODE, BTN_START = 304, 305, 316, 315
ABS_X, ABS_HAT0X = 0x00, 0x10
EVENT = struct.Struct("llHHi")  # timeval, type, code, value


def eviocgabs(axis):
    # _IOR('E', 0x40 + axis, struct input_absinfo) ; absinfo = 6 x int32
    return (2 << 30) | (24 << 16) | (ord("E") << 8) | (0x40 + axis)


def has_key(event_name, code):
    try:
        words = open(f"/sys/class/input/{event_name}/device/capabilities/key").read().split()
    except OSError:
        return False
    bits = int("".join(w.rjust(16, "0") for w in words), 16)
    return bool(bits >> code & 1)


class Gamepad:
    def __init__(self, path):
        self.path = path
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        self.stick_center, self.stick_dead = 0, 1
        try:
            buf = fcntl.ioctl(self.fd, eviocgabs(ABS_X), bytes(24))
            _, lo, hi, *_ = struct.unpack("6i", buf)
            self.stick_center = (lo + hi) // 2
            self.stick_dead = max(1, (hi - lo) * 35 // 100)
        except OSError:
            pass
        self.stick_dir = 0


class App:
    def __init__(self):
        self.pads = {}  # path -> (Gamepad, watch id)
        self.window = None
        self.selected = 0
        self.cards = []
        self.labels = []
        self.armed = False  # first A press on a "confirm" entry only asks
        self.scan()
        GLib.timeout_add_seconds(2, self.scan)

    # --- device handling -------------------------------------------------
    def scan(self):
        for path in glob.glob("/dev/input/event*"):
            name = os.path.basename(path)
            if path in self.pads or not (has_key(name, BTN_MODE) and has_key(name, BTN_SOUTH)):
                continue
            try:
                pad = Gamepad(path)
            except OSError:
                continue
            wid = GLib.io_add_watch(pad.fd, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, self.on_input, pad)
            self.pads[path] = (pad, wid)
            print(f"gamepad connected: {path}", flush=True)
        return True

    def drop(self, pad):
        self.pads.pop(pad.path, None)
        try:
            os.close(pad.fd)
        except OSError:
            pass
        print(f"gamepad disconnected: {pad.path}", flush=True)

    def on_input(self, fd, cond, pad):
        if cond & (GLib.IO_HUP | GLib.IO_ERR):
            self.drop(pad)
            return False
        try:
            data = os.read(fd, EVENT.size * 64)
        except BlockingIOError:
            return True
        except OSError:
            self.drop(pad)
            return False
        for i in range(0, len(data) - EVENT.size + 1, EVENT.size):
            _, _, etype, code, value = EVENT.unpack_from(data, i)
            self.handle(pad, etype, code, value)
        return True

    def handle(self, pad, etype, code, value):
        if etype == EV_KEY and value == 1:
            if code == BTN_MODE:
                self.toggle()
            elif self.window and code in (BTN_SOUTH, BTN_START):
                self.launch()
            elif self.window and code == BTN_EAST:
                self.close()
        elif etype == EV_ABS and self.window:
            if code == ABS_HAT0X and value:
                self.move(1 if value > 0 else -1)
            elif code == ABS_X:
                off = value - pad.stick_center
                d = 0 if abs(off) < pad.stick_dead else (1 if off > 0 else -1)
                if d and d != pad.stick_dir:
                    self.move(d)
                pad.stick_dir = d

    # --- menu ------------------------------------------------------------
    def toggle(self):
        if self.window:
            self.close()
        elif subprocess.run(["pgrep", "-x", "steam"], capture_output=True).returncode == 0:
            # Steam is running and handles the Home button by itself.
            pass
        else:
            self.open()

    def open(self):
        self.selected = 0
        self.armed = False
        win = Gtk.Window(title="Gamepad Launcher")
        win.set_decorated(False)
        win.set_keep_above(True)
        win.connect("key-press-event", self.on_key)
        win.connect("delete-event", lambda *_: self.close() or True)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=60)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        self.cards = []
        self.labels = []
        for i, e in enumerate(ENTRIES):
            card = Gtk.EventBox()
            card.get_style_context().add_class("card")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
            inner.set_margin_top(40)
            inner.set_margin_bottom(40)
            inner.set_margin_start(60)
            inner.set_margin_end(60)
            img = Gtk.Image.new_from_icon_name(e["icon"], Gtk.IconSize.DIALOG)
            img.set_pixel_size(160)
            label = Gtk.Label(label=e["name"])
            label.get_style_context().add_class("title")
            inner.pack_start(img, False, False, 0)
            inner.pack_start(label, False, False, 0)
            card.add(inner)
            card.connect("button-press-event", lambda _w, _e, i=i: self.select_and_launch(i))
            box.pack_start(card, False, False, 0)
            self.cards.append(card)
            self.labels.append(label)

        hint = Gtk.Label(label="◀ ▶  vybrat     A  spustit     B  zavřít")
        hint.get_style_context().add_class("hint")
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=50)
        outer.set_valign(Gtk.Align.CENTER)
        outer.pack_start(box, False, False, 0)
        outer.pack_start(hint, False, False, 0)
        win.add(outer)

        self.window = win
        self.refresh()
        win.fullscreen()
        win.show_all()
        win.present()

    def close(self):
        if self.window:
            self.window.destroy()
            self.window = None

    def move(self, d):
        self.selected = (self.selected + d) % len(ENTRIES)
        self.armed = False
        self.refresh()

    def refresh(self):
        for i, card in enumerate(self.cards):
            ctx = card.get_style_context()
            (ctx.add_class if i == self.selected else ctx.remove_class)("selected")
            armed = self.armed and i == self.selected
            (ctx.add_class if armed else ctx.remove_class)("armed")
            e = ENTRIES[i]
            self.labels[i].set_text(f"{e['confirm']} (A)" if armed else e["name"])

    def select_and_launch(self, i):
        self.selected = i
        self.launch()

    def launch(self):
        entry = ENTRIES[self.selected]
        if entry.get("confirm") and not self.armed:
            self.armed = True
            self.refresh()
            return
        self.close()
        print(f"launching {entry['name']}", flush=True)
        subprocess.Popen(entry["cmd"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def on_key(self, _w, ev):
        key = Gdk.keyval_name(ev.keyval)
        if key in ("Left", "a"):
            self.move(-1)
        elif key in ("Right", "d"):
            self.move(1)
        elif key in ("Return", "KP_Enter", "space"):
            self.launch()
        elif key == "Escape":
            self.close()
        return True


CSS = b"""
window { background-color: rgba(10, 12, 18, 0.96); }
.card { border-radius: 24px; background-color: #1e2230; border: 4px solid transparent; }
.card.selected { background-color: #2c3550; border-color: #5aa0ff; }
.card.armed { background-color: #4a1f24; border-color: #ff5a5a; }
.title { font-size: 36px; font-weight: bold; color: #e8ecf5; }
.hint { font-size: 20px; color: #8a93a8; }
"""


def main():
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    App()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
