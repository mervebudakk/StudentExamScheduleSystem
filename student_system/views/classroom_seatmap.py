# student_system/views/classroom_seatmap.py
from PyQt5.QtCore import Qt, QRectF, QSize
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont, QColor  # QColor EKLENDİ
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout


class SeatMapWidget(QWidget):
    """
    Basit oturma düzeni çizimi:
    - enine_sira_sayisi: satırdaki sıra grubu sayısı (kolon gibi düşünebilirsin)
    - boyuna_sira_sayisi: satır (row) sayısı
    - sira_yapisi: 2/3/4 kişilik sıra grubu
    - placements: (sira_no, sutun_no, koltuk_no, ogrenci_no, ad_soyad) dict listesi
    """

    def __init__(self, enine, boyuna, yapi, kapasite, placements=None, parent=None):
        super().__init__(parent)
        self.enine = max(1, int(enine or 1))
        self.boyuna = max(1, int(boyuna or 1))
        self.yapi = int(yapi or 2)
        self.kapasite = int(kapasite or 0)
        self.setMinimumSize(520, 360)

        # Öğrenci yerleşimlerini hızlı arama için map'e dönüştür
        self.placements_map = {}
        if placements:
            for p in placements:
                key = (p['sira_no'], p['sutun_no'], p['koltuk_no'])
                # Format: 248700624\nOya Köse
                self.placements_map[key] = f"{p['ogrenci_no']}\n{p['ad_soyad']}"

    def sizeHint(self):
        return QSize(680, 440)

    def paintEvent(self, e):  # GÜNCELLENDİ
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w, h = self.width(), self.height()
        margin = 24
        area = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)

        if self.enine <= 0 or self.boyuna <= 0:
            return

        group_w = area.width() / self.enine
        group_h = area.height() / self.boyuna

        desk_margin = 8
        seat_gap = 4

        pen = QPen(Qt.gray)
        pen.setWidth(1)
        p.setPen(pen)

        # Metin için font (Biraz büyütüldü)
        text_font = QFont("Segoe UI", 8)  # GÜNCELLENDİ (7 -> 8)

        # Sıra grupları (1-based index kullanarak DB ile eşleş)
        for r in range(1, self.boyuna + 1):
            for c in range(1, self.enine + 1):
                # 0-based index'e çevir (çizim için)
                gx = area.left() + (c - 1) * group_w
                gy = area.top() + (r - 1) * group_h

                desk_rect = QRectF(gx + desk_margin, gy + desk_margin,
                                   group_w - 2 * desk_margin, group_h - 2 * desk_margin)
                # Masa
                p.setBrush(QBrush(Qt.white))
                p.drawRoundedRect(desk_rect, 8, 8)

                # Koltuklar (yapi kadar)
                seat_w = (desk_rect.width() - (self.yapi + 1) * seat_gap) / self.yapi

                # --- DÜZELTME BAŞLANGICI ---
                # Koltuk yüksekliğini, mevcut "desk_rect" alanının tamamını
                # (üstte ve altta küçük bir boşlukla) kaplayacak şekilde ayarla
                seat_h = max(30, desk_rect.height() - (2 * seat_gap))

                # Y pozisyonunu da "alttan" değil "üstten" başlat
                sy = desk_rect.top() + seat_gap

                # Renkleri tanımla
                renk_dolu = QColor("#AED6F1")
                renk_bos_kullanilabilir = Qt.lightGray
                renk_bos_kullanilamaz = QColor("#EAECEE")  # Sosyal mesafe boşluğu (örn. Koyu Gri)
                # VEYA: renk_bos_kullanilamaz = QColor("#FADBD8") # Soluk Kırmızı

                for i in range(1, self.yapi + 1):
                    # 0-based index'e çevir (çizim için)
                    sx = desk_rect.left() + seat_gap + (i - 1) * (seat_w + seat_gap)
                    seat_rect = QRectF(sx, sy, seat_w, seat_h)

                    key = (r, c, i)
                    student_info = self.placements_map.get(key)

                    # KULLANILAMAZ (Sosyal Mesafe) koltukları belirle
                    is_unusable = False
                    if self.yapi == 3 and i == 2:  # 3'lü sıranın ortası
                        is_unusable = True
                    elif self.yapi == 4 and (i == 2 or i == 3):  # 4'lü sıranın ortası
                        is_unusable = True

                    if student_info:
                        # 1. DOLU KOLTUK
                        p.setBrush(QBrush(renk_dolu))
                        p.drawRoundedRect(seat_rect, 5, 5)
                        p.setPen(Qt.black)

                        # Fontu 3'lü/4'lü sıralar için küçük (6pt) tut
                        if self.yapi >= 3:
                            current_font = QFont("Segoe UI", 6)
                        else:
                            current_font = QFont("Segoe UI", 7)

                        p.setFont(current_font)

                        # --- HİZALAMA DÜZELTMESİ ---
                        # Metin için iç boşluğu (padding) minimuma indir
                        text_rect = seat_rect.adjusted(2, 2, -2, -2)

                        # Metni "Üstte ve Ortada" hizala (Dikey ortalamayı kaldır)
                        p.drawText(text_rect,
                                   Qt.AlignTop | Qt.AlignHCenter | Qt.TextWordWrap,
                                   student_info)

                    elif is_unusable:
                        # 2. KULLANILAMAZ (SOSYAL MESAFE) KOLTUK
                        p.setBrush(QBrush(renk_bos_kullanilamaz))
                        pen.setStyle(Qt.DotLine)  # Kenarlığı noktalı yap
                        p.setPen(pen)
                        p.drawRoundedRect(seat_rect, 5, 5)
                        pen.setStyle(Qt.SolidLine)  # Kalemi sıfırla

                    else:
                        # 3. BOŞ (AMA KULLANILABİLİR) KOLTUK
                        p.setBrush(QBrush(renk_bos_kullanilabilir))
                        p.drawRoundedRect(seat_rect, 5, 5)

                    p.setPen(pen)  # Kalemi her koltuktan sonra sıfırla

                # Kapasite bilgisi
                fiziksel_kapasite = self.enine * self.boyuna * self.yapi
                sinav_kapasitesi = self.kapasite  # DB'den gelen kapasite

                p.setFont(QFont("Segoe UI", 9))
                p.setPen(Qt.darkGray)  # Veya istediğiniz bir renk

                msg = (
                    f"Fiziksel Kapasite (Tüm Koltuklar): {fiziksel_kapasite}  "
                    f"({self.enine} Enine x {self.boyuna} Boyuna x {self.yapi} Yapı)    |    "
                    f"Sınav Kapasitesi (Sosyal Mesafeli): {sinav_kapasitesi}"
                )

                p.drawText(margin, h - 8, msg)


