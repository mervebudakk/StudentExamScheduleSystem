# student_system/views/classroom_seatmap.py
from PyQt5.QtCore import Qt, QRectF, QSize
from PyQt5.QtGui import QPainter, QPen, QBrush, QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout

class SeatMapWidget(QWidget):
    """
    Basit oturma düzeni çizimi:
    - enine_sira_sayisi: satırdaki sıra grubu sayısı (kolon gibi düşünebilirsin)
    - boyuna_sira_sayisi: satır (row) sayısı
    - sira_yapisi: 2/3/4 kişilik sıra grubu
    """
    def __init__(self, enine, boyuna, yapi, kapasite, parent=None):
        super().__init__(parent)
        self.enine = max(1, int(enine or 1))
        self.boyuna = max(1, int(boyuna or 1))
        self.yapi = int(yapi or 2)
        self.kapasite = int(kapasite or 0)
        self.setMinimumSize(520, 360)

    def sizeHint(self):
        return QSize(680, 440)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w, h = self.width(), self.height()
        margin = 24
        area = QRectF(margin, margin+20, w-2*margin, h-2*margin-20)

        # Başlık
        p.setPen(Qt.black)
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        p.drawText(16, 18, f"Oturma Düzeni  ({self.boyuna} satır × {self.enine} sıra grubu, {self.yapi}'lü)")

        # Hücre boyutları
        group_w = area.width() / self.enine
        group_h = area.height() / self.boyuna

        # Sıra grubu (desk) çizim parametreleri
        desk_margin = 8
        seat_gap = 4

        pen = QPen(Qt.gray)
        pen.setWidth(1)
        p.setPen(pen)

        # Sıra grupları
        for r in range(self.boyuna):
            for c in range(self.enine):
                gx = area.left() + c * group_w
                gy = area.top()  + r * group_h

                desk_rect = QRectF(gx + desk_margin, gy + desk_margin,
                                   group_w - 2*desk_margin, group_h - 2*desk_margin)
                # Masa
                p.setBrush(QBrush(Qt.white))
                p.drawRoundedRect(desk_rect, 8, 8)

                # Koltuklar (yapi kadar)
                seat_w = (desk_rect.width() - (self.yapi + 1) * seat_gap) / self.yapi
                seat_h = min(22, desk_rect.height()/3)

                sy = desk_rect.bottom() - seat_h - seat_gap
                for i in range(self.yapi):
                    sx = desk_rect.left() + seat_gap + i*(seat_w + seat_gap)
                    seat_rect = QRectF(sx, sy, seat_w, seat_h)
                    p.setBrush(QBrush(Qt.lightGray))
                    p.drawRoundedRect(seat_rect, 5, 5)

        # Kapasite uyarısı
        computed = self.enine * self.boyuna * self.yapi
        p.setFont(QFont("Segoe UI", 9))
        msg = f"Hesaplanan kapasite: {computed}"
        if self.kapasite and self.kapasite != computed:
            p.setPen(Qt.red)
            msg += f"  |  ⚠️ Veri kapasitesi: {self.kapasite} (eşleşmiyor)"
        else:
            p.setPen(Qt.darkGreen)
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
        lay = QVBoxLayout(self); lay.setContentsMargins(16,16,16,16); lay.setSpacing(10)

        title = QLabel(f"🏫 {rec.get('derslik_kodu','')}  —  {rec.get('derslik_adi','')}")
        title.setObjectName("title"); title.setProperty("class","title")

        meta = QLabel(
            f"• Kapasite: {rec.get('kapasite','-')}    "
            f"• Enine: {rec.get('enine_sira_sayisi','-')}    "
            f"• Boyuna: {rec.get('boyuna_sira_sayisi','-')}    "
            f"• Yapı: {rec.get('sira_yapisi','-')}"
        )
        meta.setObjectName("meta"); meta.setProperty("class","meta")

        seatmap = SeatMapWidget(
            rec.get('enine_sira_sayisi'), rec.get('boyuna_sira_sayisi'),
            rec.get('sira_yapisi'), rec.get('kapasite')
        )

        lay.addWidget(title)
        lay.addWidget(meta)
        lay.addWidget(seatmap)
