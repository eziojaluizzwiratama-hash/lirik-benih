import argparse
import os
import subprocess
import sys
import time


LIRIK_FILE = "Benih.txt" 
HASIL_FILE = "lyrics.txt"
FOLDER = os.path.dirname(os.path.abspath(__file__))
os.chdir(FOLDER)

parser = argparse.ArgumentParser(description="Atur timing lirik dan jalankan animasinya.")
parser.add_argument("--offset", type=float, default=0.0,
                    help="koreksi timing awal dalam detik (default: 0)")
parser.add_argument("--record", action="store_true",
                    help="catat ulang timing dengan menekan Enter saat tiap baris mulai dinyanyikan")
parser.add_argument("--no-play", action="store_true",
                    help="hanya catat timing tanpa menjalankan animasi (gunakan bersama --record)")
args = parser.parse_args()

if not os.path.exists(LIRIK_FILE):
    print(f"File '{LIRIK_FILE}' tidak ada di folder ini.")
    sys.exit(1)

with open(LIRIK_FILE, encoding="utf-8") as file:
    lines = [line.strip() for line in file if line.strip()]
if not lines:
    print("File lirik kosong.")
    sys.exit(1)


def rekam_timing():
    print("\nSiapkan lagu di bagian yang sesuai, tetapi jangan di-play dulu.")
    print("Tekan ENTER di sini bersamaan dengan PLAY lagu.")
    print("Lalu tekan ENTER setiap kali baris berikut mulai dinyanyikan. Ketik s untuk melewati baris.\n")
    input("Siap? ENTER + PLAY... ")
    start = time.time()
    hasil = []
    for index, line in enumerate(lines, 1):
        print(f"\n[{index}/{len(lines)}] {line}")
        command = input("   ENTER untuk catat waktu, s untuk lewati: ")
        timestamp = time.time() - start
        if command.strip().lower() != "s":
            hasil.append((round(timestamp, 1), line))
    with open(HASIL_FILE, "w", encoding="utf-8") as file:
        for timestamp, text in hasil:
            file.write(f"{timestamp}|{text}\n")
    print("Timing tersimpan di", HASIL_FILE)


if args.record:
    rekam_timing()

if args.no_play:
    sys.exit(0)

if not os.path.exists(HASIL_FILE):
    print(f"File '{HASIL_FILE}' tidak ada. Buat file dengan format detik|lirik terlebih dahulu.")
    sys.exit(1)

print(f"\nOffset: {args.offset:g} detik. Sesuaikan dengan --offset bila perlu.")
print("Mulai lagu dari bagian yang sama seperti saat mencatat timing.")
print("Ctrl+C di terminal untuk berhenti.\n")
environment = dict(os.environ, LYRIC_WAIT="1", LYRIC_OFFSET=str(args.offset))
subprocess.run([sys.executable, os.path.join(FOLDER, "lyric_float.py")], env=environment)
