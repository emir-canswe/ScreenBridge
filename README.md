# 🌉 ScreenBridge - Çift Monitör Pencere Yöneticisi & Akıllı Jest Köprüsü

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.111.0-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV" />
  <img src="https://img.shields.io/badge/WebSocket-Realtime-black?style=for-the-badge&logo=socketdotio" alt="WebSocket" />
  <img src="https://img.shields.io/badge/Windows_API-ctypes-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows API" />
  <img src="https://img.shields.io/badge/UI-Cyberpunk_Glass-00FFB2?style=for-the-badge" alt="UI" />
</p>

---

## 📌 Proje Hakkında

**ScreenBridge**, Windows işletim sisteminde çoklu monitör (özellikle çift monitör) kullanan geliştiriciler, yayıncılar ve profesyoneller için tasarlanmış hibrit bir pencere yöneticisi ve akıllı köprü sistemidir.

Geleneksel kısayollarla uğraşmak yerine:
1. **Modern Web Arayüzü:** Açık pencereleri sol ve sağ monitör panellerinde anlık olarak görebilir, tek tıkla veya sürükle-bırak (Drag & Drop) ile monitörler arasında taşıyabilirsiniz.
2. **Bilgisayarlı Görü (Computer Vision) Destekli Jest Takibi:** Web kameranız üzerinden elinizdeki herhangi bir nesneyi (kalem, kart, fosforlu nesne, telefon vb.) tıklayarak seçebilir; nesneyi sola veya sağa hareket ettirerek seçtiğiniz pencereyi fiziksel bir hareketle ekranlar arasında aktarabilirsiniz!

---

## ✨ Temel Özellikler

- 🖥️ **Dinamik Monitör & Çözünürlük Algılama:** Windows API (ctypes.windll.user32) entegrasyonu sayesinde bağlı monitörlerin koordinatları, sınırları ve çözünürlükleri otomatik hesaplanır. Farklı ölçekleme (%125, %150) ve konumlandırmalara tam uyumludur.
- 🖱️ **Sezgisel Sürükle & Bırak (Drag & Drop):** Pencereleri panel kartları olarak tutup monitörler arasında sürükleyip bırakarak yer değiştirebilirsiniz.
- 📷 **OpenCV Tabanlı Renk & Hareket Takibi:**
  - HSV renk uzayında dinamik tolerans ile hassas nesne tespiti.
  - Morfolojik filtreleme (gürültü temizleme) ve kontur takibi.
  - Sola/Sağa yön algılama ve cooldown mekanizması (çift tetiklemeyi önler).
  - Canlı kamera önizlemesi ve tıkla-seç renk kalibrasyonu.
- ⚡ **Tam İki Yönlü WebSocket İletişimi:** Arka planda açılan/kapanan pencereler 2 saniyede bir otomatik taranır ve arayüze anında yansıtılır.
- 🪟 **Akıllı Pencere Yönetimi (Restore & Ortala):** Tam ekran (Maximized) veya simge durumundaki (Minimized) pencereler taşınmadan önce güvenli şekilde geri yüklenir ve hedef monitörün merkezine hizalanır.
- 🎨 **Modern Cyberpunk / Glassmorphism Arayüzü:** Koyu tema, akıcı CSS animasyonları, durum hapları, neon efektler ve ses getiren görsel geri bildirimler.

---

## 🏗️ Mimari Şema

`mermaid
graph TD
    A[Webcam / Kamera Görüntüsü] -->|OpenCV / HSV Renk Takibi| B[KalemTakipci Modülü]
    B -->|Jest Algılama: Sola / Sağa| C[Backend Callback]
    
    D[Web Tarayıcı Arayüzü] -->|Drag & Drop / Buton Tıklama| E[FastAPI / WebSocket Sunucusu]
    C -->|Thread-Safe ws_broadcast| E
    
    E -->|PyGetWindow & Windows User32 API| F[Windows Pencere Yöneticisi]
    F -->|Pencereyi Sol/Sağ Ekrana Taşı| G[Monitör 1 / Monitör 2]
    
    E -->|Canlı Durum Güncellemesi| D
`

---

## 🛠️ Teknoloji Yığını

| Katman | Teknoloji / Kütüphane | Açıklama |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI (0.111.0) | Yüksek performanslı asenkron REST & WebSocket sunucusu |
| **ASGI Sunucusu** | Uvicorn (0.29.0) | Lightning-fast ASGI web sunucusu |
| **Bilgisayarlı Görü** | OpenCV (opencv-python) | Gerçek zamanlı kamera yakalama ve nesne/renk takibi |
| **Matematiksel İşlem** | NumPy | Matris manipülasyonu ve renk aralığı filtreleme |
| **Pencere Otomasyonu** | PyGetWindow & PyAutoGUI | Windows pencerelerini listeleme, konumlandırma ve odaklama |
| **Sistem API** | ctypes (Win32 API) | Ekran ve monitör çözünürlüklerini dinamik tespit etme |
| **Frontend** | HTML5, Modern CSS3, Vanilla JS | Sıfır harici bağımlılık, ultra hızlı çalışan SPA |
| **İletişim Protokolü** | WebSockets | Çift yönlü gerçek zamanlı veri akışı ve bildirimler |

