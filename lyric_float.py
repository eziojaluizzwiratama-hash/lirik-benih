import math
import ctypes
import os
import random
import sys
import threading
import time
import tkinter as tk


LYRICS_FILE = "lyrics.txt"
OFFSET = float(os.environ.get("LYRIC_OFFSET", "0"))
FONT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "FONT LAGU", "monospace-radon", "static",
    "monaspace-radon-latin-200-italic.ttf",
)

BOX_W, BOX_H = 300, 250
# Berkas 200 italic ini terdaftar di Windows sebagai "Monaspace Radon ExtraLight".
FONT = ("Monaspace Radon ExtraLight", 22, "italic")
# Palet hijau gelap dengan aksen lembut yang kontras.
BG_COLOR = "#355E3B"
FG_COLOR = "#EAE3D2"
RISE_SPEED = 75
TYPE_FRACTION = 0.8
LAST_DURATION = 3
FLOATING_SYMBOLS = ["♧", "♣", "❦", "❧", "❀", "✿", "☼"]
SYMBOL_FONT_SIZES = [15, 20, 25, 31, 36]
SYMBOL_COLORS = [
    "#A8C9A0", "#C8DDBB", "#EAE3D2", "#8FB89A",
    "#D5E6C8", "#B7D2A8", "#F0EBDD",
]
# Jeda lebih pendek membuat lebih banyak simbol terlihat bersamaan.
SYMBOL_COUNT = 20
SYMBOL_SPEED_RANGE = (18, 48)
SYMBOL_WOBBLE_AMP_RANGE = (10, 32)
SYMBOL_WOBBLE_FREQ_RANGE = (0.5, 1.5)
FRAME_INTERVAL_MS = 16
STARTUP_DELAY = 5


def load_lyrics(path):
    if not os.path.exists(path):
        print("File timing lirik belum ada:", path)
        sys.exit(1)
    data = []
    with open(path, encoding="utf-8") as file:
        for raw_line in file:
            if "|" not in raw_line:
                continue
            timestamp, text = raw_line.strip().split("|", 1)
            try:
                data.append((float(timestamp), text))
            except ValueError:
                continue
    if not data:
        print("Isi file timing lirik kosong.")
        sys.exit(1)
    return sorted(data)


LYRICS = load_lyrics(LYRICS_FILE)


class LyricCard:
    def __init__(self, parent, text, x, y, duration):
        self.win = tk.Toplevel(parent)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=BG_COLOR)
        self.win.geometry(f"{BOX_W}x{BOX_H}+{int(x)}+{int(y)}")
        self.full_text = text
        self.delay = int(max(20, min(250,
            duration * TYPE_FRACTION * 1000 / max(1, len(text)))))
        self.alive = True
        self.started_typing = False
        self.label = tk.Label(
            self.win, text="", font=FONT, bg=BG_COLOR, fg=FG_COLOR,
            wraplength=BOX_W - 25, justify="center"
        )
        self.label.pack(expand=True, fill="both", padx=15, pady=15)
        self.x = x
        self.y = float(y)
        self.typewriter_index = 0

    def typewriter(self):
        if not self.alive:
            return
        self.label.config(text=self.full_text[:self.typewriter_index])
        if self.typewriter_index < len(self.full_text):
            self.typewriter_index += 1
            self.win.after(self.delay, self.typewriter)

    def rise(self, dy):
        self.y -= dy
        self.win.geometry(f"{BOX_W}x{BOX_H}+{int(self.x)}+{int(self.y)}")
        if not self.started_typing and self.y <= self.win.winfo_screenheight() - BOX_H:
            self.started_typing = True
            self.typewriter()

    def is_offscreen(self):
        return self.y + BOX_H < -50

    def destroy(self):
        self.alive = False
        try:
            self.win.destroy()
        except tk.TclError:
            pass


