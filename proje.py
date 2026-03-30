import os
import sys
import ctypes
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import subprocess
import time
import sqlite3
import re
import csv
import json
import urllib.request
from urllib.error import HTTPError, URLError
import socket
import threading
import hashlib
import winreg 
import ssl 
import math
import string

# --- 1. YÖNETİCİ KONTROLÜ ---
def yonetici_mi():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

YETKI_DURUMU = yonetici_mi()

if not YETKI_DURUMU:
    if getattr(sys, 'frozen', False): ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, None, None, 1)
    else: ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', None, 1)
    sys.exit()

# --- 2. VERİTABANI VE GÜVENLİK SINIFLARI ---
class VeritabaniYoneticisi:
    def __init__(self):
        base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        self.db_yolu = os.path.join(base_dir, "nexus_vault.db")
        self.lock = threading.Lock()
        self.komut_calistir("CREATE TABLE IF NOT EXISTS EngellenenIPler (ID INTEGER PRIMARY KEY AUTOINCREMENT, IpAdresi TEXT NOT NULL, EngellenmeZamani DATETIME DEFAULT CURRENT_TIMESTAMP)")

    def komut_calistir(self, sorgu, parametreler=(), fetch=False):
        with self.lock:
            try:
                baglanti = sqlite3.connect(self.db_yolu)
                imlec = baglanti.cursor()
                imlec.execute(sorgu, parametreler)
                if fetch:
                    sonuc = imlec.fetchall()
                    baglanti.close()
                    return sonuc
                baglanti.commit()
                baglanti.close()
                return True, "Başarılı"
            except Exception as e: return [] if fetch else (False, f"Hata: {e}")

    def ip_kayitli_mi(self, ip): return bool(self.komut_calistir("SELECT COUNT(*) FROM EngellenenIPler WHERE IpAdresi = ?", (ip,), fetch=True)[0][0] > 0)
    def ip_kaydet(self, ip): return self.komut_calistir("INSERT INTO EngellenenIPler (IpAdresi) VALUES (?)", (ip,))
    def ip_sil(self, ip): return self.komut_calistir("DELETE FROM EngellenenIPler WHERE IpAdresi = ?", (ip,))
    def tum_ipleri_getir(self): return self.komut_calistir("SELECT IpAdresi, datetime(EngellenmeZamani, 'localtime') FROM EngellenenIPler ORDER BY ID DESC", fetch=True)

