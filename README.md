====================================================================
🛡️ NEXUS SYSTEM SUITE - SOC COMMAND CENTER (Ultimate Edition) 🛡️
====================================================================

Geliştirici: İnan Demir
Versiyon: 1.0.0
Platform: Windows (10/11)
Mimari: Portable (Kurulum Gerektirmez)

HAKKINDA
--------------------------------------------------------------------
Nexus System Suite; Siber Güvenlik Uzmanları, Sistem Denetçileri (Auditor) 
ve Olay Müdahale (Incident Response) ekipleri için Python ile sıfırdan 
geliştirilmiş hepsi bir arada bir "Siber Savunma ve Adli Bilişim" aracıdır.

Sistem, dışarıdan hiçbir kütüphane kurulumuna ihtiyaç duymadan (Portable)
çalışır ve verilerini kendi oluşturduğu yerel (SQLite) kasasında şifreler.

MODÜLLER VE ÖZELLİKLER
--------------------------------------------------------------------
1. Otonom Firewall: Zararlı IP adreslerini tespit eder ve Windows Güvenlik 
   Duvarı'na tek tıkla engelleme (Block) kuralı yazar.
2. Ağ Keşfi (Recon): Hedef IP istihbaratı, Port taraması, ARP tablosu okuma 
   ve aktif TCP (Netstat) bağlantı analizi yapar.
3. OSINT & Web Sniper: Hedef domainlerde gizli dizin, subdomain ve HTTP 
   Header analizi yapar. E-posta MX kayıtlarını ve web teknoloji altyapısını 
   (Tech Stack) ifşa eder. Zafiyet avcıları için Google Dork üretir.
4. Zafiyet Denetimi (Auditor): Windows Event Loglarına sızarak başarısız 
   RDP (Uzak Masaüstü) saldırılarını tespit eder. Başlangıç (Autorun) 
   zararlılarını ve yerel yönetici (Admin) yetkilerini denetler.
5. Adli Bilişim (Forensics): Windows Kayıt Defteri (Registry) üzerinden 
   geçmiş USB bağlantılarını, son açılan dosyaları ve Exif/Meta verilerini 
   kurtarır. "Ghost Mode" ile DNS önbelleği ve Temp sızıntılarını temizler.

KULLANIM TALİMATLARI
--------------------------------------------------------------------
1. Uygulama kurulum gerektirmez. Sadece "Nexus_SuperApp.exe" dosyasını 
   çalıştırmanız yeterlidir.
2. ÖNEMLİ: Uygulamaya sağ tıklayıp "Yönetici Olarak Çalıştır" (Run as 
   Administrator) seçeneği ile açmanız zorunludur!

NEDEN YÖNETİCİ YETKİSİ (UAC) İSTİYOR?
Yazılımın temel işlevi Windows çekirdeğine müdahale etmektir. 
- Firewall kurallarını yazabilmek, 
- Olay günlüklerini (Event 4625) okuyabilmek,
- Kayıt Defterinden (Registry) Adli Bilişim verisi çekebilmek için 
bu yetki zorunludur. Uygulama, normal kullanıcı modunda açıldığında
kendini güvenli bir şekilde Yönetici moduna geçmeye zorlar.

YASAL UYARI
--------------------------------------------------------------------
Bu yazılım sadece Defansif Güvenlik (Blue Team), eğitim ve sistem denetimi 
(Audit) amacıyla geliştirilmiştir. Ağ keşfi ve OSINT araçlarının yetkisiz 
sistemler üzerinde kötüye kullanımından doğacak yasal sorumluluk tamamen 
kullanıcıya aittir.

====================================================================
İletişim ve Geri Bildirim İçin:
LinkedIn: https://www.linkedin.com/in/inan-demir-117022378/
GitHub:   https://github.com/inandemir
====================================================================
