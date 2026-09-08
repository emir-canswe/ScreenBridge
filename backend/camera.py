"""
ScreenBridge - Kamera Modülü
Tıklanan nesnenin rengini takip eder, sola/sağa hareketini algılar.
"""

import cv2
import numpy as np
import threading
import time
from collections import deque


class KalemTakipci:
    def __init__(self):
        self.calisiyor = False
        self.thread = None
        self.cap = None

        # Renk takibi
        self.hedef_lower = None
        self.hedef_upper = None
        self.renk_secildi = False

        # Pozisyon geçmişi
        self.pozisyonlar = deque(maxlen=30)

        # Hareket callback
        self.on_hareket = None  # fn(yon: "left" | "right")

        # Cooldown
        self.son_tetik = 0
        self.cooldown = 1.5  # saniye

        # Kamera frame (JPEG bytes) — frontend için
        self.son_frame = None
        self.frame_lock = threading.Lock()

        # Durum mesajı
        self.durum = "Kameraya tıklayarak nesneyi seçin"
        self.tiklama_bekleniyor = True

        # Canvas boyutu
        self.W = 640
        self.H = 480

    @property
    def calisıyor(self):
        return self.calisiyor

    @calisıyor.setter
    def calisıyor(self, value):
        self.calisiyor = value

    def baslat(self, on_hareket_fn):
        """Kamera döngüsünü başlat."""
        self.on_hareket = on_hareket_fn
        self.calisiyor = True
        self.thread = threading.Thread(target=self._dongu, daemon=True)
        self.thread.start()

    def durdur(self):
        self.calisiyor = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        cv2.destroyAllWindows()

    def renk_sec(self, x, y):
        """Kullanıcı kamera görüntüsünde bir noktaya tıkladı — o noktanın rengini al."""
        if self.cap is None or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        h_img, w_img = frame.shape[:2]
        # Koordinat sınırlarını koru (IndexError engelleme)
        clamped_x = max(0, min(w_img - 1, int(x)))
        clamped_y = max(0, min(h_img - 1, int(y)))

        # Tıklanan piksel HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[clamped_y, clamped_x]

        # Toleranslı aralık
        self.hedef_lower = np.array([max(0, int(h) - 15), max(40, int(s) - 60), max(40, int(v) - 60)])
        self.hedef_upper = np.array([min(179, int(h) + 15), min(255, int(s) + 60), min(255, int(v) + 60)])
        self.renk_secildi = True
        self.tiklama_bekleniyor = False
        self.durum = "Nesne takip ediliyor — sola/sağa hareket ettirin"
        self.pozisyonlar.clear()

    def _dongu(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.durum = "Kamera açılamadı (Webcam bulunamadı veya başka uygulama kullanıyor)"
            self.calisiyor = False
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.W)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.H)

        while self.calisiyor:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            frame = cv2.flip(frame, 1)  # Ayna görüntü
            goster = frame.copy()

            if self.renk_secildi and self.hedef_lower is not None:
                # Renk maskesi
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, self.hedef_lower, self.hedef_upper)

                # Gürültü temizle
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                mask = cv2.dilate(mask, kernel, iterations=2)

                # Kontur bul
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                if contours:
                    en_buyuk = max(contours, key=cv2.contourArea)
                    alan = cv2.contourArea(en_buyuk)

                    if alan > 500:  # Yeterince büyük nesne
                        (cx, cy), r = cv2.minEnclosingCircle(en_buyuk)
                        cx, cy = int(cx), int(cy)

                        # Çizim
                        cv2.circle(goster, (cx, cy), int(r), (0, 255, 178), 2)
                        cv2.circle(goster, (cx, cy), 5, (0, 255, 178), -1)

                        # Pozisyon kaydet
                        self.pozisyonlar.append((cx, cy, time.time()))

                        # Hareket algıla
                        self._hareket_kontrol(cx)

                # Maske overlay (hafif)
                mask_renkli = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                goster = cv2.addWeighted(goster, 0.85, mask_renkli // 4, 0.15, 0)

            # Yön göstergesi çiz
            self._ui_ciz(goster)

            # JPEG encode
            _, buf = cv2.imencode('.jpg', goster, [cv2.IMWRITE_JPEG_QUALITY, 75])
            with self.frame_lock:
                self.son_frame = buf.tobytes()

        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def _hareket_kontrol(self, cx):
        """Son pozisyonlara bakarak sola/sağa hareketi algıla."""
        if len(self.pozisyonlar) < 8:
            return

        simdi = time.time()
        if simdi - self.son_tetik < self.cooldown:
            return

        # Son 8 pozisyonun ilk ve son x farkı
        ilk_x = self.pozisyonlar[-8][0]
        son_x = self.pozisyonlar[-1][0]
        delta = son_x - ilk_x

        if delta > 80:   # Sağa hareket
            self.son_tetik = simdi
            self.pozisyonlar.clear()
            if self.on_hareket:
                self.on_hareket("right")

        elif delta < -80:  # Sola hareket
            self.son_tetik = simdi
            self.pozisyonlar.clear()
            if self.on_hareket:
                self.on_hareket("left")

    def _ui_ciz(self, frame):
        """Yardımcı UI öğeleri çiz."""
        h, w = frame.shape[:2]

        # Sol ok
        cv2.arrowedLine(frame, (80, h // 2), (20, h // 2), (100, 200, 255), 2, tipLength=0.4)
        cv2.putText(frame, "SOL", (20, h // 2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)

        # Sağ ok
        cv2.arrowedLine(frame, (w - 80, h // 2), (w - 20, h // 2), (100, 200, 255), 2, tipLength=0.4)
        cv2.putText(frame, "SAG", (w - 55, h // 2 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 200, 255), 1)

        # Orta çizgi
        cv2.line(frame, (w // 2, 0), (w // 2, h), (60, 60, 60), 1)

        # Durum
        cv2.putText(frame, self.durum, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 178), 1)

    def frame_al(self):
        with self.frame_lock:
            return self.son_frame


# Singleton
takipci = KalemTakipci()