class TehditYonetimi:
    def __init__(self, db_yoneticisi):
        self.db = db_yoneticisi
        self.ip_sablonu = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

    def os_komut_calistir(self, komut):
        try:
            subprocess.run(komut, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except: return False

    def ip_engelle(self, ip):
        if not self.ip_sablonu.match(ip): return False, f"[-] '{ip}' geçersiz IP."
        if self.db.ip_kayitli_mi(ip): return False, f"[!] '{ip}' zaten engelli."
        if self.os_komut_calistir(f'netsh advfirewall firewall add rule name="Otonom_Engel_{ip}" dir=in action=block remoteip={ip}'):
            self.db.ip_kaydet(ip)
            return True, f"[+] BAŞARILI: {ip} engellendi."
        return False, f"[-] HATA: Kural oluşturulamadı."

    def ip_kaldir(self, ip):
        self.os_komut_calistir(f'netsh advfirewall firewall delete rule name="Otonom_Engel_{ip}"')
        self.db.ip_sil(ip)
        return True, f"[+] BİLGİ: {ip} engeli kaldırıldı."

# --- 3. SUPER APP ARAYÜZÜ ---
class OtonomSavunmaPaneli:
    def __init__(self, root):
        self.root = root
        self.root.title("Nexus System Suite - SOC Command Center (Ultimate Edition)")
        self.root.geometry("1150x850") 
        self.db = VeritabaniYoneticisi()
        self.tehdit = TehditYonetimi(self.db)
        
        self.temalar = {
            "Profesyonel (Kurumsal)": {"bg": "#201f1e", "fg": "#f3f2f1", "panel": "#292827", "accent": "#0078d4", "log_bg": "#11100f", "log_fg": "#4dabf7"},
            "Dark (Karanlık)": {"bg": "#0f172a", "fg": "#f8fafc", "panel": "#1e293b", "accent": "#38bdf8", "log_bg": "#020617", "log_fg": "#22c55e"},
            "Hacker (Terminal)": {"bg": "#000000", "fg": "#00ff00", "panel": "#050505", "accent": "#00cc00", "log_bg": "#000000", "log_fg": "#00ff00"}
        }
        self.aktif_tema = "Profesyonel (Kurumsal)" 
        self.stiller_hazirla()
        self.arayuz_olustur()

    def stiller_hazirla(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.tema_uygula(self.aktif_tema)

    def tema_uygula(self, tema_adi):
        renk = self.temalar[tema_adi]
        self.root.configure(bg=renk["bg"])
        self.style.configure("TNotebook", background=renk["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", background=renk["panel"], foreground=renk["fg"], font=("Segoe UI", 10, "bold"), padding=[15, 5])
        self.style.map("TNotebook.Tab", background=[("selected", renk["accent"])], foreground=[("selected", "#ffffff")])
        self.style.configure("Treeview", background=renk["panel"], foreground=renk["fg"], fieldbackground=renk["panel"], rowheight=30, borderwidth=0)
        self.style.map('Treeview', background=[('selected', renk["accent"])])
        self.style.configure("Treeview.Heading", background=renk["accent"], foreground="white", font=("Segoe UI", 10, "bold"), borderwidth=0)

        try:
            self.ust_cerceve.config(bg=renk["log_bg"])
            self.baslik_etiket.config(bg=renk["log_bg"], fg=renk["accent"])
            self.log_etiket.config(bg=renk["bg"], fg=renk["accent"])
            self.log_ekrani.config(bg=renk["log_bg"], fg=renk["log_fg"])
            for f in [self.sekme_guvenlik, self.sekme_ag_analiz, self.sekme_osint, self.sekme_log, self.sekme_kripto]: f.config(bg=renk["bg"])
            for widget in self.root.winfo_children(): self.widget_renklendir(widget, renk)
        except: pass 

    def widget_renklendir(self, widget, renk):
        try:
            if type(widget) == tk.Label: widget.config(bg=renk["bg"], fg=renk["fg"])
            elif type(widget) == tk.Entry: widget.config(bg=renk["panel"], fg=renk["fg"], insertbackground=renk["fg"])
        except: pass 
        for child in widget.winfo_children(): self.widget_renklendir(child, renk)

    def arayuz_olustur(self):
        self.ust_cerceve = tk.Frame(self.root, height=50)
        self.ust_cerceve.pack(fill=tk.X)
        self.baslik_etiket = tk.Label(self.ust_cerceve, text="🛡️ NEXUS SUPER APP - Ultimate Edition", font=("Segoe UI", 16, "bold"), pady=10)
        self.baslik_etiket.pack(side=tk.LEFT, padx=20)
        
        tema_frame = tk.Frame(self.ust_cerceve, bg="#11100f"); tema_frame.pack(side=tk.RIGHT, padx=20, pady=10)
        self.tema_secici = ttk.Combobox(tema_frame, values=list(self.temalar.keys()), state="readonly", width=20)
        self.tema_secici.set(self.aktif_tema); self.tema_secici.pack(side=tk.LEFT, padx=5)
        self.tema_secici.bind("<<ComboboxSelected>>", lambda e: self.tema_uygula(self.tema_secici.get()))

        self.sekmeler = ttk.Notebook(self.root)
        self.sekmeler.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)

        self.sekme_guvenlik = tk.Frame(self.sekmeler); self.sekme_ag_analiz = tk.Frame(self.sekmeler)
        self.sekme_osint = tk.Frame(self.sekmeler); self.sekme_log = tk.Frame(self.sekmeler); self.sekme_kripto = tk.Frame(self.sekmeler)

        self.sekmeler.add(self.sekme_guvenlik, text="🔒 Otonom Firewall")
        self.sekmeler.add(self.sekme_ag_analiz, text="🌐 Ağ & Cihaz Keşfi")
        self.sekmeler.add(self.sekme_osint, text="🕵️ OSINT & Web")
        self.sekmeler.add(self.sekme_kripto, text="🧬 Kripto & Adli Bilişim")
        self.sekmeler.add(self.sekme_log, text="📜 Zafiyet Denetimi")

        self.arayuz_guvenlik(); self.arayuz_ag(); self.arayuz_osint(); self.arayuz_kripto(); self.arayuz_log()

        self.log_etiket = tk.Label(self.root, text="Sistem Terminali", font=("Consolas", 10, "bold")); self.log_etiket.pack(anchor="w", padx=20)
        self.log_ekrani = scrolledtext.ScrolledText(self.root, width=100, height=10, font=("Consolas", 10), relief="flat", borderwidth=1)
        self.log_ekrani.pack(pady=5, padx=20, fill=tk.X)
        self.tema_uygula(self.aktif_tema); self.tabloyu_guncelle()
        self.log_yaz("[+] Nexus Ultimate Edition Başlatıldı. Tüm profesyonel araçlar emrinizde.")

    # --- SEKME 1: GÜVENLİK ---
    def arayuz_guvenlik(self):
        f = tk.Frame(self.sekme_guvenlik); f.pack(pady=15)
        self.ip_giris = tk.Entry(f, width=25, font=("Consolas", 14), relief="flat")
        self.ip_giris.pack(side=tk.LEFT, padx=10, ipady=5); self.ip_giris.insert(0, "Engellenecek IP...")
        self.ip_giris.bind("<FocusIn>", lambda e: self.ip_giris.delete(0, tk.END) if "Engellenecek" in self.ip_giris.get() else None)
        tk.Button(f, text="ENGELLE", bg="#ef4444", fg="white", font=("Arial", 11, "bold"), relief="flat", command=self.manuel_engelle).pack(side=tk.LEFT, padx=5)

        self.tablo = ttk.Treeview(self.sekme_guvenlik, columns=("ip", "zaman"), show="headings", height=6)
        self.tablo.heading("ip", text="IP Adresi"); self.tablo.heading("zaman", text="Kayıt Zamanı")
        self.tablo.column("ip", width=250, anchor=tk.CENTER); self.tablo.column("zaman", width=350, anchor=tk.CENTER)
        self.tablo.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)
        tk.Button(self.sekme_guvenlik, text="Seçili Engeli Kaldır", bg="#3b82f6", fg="white", font=("Arial", 10, "bold"), relief="flat", command=self.tablodan_secileni_kaldir).pack(pady=10)

    # --- SEKME 2: AĞ & CİHAZ KEŞFİ ---
    def arayuz_ag(self):
        f_ust = tk.Frame(self.sekme_ag_analiz); f_ust.pack(fill=tk.X, padx=20, pady=10)
        f_sol = tk.Frame(f_ust); f_sol.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(f_sol, text="🌐 Hedef Ağ İstihbaratı", font=("Segoe UI", 12, "bold")).pack(pady=5)
        self.analiz_ip_giris = tk.Entry(f_sol, width=20, font=("Consolas", 12), relief="flat")
        self.analiz_ip_giris.pack(pady=5, ipady=4); self.analiz_ip_giris.insert(0, "IP Adresi...")
        self.analiz_ip_giris.bind("<FocusIn>", lambda e: self.analiz_ip_giris.delete(0, tk.END) if "IP" in self.analiz_ip_giris.get() else None)
        tk.Button(f_sol, text="Ping & Konum Bul", bg="#f59e0b", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.ip_analiz_et).start()).pack(pady=2, fill=tk.X, padx=50)
        tk.Button(f_sol, text="Açık Portları Tara", bg="#8b5cf6", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.port_taramasi).start()).pack(pady=2, fill=tk.X, padx=50)

        f_sag = tk.Frame(f_ust); f_sag.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(f_sag, text="🖧 Yerel Ağ Cihazları & Kartlar", font=("Segoe UI", 12, "bold")).pack(pady=5)
        tk.Button(f_sag, text="TCP Bağlantıları (Netstat)", bg="#0ea5e9", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.aktif_baglantilari_goster).start()).pack(pady=2, fill=tk.X, padx=50)
        tk.Button(f_sag, text="Yerel Cihazlar (ARP)", bg="#ec4899", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.arp_tablosu_getir).start()).pack(pady=2, fill=tk.X, padx=50)
        # YENİ ARAÇ (Seçim #9): Ağ Arayüzleri ve MAC
        tk.Button(f_sag, text="Ağ Kartları & MAC Analizi (İfşa)", bg="#10b981", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.ag_arayuzleri_getir).start()).pack(pady=2, fill=tk.X, padx=50)

    # --- SEKME 3: OSINT & WEB ---
    def arayuz_osint(self):
        f_ust = tk.Frame(self.sekme_osint); f_ust.pack(fill=tk.X, padx=20, pady=10)
        
        f_sol = tk.Frame(f_ust); f_sol.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(f_sol, text="📧 E-Posta İstihbaratı", font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))
        self.email_giris = tk.Entry(f_sol, width=20, font=("Consolas", 12), relief="flat")
        self.email_giris.pack(pady=5, ipady=4); self.email_giris.insert(0, "hedef@sirket.com")
        self.email_giris.bind("<FocusIn>", lambda e: self.email_giris.delete(0, tk.END) if "hedef" in self.email_giris.get() else None)
        tk.Button(f_sol, text="MX Sunucu & DNS Analizi", bg="#f59e0b", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.email_osint).start()).pack(pady=5, fill=tk.X, padx=50)

        f_sag = tk.Frame(f_ust); f_sag.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(f_sag, text="🌐 Web Sniper & Dork Jeneratörü", font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))
        self.domain_giris = tk.Entry(f_sag, width=22, font=("Consolas", 12), relief="flat")
        self.domain_giris.pack(pady=5, ipady=4); self.domain_giris.insert(0, "sirket.com")
        self.domain_giris.bind("<FocusIn>", lambda e: self.domain_giris.delete(0, tk.END) if "sirket" in self.domain_giris.get() else None)
        tk.Button(f_sag, text="Gizli Dizin ve Subdomain Taraması", bg="#ef4444", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.tam_web_tarama).start()).pack(pady=2, fill=tk.X, padx=30)
        tk.Button(f_sag, text="Web Teknolojisi & Header Analizi", bg="#0078d4", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.tam_tech_tarama).start()).pack(pady=2, fill=tk.X, padx=30)
        # YENİ ARAÇ (Seçim #3): Google Dork Jeneratörü
        tk.Button(f_sag, text="Google Dork Jeneratörü (Zafiyet Bulucu)", bg="#8b5cf6", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.dork_jeneratoru).start()).pack(pady=2, fill=tk.X, padx=30)

    # --- SEKME 4: KRİPTO & ADLİ BİLİŞİM ---
    def arayuz_kripto(self):
        f_ust = tk.Frame(self.sekme_kripto); f_ust.pack(fill=tk.X, padx=20, pady=10)
        
        f_sol = tk.Frame(f_ust); f_sol.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(f_sol, text="🧬 Kriptografi & Şifre Denetimi", font=("Segoe UI", 12, "bold")).pack(pady=5)
        self.hash_giris = tk.Entry(f_sol, width=25, font=("Consolas", 12), relief="flat")
        self.hash_giris.pack(pady=5, ipady=4); self.hash_giris.insert(0, "Şifre veya Metin...")
        self.hash_giris.bind("<FocusIn>", lambda e: self.hash_giris.delete(0, tk.END) if "Metin" in self.hash_giris.get() else None)
        tk.Button(f_sol, text="MD5/SHA256 Hash Oluştur", bg="#0ea5e9", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.hash_olustur).start()).pack(pady=2, fill=tk.X, padx=30)
        # YENİ ARAÇ (Seçim #6): Şifre Sağlamlık ve Kırılma Süresi
        tk.Button(f_sol, text="Şifre Kırılma Süresi (Entropy) Testi", bg="#8b5cf6", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.sifre_gucu_testi).start()).pack(pady=2, fill=tk.X, padx=30)

        f_sag = tk.Frame(f_ust); f_sag.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(f_sag, text="💾 Adli Bilişim & Anti-Forensics", font=("Segoe UI", 12, "bold")).pack(pady=5)
        tk.Button(f_sag, text="USB Bağlantı & Recent Dosya Kayıtları", bg="#0078d4", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.tam_adli_bilisim).start()).pack(pady=2, fill=tk.X, padx=30)
        # YENİ ARAÇ (Seçim #1): Meta Veri (Exif) Avcısı
        tk.Button(f_sag, text="Görsel/Belge Meta Veri (Exif) Avcısı", bg="#f59e0b", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.metadata_avcisi).start()).pack(pady=2, fill=tk.X, padx=30)
        # YENİ ARAÇ (Seçim #10): Anti-Adli Bilişim (Ghost Mode)
        tk.Button(f_sag, text="Siber İz Temizleyici (Ghost Mode)", bg="#ef4444", fg="white", font=("Arial", 10, "bold"), relief="flat", command=lambda: threading.Thread(target=self.ghost_mode).start()).pack(pady=2, fill=tk.X, padx=30)

    # --- SEKME 5: ZAFİYET DENETİMİ ---
    def arayuz_log(self):
        tk.Label(self.sekme_log, text="İşletim Sistemi Denetleyicisi (Auditor)", font=("Segoe UI", 12, "bold")).pack(pady=20)
        f = tk.Frame(self.sekme_log); f.pack(pady=5)
        tk.Button(f, text="RDP Saldırı Loglarını Tarat", bg="#f97316", fg="white", font=("Arial", 10, "bold"), relief="flat", padx=10, command=lambda: threading.Thread(target=self.windows_loglarini_tara).start()).pack(side=tk.LEFT, padx=10)
        tk.Button(f, text="Windows Güvenlik Kalkanı Check-up", bg="#3b82f6", fg="white", font=("Arial", 10, "bold"), relief="flat", padx=10, command=lambda: threading.Thread(target=self.windows_checkup).start()).pack(side=tk.LEFT, padx=10)
        f2 = tk.Frame(self.sekme_log); f2.pack(pady=15)
        tk.Button(f2, text="Yerel Yönetici Yetki Denetimi", bg="#ef4444", fg="white", font=("Arial", 10, "bold"), relief="flat", padx=10, command=lambda: threading.Thread(target=self.yerel_yetki_analizi).start()).pack(side=tk.LEFT, padx=10)
        tk.Button(f2, text="Başlangıç Zararlı Avcısı (Autorun)", bg="#10b981", fg="white", font=("Arial", 10, "bold"), relief="flat", padx=10, command=lambda: threading.Thread(target=self.baslangic_analizi).start()).pack(side=tk.LEFT, padx=10)

    # --- GENEL METOTLAR ---
    def log_yaz(self, mesaj):
        self.log_ekrani.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {mesaj}\n")
        self.log_ekrani.see(tk.END)

    def tabloyu_guncelle(self):
        for k in self.tablo.get_children(): self.tablo.delete(k)
        for s in self.db.tum_ipleri_getir(): self.tablo.insert("", tk.END, values=(s[0], s[1]))

    def manuel_engelle(self):
        if "IP" not in self.ip_giris.get():
            b, m = self.tehdit.ip_engelle(self.ip_giris.get().strip())
            self.log_yaz(m); self.tabloyu_guncelle()

    def tablodan_secileni_kaldir(self):
        secili = self.tablo.selection()
        if secili: self.log_yaz(self.tehdit.ip_kaldir(self.tablo.item(secili[0])['values'][0])[1]); self.tabloyu_guncelle()

    def rapor_disa_aktar(self):
        v = self.db.tum_ipleri_getir()
        dy = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], title="Rapor")
        if dy and v:
            with open(dy, mode='w', newline='', encoding='utf-8') as d: csv.writer(d).writerows([["Tehdit_IP", "Zaman"]] + v)
            self.log_yaz(f"[+] Rapor oluşturuldu.")

    # --- ARAÇLAR ---
    def ping_testi(self):
        ip = self.analiz_ip_giris.get().strip()
        si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        s = subprocess.run(["ping", "-n", "1", "-w", "1000", ip], startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, text=True)
        self.log_yaz(f"[+] {ip} ayakta." if "TTL=" in s.stdout else f"[-] {ip} kapalı.")

    def ip_analiz_et(self):
        try: self.log_yaz(f"[+] Konum: {json.loads(urllib.request.urlopen(f'http://ip-api.com/json/{self.analiz_ip_giris.get().strip()}', timeout=3).read().decode()).get('country')}")
        except: self.log_yaz("[-] OSINT Başarısız.")

    def port_taramasi(self):
        ip = self.analiz_ip_giris.get().strip()
        self.log_yaz(f"[*] {ip} portları taranıyor...")
        acik = []
        for p, s in {21:"FTP", 22:"SSH", 80:"HTTP", 443:"HTTPS", 3389:"RDP", 445:"SMB"}.items():
            try:
                sk = socket.socket(socket.AF_INET, socket.SOCK_STREAM); sk.settimeout(0.5)
                if sk.connect_ex((ip, p)) == 0: acik.append(str(p))
                sk.close()
            except: pass
        self.log_yaz(f"[!] AÇIK PORT: {', '.join(acik)}" if acik else "[+] Güvenli.")

    def aktif_baglantilari_goster(self):
        try:
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            s = subprocess.check_output("netstat -ano | findstr ESTABLISHED", shell=True, text=True, startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW)
            ipler = {st.split()[2].split(":")[0] for st in s.strip().split('\n') if len(st.split()) >= 3}
            dis = [i for i in ipler if i not in ["127.0.0.1", "0.0.0.0"] and not i.startswith("192.168.")]
            self.log_yaz(f"[!] Dış Bağlantılar: {', '.join(dis[:5])}" if dis else "[+] Yerel.")
        except: pass

    def arp_tablosu_getir(self):
        si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            s = subprocess.check_output("arp -a", shell=True, text=True, startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW)
            satirlar = [st.strip() for st in s.split('\n') if "dynamic" in st or "dinamik" in st.lower()]
            if satirlar:
                self.log_yaz("[+] Bulunan Cihazlar:")
                for st in satirlar[:5]: self.log_yaz(f"    -> IP: {st.split()[0]:<15} | MAC: {st.split()[1]}")
        except: pass

    # YENİ: AĞ ARAYÜZÜ VE MAC İFŞA (#9)
    def ag_arayuzleri_getir(self):
        self.log_yaz("[*] Fiziksel/Sanal Ağ Kartları ve MAC Adresleri taranıyor...")
        try:
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            s = subprocess.check_output("ipconfig /all", shell=True, text=True, startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW, errors="ignore")
            adaptor = ""
            for satir in s.split('\n'):
                if "adapter" in satir.lower() or "bağdaştırıcı" in satir.lower(): adaptor = satir.strip(" :")
                if "Physical Address" in satir or "Fiziksel Adres" in satir:
                    mac = satir.split(":")[1].strip()
                    if mac and mac != "00-00-00-00-00-00": self.log_yaz(f"  [+] {adaptor[:25]}... -> MAC: {mac}")
        except: self.log_yaz("[-] Arayüzler okunamadı.")

    def email_osint(self):
        mail = self.email_giris.get().strip()
        if "@" not in mail: return self.log_yaz("[-] E-posta giriniz.")
        self.log_yaz(f"[*] {mail.split('@')[1]} MX Analizi başlatıldı...")
        try:
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            s = subprocess.check_output(f"nslookup -type=mx {mail.split('@')[1]}", shell=True, text=True, startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW, errors="ignore")
            mx = [st.strip() for st in s.split('\n') if "MX preference" in st or "mail exchanger" in st]
            if mx:
                self.log_yaz("[+] Sunucular aktif:"); [self.log_yaz(f"    -> {m}") for m in mx]
            else: self.log_yaz("[-] MX sunucusu bulunamadı.")
        except: pass

    def tam_web_tarama(self):
        h = self.domain_giris.get().strip().replace("https://", "").replace("http://", "").split("/")[0]
        self.log_yaz(f"[*] {h} gizli dizin ve subdomain taraması başlatıldı...")
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        for yol in ["/robots.txt", "/admin", "/login", "/.env", "/backup.zip"]:
            try:
                if urllib.request.urlopen(urllib.request.Request(f"https://{h}{yol}", headers={'User-Agent':'Mozilla/5.0'}), timeout=2, context=ctx).status == 200:
                    self.log_yaz(f"  [!] AÇIK DOSYA: {yol}")
            except: pass
        for alt in ["www", "mail", "dev", "api", "admin", "test"]:
            try: self.log_yaz(f"  [+] Alt Alan: {alt}.{h} -> IP: {socket.gethostbyname(f'{alt}.{h}')}")
            except: pass
        self.log_yaz("[+] Web taraması tamamlandı.")

    def tam_tech_tarama(self):
        h = self.domain_giris.get().strip().replace("https://", "").replace("http://", "")
        self.log_yaz(f"[*] {h} Web Altyapısı ve Güvenlik Başlıkları analiz ediliyor...")
        try:
            ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
            cevap = urllib.request.urlopen(urllib.request.Request(f"https://{h}", headers={'User-Agent':'Mozilla/5.0'}), timeout=4, context=ctx)
            b = dict(cevap.headers); html = cevap.read().decode('utf-8', errors='ignore').lower()
            self.log_yaz(f"  [+] Sunucu: {b.get('Server', 'Gizlenmiş')}")
            if 'X-Powered-By' in b: self.log_yaz(f"  [+] Dil: {b['X-Powered-By']}")
            if "wp-content" in html: self.log_yaz("  [+] Sistem: WordPress")
            
            eksikler = [gb for gb in ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options"] if gb not in b]
            if eksikler: self.log_yaz(f"  [!] EKSİK Kalkanlar: {', '.join(eksikler)}")
            else: self.log_yaz("  [+] Tüm temel kalkanlar AKTİF.")
        except: self.log_yaz("[-] Analiz Hatası.")

    # YENİ: GOOGLE DORK JENERATÖRÜ (#3)
    def dork_jeneratoru(self):
        h = self.domain_giris.get().strip().replace("https://", "").replace("http://", "").split("/")[0]
        if not h or "sirket" in h: return self.log_yaz("[-] Dork üretmek için alan adı girin.")
        self.log_yaz(f"[*] {h} için Kritik Zafiyet (Google Dork) Sorguları Üretildi:")
        dorks = [f"site:{h} ext:php | ext:txt | ext:env", f"site:{h} inurl:admin | inurl:login", f"site:{h} intitle:\"index of\"", f"site:{h} filetype:pdf confidential | secret"]
        for d in dorks: self.log_yaz(f"  -> {d}")
        self.log_yaz("[+] Bu sorguları kopyalayıp Google'da aratarak sızıntıları ifşa edebilirsiniz.")

    def hash_olustur(self):
        m = self.hash_giris.get().strip()
        if "Metin" not in m: self.log_yaz(f"[*] Hash: MD5={hashlib.md5(m.encode()).hexdigest()} | SHA256={hashlib.sha256(m.encode()).hexdigest()[:15]}...")

    # YENİ: ŞİFRE SAĞLAMLIK & KIRILMA SÜRESİ (ENTROPY) (#6)
    def sifre_gucu_testi(self):
        sifre = self.hash_giris.get().strip()
        if not sifre or "Metin" in sifre: return self.log_yaz("[-] Şifre giriniz.")
        self.log_yaz("[*] Şifre Sağlamlık (Entropy) ve Kaba Kuvvet Analizi Başlatıldı...")
        
        havuz = 0
        if any(c.islower() for c in sifre): havuz += 26
        if any(c.isupper() for c in sifre): havuz += 26
        if any(c.isdigit() for c in sifre): havuz += 10
        if any(c in string.punctuation for c in sifre): havuz += len(string.punctuation)
        
        if havuz == 0: return self.log_yaz("[-] Geçersiz şifre formatı.")
        
        kombinasyon = havuz ** len(sifre)
        entropy = math.log2(kombinasyon) if kombinasyon > 0 else 0
        hiz = 100_000_000_000 # Modern GPU gücü (Saniyede 100 Milyar deneme)
        saniye = kombinasyon / hiz
        
        if saniye < 60: sure = "Saniyeler içinde kırılır! (AŞIRI ZAYIF)"
        elif saniye < 3600: sure = f"{int(saniye/60)} Dakika (ZAYIF)"
        elif saniye < 86400: sure = f"{int(saniye/3600)} Saat (ORTA)"
        elif saniye < 31536000: sure = f"{int(saniye/86400)} Gün (GÜÇLÜ)"
        else: sure = f"{int(saniye/31536000)} Yıl (AŞILAMAZ)"
        
        self.log_yaz(f"  [+] Karakter Havuzu: {havuz} | Uzunluk: {len(sifre)}")
        self.log_yaz(f"  [+] Matematiksel Entropy: {entropy:.2f} bit")
        self.log_yaz(f"  [!] Tahmini Kırılma Süresi (RTX 4090x4): {sure}")

    def tam_adli_bilisim(self):
        self.log_yaz("[*] Adli Bilişim: USB Bağlantı Geçmişi okunuyor...")
        try:
            anahtar = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Enum\USBSTOR")
            for i in range(min(winreg.QueryInfoKey(anahtar)[0], 5)): self.log_yaz(f"    -> Cihaz: {winreg.EnumKey(anahtar, i).replace('Disk&Ven_', '').split('&')[0]}")
        except: pass
        self.log_yaz("[*] Adli Bilişim: En son açılan 3 dosya...")
        try:
            r = os.path.join(os.environ['USERPROFILE'], r'AppData\Roaming\Microsoft\Windows\Recent')
            d = [f for f in os.listdir(r) if f.endswith(".lnk")]
            d.sort(key=lambda x: os.path.getmtime(os.path.join(r, x)), reverse=True)
            for file in d[:3]: self.log_yaz(f"    -> {file.replace('.lnk', '')}")
        except: pass

    # YENİ: EXIF VE META VERİ AVCISI (#1)
    def metadata_avcisi(self):
        dosya = filedialog.askopenfilename(title="Analiz Edilecek Görsel veya Belgeyi Seçin")
        if not dosya: return
        self.log_yaz(f"[*] Meta Veri (Exif) Analizi: {os.path.basename(dosya)}")
        try:
            self.log_yaz(f"  [+] Boyut: {os.path.getsize(dosya)/1024:.2f} KB | Son Değişiklik: {time.ctime(os.path.getmtime(dosya))}")
            with open(dosya, "rb") as f:
                veri = f.read(8192) # İlk 8KB'ye bak
                if b"Exif" in veri or b"EXIF" in veri or b"JFIF" in veri: self.log_yaz("  [!] EXIF/JFIF Meta verisi tespit edildi! (Fotoğraf izleri)")
                metinler = re.findall(b"[A-Za-z0-9/\-:;.,_$]{6,}", veri)
                ilginc = [m.decode('utf-8', 'ignore') for m in metinler if b"http" in m or b"Apple" in m or b"Samsung" in m or b"Windows" in m]
                if ilginc: self.log_yaz(f"  [!] Gizli Cihaz/Yazılım İzleri: {', '.join(set(ilginc[:4]))}")
                else: self.log_yaz("  [+] Dosyada derin Exif cihaz izi bulunamadı.")
        except Exception as e: self.log_yaz(f"[-] Analiz hatası: {e}")

    # YENİ: ANTI-FORENSICS GHOST MODE (#10)
    def ghost_mode(self):
        self.log_yaz("[!] ANTI-FORENSICS (Ghost Mode) BAŞLATILDI...")
        self.log_yaz("[*] Sistem izleri, önbellekler ve geçici dosyalar yok ediliyor...")
        try:
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run("ipconfig /flushdns", shell=True, startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW)
            self.log_yaz("  [+] DNS Önbelleği (Cache) silindi. Hedef bağlantı geçmişi gizlendi.")
            
            temp_yolu = os.environ.get('TEMP')
            temizlenen = 0
            if temp_yolu and os.path.exists(temp_yolu):
                for dosya in os.listdir(temp_yolu)[:25]: 
                    try:
                        os.remove(os.path.join(temp_yolu, dosya))
                        temizlenen += 1
                    except: pass
            self.log_yaz(f"  [+] Geçici Dizin (TEMP) tarandı, {temizlenen} adet sızıntı izi silindi.")
            self.log_yaz("[+] İŞLEM TAMAMLANDI. Sistemde bir hayalet gibisiniz.")
        except: self.log_yaz("[-] Yönetici izinlerini kontrol edin.")

    def windows_loglarini_tara(self):
        try:
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            komut = "Get-EventLog -LogName Security -InstanceId 4625 -Newest 1 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Message"
            sonuc = subprocess.check_output(["powershell", "-ExecutionPolicy", "Bypass", "-Command", komut], startupinfo=si, text=True, errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW)
            self.log_yaz(f"[!] RDP Logu:\n{sonuc.strip()[:100]}..." if sonuc.strip() else "[+] RDP saldırısı yok.")
        except: pass

    def windows_checkup(self):
        try:
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            defender = subprocess.check_output(["powershell", "-ExecutionPolicy", "Bypass", "-Command", "(Get-MpComputerStatus).AMServiceEnabled"], startupinfo=si, text=True, errors='ignore', creationflags=subprocess.CREATE_NO_WINDOW).strip()
            self.log_yaz("[*] Windows Defender: " + ("AKTİF" if defender == "True" else "KAPALI!"))
        except: pass

    def yerel_yetki_analizi(self):
        self.log_yaz("[*] Yöneticiler (Administrators) taranıyor...")
        try:
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            sonuc = subprocess.check_output("net localgroup administrators", shell=True, text=True, startupinfo=si, creationflags=subprocess.CREATE_NO_WINDOW, errors="ignore")
            kullanicilar = [s.strip() for s in sonuc.split('\n') if s.strip() and not s.startswith('-') and "Alias" not in s and "Name" not in s and "Comment" not in s and "komut" not in s.lower()]
            if kullanicilar:
                self.log_yaz(f"[!] Tam yetkili hesaplar:"); [self.log_yaz(f"    -> {k}") for k in kullanicilar[:-1]]
        except: pass

    def baslangic_analizi(self):
        self.log_yaz("[*] Autorun Başlangıç Kayıtları (Malware Analizi)...")
        bulunan = 0
        for hk, y in [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"), (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")]:
            try:
                a = winreg.OpenKey(hk, y)
                for i in range(winreg.QueryInfoKey(a)[1]):
                    self.log_yaz(f"  [!] Tespit: {winreg.EnumValue(a, i)[0]} -> {winreg.EnumValue(a, i)[1][:40]}"); bulunan += 1
            except: pass
        if bulunan == 0: self.log_yaz("[+] Başlangıca tutunmuş şüpheli bir program yok.")

if __name__ == "__main__":
    pencere = tk.Tk()
    uygulama = OtonomSavunmaPaneli(pencere)
    pencere.mainloop()