---

## 📂 Proje Dizin Yapısı

`
ScreenBridge/
├── backend/
│   ├── main.py          # FastAPI uygulaması, WebSocket kanalı, pencere mantığı ve REST rotaları
│   └── camera.py        # OpenCV tabanlı kamera işleme, HSV renk seçimi ve jest algılama modülü
├── frontend/
│   └── index.html       # Cyberpunk temalı tek sayfa kullanıcı arayüzü (Drag & Drop, Canlı Kamera)
├── .gitignore           # Python, pycache ve geçici sistem dosyaları filtresi
├── requirements.txt     # Python paket bağımlılıkları listesi
├── run.bat              # Windows için tek tıkla otomatik başlatıcı betik
└── README.md            # Proje dokümantasyonu
`

---

## 🚀 Kurulum ve Başlangıç

### 1. Gereksinimler
- **İşletim Sistemi:** Windows 10 veya Windows 11
- **Python:** Python 3.10 veya üzeri
- **Donanım:** Webcam (kamera tabanlı jest takibi kullanılacaksa)

### 2. Depoyu Klonlayın
`ash
git clone https://github.com/emir-canswe/ScreenBridge.git
cd ScreenBridge
`

### 3. Sanal Ortam Oluşturun ve Paketleri Yükleyin
`ash
# Sanal ortam oluşturma (isteğe bağlı ama önerilir)
python -m venv venv
venv\Scripts\activate

# Gerekli paketleri kurma
pip install -r requirements.txt
`

### 4. Uygulamayı Başlatın

**Yöntem A — Kolay Başlatıcı:**
Proje kök dizinindeki un.bat dosyasına çift tıklayın.

**Yöntem B — Terminal:**
`ash
python backend/main.py
`

Tarayıcınızda açın:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📖 Kullanım Kılavuzu

### 1. Butonlar ile Taşıma
Pencere kartının sağ tarafında bulunan ← veya → butonuna tıklayarak pencereyi anında karşı monitörün merkezine gönderebilirsiniz.

### 2. Sürükle & Bırak (Drag & Drop)
Pencere kartını farenizle tutun ve karşı monitörün alanına sürükleyip bırakın.

### 3. 📷 Kamera ile Nesne & Jest Takibi
1. Taşımak istediğiniz pencere kartındaki **📷 kamera simgesine** tıklayın.
2. Açılan modal pencerede kameranız aktif hale gelecektir.
3. Elinizde tuttuğunuz belirgin renkli bir nesneye (örneğin mavi bir kalem ucu, renkli bir kart vb.) kamera ekranında **tıklayın**.
4. Sistem o noktanın rengini hafızaya alır ve yeşil takip halkası ile nesneyi izlemeye başlar.
5. Nesneyi **sola kaydırdığınızda** pencere sol monitöre; **sağa kaydırdığınızda** sağ monitöre taşınır!

---

## 🔌 API Uç Noktaları

| Metot | Uç Nokta | Açıklama |
| :--- | :--- | :--- |
| GET | / | Web arayüzünü (index.html) sunar |
| GET | /api/windows | Aktif pencereleri ve monitör konumlarını listeler |
| POST | /api/move/left | Belirtilen pencereyi sol monitöre taşır |
| POST | /api/move/right | Belirtilen pencereyi sağ monitöre taşır |
| POST | /api/camera/start | Kamera modülünü başlatır ve hedef pencereyi kilitler |
| POST | /api/camera/stop | Kamerayı güvenli şekilde kapatır |
| POST | /api/camera/select-color | Tıklanan (x, y) pikselinin HSV rengini seçer |
| GET | /api/camera/frame | İşlenmiş anlık kamera görüntüsünü (JPEG) akıtır |
| GET | /api/camera/status | Kamera durumunu ve aktiflik bilgisini döner |
| WS | /ws | Gerçek zamanlı çift yönlü WebSocket kanalı |

---

## 💡 Sorun Giderme (FAQ)

- **Pencereler taşınmıyor veya hata veriyor mu?**
  Yönetici olarak çalışan bazı uygulamaları (Örn. Görev Yöneticisi) Windows güvenlik kısıtlamaları nedeniyle normal kullanıcı izinleriyle hareket ettiremeyebilirsiniz. ScreenBridge terminalini veya un.bat dosyasını **Yönetici Olarak Çalıştır** seçeneğiyle açabilirsiniz.
- **Kamera açılmıyor mu?**
  Web kameranızın başka bir uygulama (Zoom, Teams vb.) tarafından kullanılmadığından emin olun.
- **Tek monitörde çalışır mı?**
  Evet, tek monitör bağlandığında sistem otomatik olarak sanal bir ikinci monitör uzantısı hesaplar ve pencere taşıma komutlarını simüle eder.

---

## 👨‍💻 Geliştirici

**Emircan** - [emir-canswe](https://github.com/emir-canswe)

Lisans: MIT