class FloatingSymbols:
    def __init__(self, parent, screen_w, screen_h):
        self.win = tk.Toplevel(parent)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry(f"{screen_w}x{screen_h}+0+0")
        self.win.configure(bg="#000001")
        try:
            self.win.attributes("-transparentcolor", "#000001")
        except tk.TclError:
            pass
        self.canvas = tk.Canvas(self.win, width=screen_w, height=screen_h,
                                bg="#000001", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.items = []
        for _ in range(SYMBOL_COUNT):
            x = random.uniform(0, screen_w)
            y = random.uniform(screen_h + 10, screen_h + 100)
            size = random.choice(SYMBOL_FONT_SIZES)
            item = self.canvas.create_text(
                x, y, text=random.choice(FLOATING_SYMBOLS),
                font=("Helvetica", size, "bold"),
                fill=random.choice(SYMBOL_COLORS)
            )
            self.items.append({
                "id": item, "x": x, "y": y,
                "base_x": x, "speed": random.uniform(*SYMBOL_SPEED_RANGE),
                "phase": random.uniform(0, math.tau),
                "amp": random.uniform(*SYMBOL_WOBBLE_AMP_RANGE),
                "freq": random.uniform(*SYMBOL_WOBBLE_FREQ_RANGE),
            })
        self.elapsed = 0.0

    def update(self, dt):
        self.elapsed += dt
        for symbol in self.items:
            symbol["y"] -= symbol["speed"] * dt
            if symbol["y"] < -30:
                symbol["y"] = self.screen_h + random.uniform(10, 100)
                symbol["base_x"] = random.uniform(0, self.screen_w)
            x = symbol["base_x"] + math.sin(
                self.elapsed * symbol["freq"] + symbol["phase"]
            ) * symbol["amp"]
            self.canvas.coords(symbol["id"], x, symbol["y"])


class LyricFloatApp:
    def __init__(self, root):
        self.root = root
        self.screen_w = root.winfo_screenwidth()
        self.screen_h = root.winfo_screenheight()
        self.next_lyric_idx = 0
        self.boxes = []
        self.symbols = FloatingSymbols(root, self.screen_w, self.screen_h)
        self.current_side = "left"
        self.wait_for_play = os.environ.get("LYRIC_WAIT") == "1"
        self.play_event = threading.Event()
        self.start()

    def random_safe_x(self):
        center_x = self.screen_w // 2
        if self.current_side == "left":
            self.current_side = "right"
            return center_x - (BOX_W + 60)
        self.current_side = "left"
        return center_x + 60

    def start(self):
        self.root.iconify()
        self.start_time = None
        self.last_frame_time = time.time()
        self.root.after(STARTUP_DELAY * 1000, self.after_startup_delay)
        self.root.after(FRAME_INTERVAL_MS, self.animate_symbols_during_delay)

    def after_startup_delay(self):
        if not self.wait_for_play:
            self.begin_lyrics()
            return
        print("Simbol sudah bergerak. Tekan ENTER bersamaan dengan PLAY lagu.")
        threading.Thread(target=self.wait_for_play_input, daemon=True).start()
        self.check_play_input()

    def wait_for_play_input(self):
        try:
            input()
        finally:
            self.play_event.set()

    def check_play_input(self):
        if self.play_event.is_set():
            self.begin_lyrics()
        else:
            self.root.after(50, self.check_play_input)

    def begin_lyrics(self):
        self.start_time = time.time()
        self.last_frame_time = self.start_time
        self.tick()

    def animate_symbols_during_delay(self):
        if self.start_time is not None:
            return
        now = time.time()
        dt = now - self.last_frame_time
        self.last_frame_time = now
        self.symbols.update(dt)
        self.root.after(FRAME_INTERVAL_MS, self.animate_symbols_during_delay)

    def tick(self):
        now = time.time()
        elapsed = now - self.start_time + OFFSET
        dt = now - self.last_frame_time
        self.last_frame_time = now

        while (self.next_lyric_idx < len(LYRICS)
               and LYRICS[self.next_lyric_idx][0] <= elapsed):
            i = self.next_lyric_idx
            text = LYRICS[i][1]
            duration = (LYRICS[i + 1][0] - LYRICS[i][0]
                        if i + 1 < len(LYRICS) else LAST_DURATION)
            x = self.random_safe_x()
            y = self.screen_h
            self.boxes.append(LyricCard(self.root, text, x, y, duration))
            self.next_lyric_idx += 1

        for box in self.boxes:
            box.rise(RISE_SPEED * dt)
        still_visible = []
        for box in self.boxes:
            if box.is_offscreen():
                box.destroy()
            else:
                still_visible.append(box)
        self.boxes = still_visible

        self.symbols.update(dt)

        if self.next_lyric_idx < len(LYRICS) or self.boxes:
            self.root.after(FRAME_INTERVAL_MS, self.tick)
        else:
            self.root.destroy()


if __name__ == "__main__":
    # Muat font secara privat untuk proses ini supaya Tkinter dapat
    # menggunakannya tanpa perlu memasang font ke seluruh Windows.
    if os.name == "nt" and os.path.exists(FONT_FILE):
        gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
        gdi32.AddFontResourceExW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        gdi32.AddFontResourceExW.restype = ctypes.c_int
        if not gdi32.AddFontResourceExW(FONT_FILE, 0x10, None):
            print(f"Font Monaspace Radon gagal dimuat: {FONT_FILE}")
    root = tk.Tk()
    LyricFloatApp(root)
    root.mainloop()