class ClassroomDetailPanel(QFrame):
    """Üstte derslik bilgilerinin yazdığı, altta çizimin olduğu basit panel."""

    def __init__(self, rec: dict, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame { background: white; border: 2px solid #ecf0f1; border-radius: 12px; }
            QLabel.title { color:#2c3e50; font-size:16px; font-weight:700; }
            QLabel.meta  { color:#7f8c8d; font-size:13px; }
        """)
        lay = QVBoxLayout(self);
        lay.setContentsMargins(16, 16, 16, 16);
        lay.setSpacing(10)

        title = QLabel(f"🏫 {rec.get('derslik_kodu', '')}  —  {rec.get('derslik_adi', '')}")
        title.setObjectName("title");
        title.setProperty("class", "title")

        meta = QLabel(
            f"• Kapasite: {rec.get('kapasite', '-')}    "
            f"• Enine: {rec.get('enine_sira_sayisi', '-')}    "
            f"• Boyuna: {rec.get('boyuna_sira_sayisi', '-')}    "
            f"• Yapı: {rec.get('sira_yapisi', '-')}"
        )
        meta.setObjectName("meta");
        meta.setProperty("class", "meta")

        seatmap = SeatMapWidget(
            rec.get('enine_sira_sayisi'), rec.get('boyuna_sira_sayisi'),
            rec.get('sira_yapisi'), rec.get('kapasite'),
            placements=None
        )

        lay.addWidget(title)
        lay.addWidget(meta)
        lay.addWidget(seatmap)