# student_system/views/seat_plan.py
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog
)
from student_system.core.database import Database
from student_system.views.classroom_seatmap import SeatMapWidget
import math
import os

# PDF Kütüphaneleri
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# --- Türkçe Karakterler için Font Kaydı ---
try:
    # Windows yolları
    font_paths = [
        "C:/Windows/Fonts/Verdana.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/Tahoma.ttf"
    ]
    font_registered = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Verdana', font_path))
            font_registered = True
            break
    if not font_registered:
        print("Uyarı: Verdana/Arial fontu bulunamadı. PDF'te Türkçe karakter sorunu olabilir.")

    # PDF stilleri
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Baslik',
        fontName='Verdana' if font_registered else 'Helvetica-Bold',
        fontSize=14,
        alignment=TA_CENTER,
        spaceBottom=10
    ))
    styles.add(ParagraphStyle(
        name='AltBaslik',
        fontName='Verdana' if font_registered else 'Helvetica',
        fontSize=11,
        alignment=TA_LEFT,
        spaceBottom=5
    ))
    styles.add(ParagraphStyle(
        name='TabloIci',
        fontName='Verdana' if font_registered else 'Helvetica',
        fontSize=9
    ))
except Exception as e:
    print(f"PDF Font hatası: {e}")


# ---


class SeatPlanView(QWidget):
    """
    MainDashboard içerik alanında çalışan 'Oturma Planı' ekranı.
    Ayrı pencere açmaz; tek bir QWidget’tır.
    """

    def __init__(self, user, permission_manager, parent=None):
        super().__init__(parent)
        self.user = user
        self.pm = permission_manager
        self.current_exam_id = None
        self.current_room = None
        self.rooms = []
        self._build_ui()
        self._load_exams()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Üst başlık
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27ae60, stop:1 #16a085);
                border-radius: 12px;
            }
            QLabel { color:white; }
        """)
        hl = QHBoxLayout(header);
        hl.setContentsMargins(18, 14, 18, 14)
        title = QLabel("💺 Oturma Planı")
        title.setStyleSheet("font-size:20px; font-weight:700;")
        hl.addWidget(title);
        hl.addStretch()

        self.btn_generate = QPushButton("⚙️ Plan Oluştur/Güncelle")
        self.btn_generate.clicked.connect(self._generate_plan)
        self.btn_generate.setCursor(Qt.PointingHandCursor)

        self.btn_pdf = QPushButton("⬇️ PDF İndir")
        self.btn_pdf.clicked.connect(self._export_pdf)
        self.btn_pdf.setCursor(Qt.PointingHandCursor)

        hl.addWidget(self.btn_generate)
        hl.addWidget(self.btn_pdf)
        root.addWidget(header)

        # Filtre/Seçim çubuğu
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame { background:#ffffff; border:2px solid #ecf0f1; border-radius:12px; }
            QComboBox { border:2px solid #bdc3c7; border-radius:8px; padding:6px 10px; background:white; }
        """)
        tl = QHBoxLayout(toolbar);
        tl.setContentsMargins(14, 12, 14, 12)

        self.cmb_exam = QComboBox()
        self.cmb_exam.currentIndexChanged.connect(self._on_exam_changed)

        self.cmb_room = QComboBox()
        self.cmb_room.currentIndexChanged.connect(self._on_room_changed)

        tl.addWidget(QLabel("Sınav:"));
        tl.addWidget(self.cmb_exam, 4)
        tl.addSpacing(10)
        tl.addWidget(QLabel("Derslik:"));
        tl.addWidget(self.cmb_room, 3)
        root.addWidget(toolbar)

        # Sınav-Derslik listesi (seçilen sınavın tüm salonları)
        table_wrap = QFrame()
        table_wrap.setStyleSheet("QFrame { background:white; border:2px solid #ecf0f1; border-radius:12px; }")
        tv = QVBoxLayout(table_wrap);
        tv.setContentsMargins(10, 10, 10, 10)

        self.tbl_rooms = QTableWidget(0, 4)
        self.tbl_rooms.setHorizontalHeaderLabels(["Derslik", "Kapasite", "Enine×Boyuna×Yapı", "Atanan Öğrenci"])
        self.tbl_rooms.horizontalHeader().setStretchLastSection(True)
        self.tbl_rooms.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_rooms.setEditTriggers(self.tbl_rooms.NoEditTriggers)
        self.tbl_rooms.setSelectionBehavior(self.tbl_rooms.SelectRows)
        self.tbl_rooms.itemSelectionChanged.connect(self._on_table_select)

        tv.addWidget(self.tbl_rooms)
        root.addWidget(table_wrap)

        # Önizleme (SeatMapWidget)
        preview_wrap = QFrame()
        preview_wrap.setStyleSheet("QFrame { background:white; border:2px solid #ecf0f1; border-radius:12px; }")
        pv = QVBoxLayout(preview_wrap);
        pv.setContentsMargins(12, 12, 12, 12);
        pv.setSpacing(10)

        self.preview_title = QLabel("Önizleme")
        self.preview_title.setStyleSheet("font-size:14px; font-weight:700; color:#2c3e50;")
        pv.addWidget(self.preview_title)

        self.preview = SeatMapWidget(enine=6, boyuna=10, yapi=3, kapasite=180)  # varsayılan; seçimde güncellenecek
        pv.addWidget(self.preview)
        root.addWidget(preview_wrap)

    # ---------- Data ----------
    def _load_exams(self):
        # Admin ise tüm sınavlar, değilse kendi bölümüne göre
        if self.pm.can_manage_all_departments():
            rows = Database.execute_query("""
                SELECT s.sinav_id,
                       s.sinav_tarihi,
                       s.sinav_saati,
                       s.sinav_turu,
                       d.ders_kodu,
                       d.ders_adi
                FROM sinavlar s
                JOIN dersler d ON d.ders_id = s.ders_id
                ORDER BY s.sinav_tarihi, s.sinav_saati
            """)
        else:
            rows = Database.execute_query("""
                SELECT s.sinav_id,
                       s.sinav_tarihi,
                       s.sinav_saati,
                       s.sinav_turu,
                       d.ders_kodu,
                       d.ders_adi
                FROM sinavlar s
                JOIN dersler d ON d.ders_id = s.ders_id
                WHERE s.bolum_id = %s
                ORDER BY s.sinav_tarihi, s.sinav_saati
            """, (self.user["bolum_id"],))

        self.cmb_exam.clear()
        for r in rows or []:
            # ekranda gösterilecek etiket
            saat_str = r["sinav_saati"].strftime('%H:%M') if r["sinav_saati"] else "--:--"
            tarih_str = r["sinav_tarihi"].strftime('%d.%m.%Y') if r["sinav_tarihi"] else "---"
            label = f"{r['ders_kodu']} – {r['ders_adi']} ({r['sinav_turu']}) — {tarih_str} {saat_str}"
            self.cmb_exam.addItem(label, r["sinav_id"])

        if rows:
            self._on_exam_changed(0)

    def _on_exam_changed(self, _):
        self.current_exam_id = self.cmb_exam.currentData()
        self._load_rooms_for_exam()

    def _load_rooms_for_exam(self):
        if not self.current_exam_id:
            self.rooms = []
            self.cmb_room.clear()
            self.tbl_rooms.setRowCount(0)
            return

        self.rooms = Database.execute_query("""
            SELECT d.derslik_id, d.derslik_kodu, d.derslik_adi, d.kapasite,
                   d.enine_sira_sayisi, d.boyuna_sira_sayisi, d.sira_yapisi,
                   COALESCE((
                     SELECT COUNT(*)
                     FROM oturmaplani op
                     WHERE op.sinav_id = sd.sinav_id AND op.derslik_id = d.derslik_id
                   ),0) AS atanan
            FROM sinavderslikleri sd
            JOIN derslikler d ON d.derslik_id = sd.derslik_id
            WHERE sd.sinav_id = %s
            ORDER BY d.derslik_kodu
        """, (self.current_exam_id,)) or []

        # combobox
        self.cmb_room.clear()
        for r in self.rooms:
            self.cmb_room.addItem(f"{r['derslik_kodu']} (Kapasite: {r['kapasite']})", r)  # data=r

        # tablo
        self.tbl_rooms.setRowCount(0)
        for r in self.rooms:
            row = self.tbl_rooms.rowCount();
            self.tbl_rooms.insertRow(row)
            self.tbl_rooms.setItem(row, 0, QTableWidgetItem(f"{r['derslik_kodu']} - {r.get('derslik_adi') or ''}"))
            self.tbl_rooms.setItem(row, 1, QTableWidgetItem(str(r['kapasite'])))
            self.tbl_rooms.setItem(
                row, 2,
                QTableWidgetItem(f"{r['enine_sira_sayisi']}×{r['boyuna_sira_sayisi']} × {r['sira_yapisi']}'li")
            )
            self.tbl_rooms.setItem(row, 3, QTableWidgetItem(str(r['atanan'])))

        if self.rooms:
            self._on_room_changed(0)  # İlk dersliği seç
        else:
            self.current_room = None
            self._apply_preview(None)  # Önizlemeyi temizle

    def _on_table_select(self):
        r = self.tbl_rooms.currentRow()
        if r < 0 or r >= len(self.rooms): return
        data = self.rooms[r]
        # ComboBox'ı da senkronize et
        for i in range(self.cmb_room.count()):
            if self.cmb_room.itemData(i)['derslik_id'] == data['derslik_id']:
                self.cmb_room.setCurrentIndex(i)
                break
        self._apply_preview(data)

    def _on_room_changed(self, _):
        data = self.cmb_room.currentData()
        if data:
            self._apply_preview(data)

    def _apply_preview(self, data):
        self.current_room = data

        # Eski widget'ı değiştir (önceki hatayı önlemek için)
        if hasattr(self, 'preview') and self.preview:
            parent = self.preview.parent()
            if parent:
                parent.layout().removeWidget(self.preview)
            self.preview.deleteLater()

        if data is None:
            self.preview_title.setText("Önizleme (Derslik seçilmedi)")
            self.preview = SeatMapWidget(enine=1, boyuna=1, yapi=1, kapasite=0)
        else:
            enine = int(data['enine_sira_sayisi'])
            yapi = int(data['sira_yapisi'])
            kapasite = int(data['kapasite'])

            # PDF kuralına göre efektif satır sayısı
            seats_per_row = enine * yapi
            rows_needed = max(1, math.ceil(kapasite / seats_per_row))

            self.preview_title.setText(
                f"Önizleme — {data['derslik_kodu']} ({kapasite})  "
                f"Oturma Düzeni: {rows_needed} satır × {enine} sıra grubu, {yapi}'li"
            )
            self.preview = SeatMapWidget(
                enine=enine,
                boyuna=rows_needed,  # kapasiteye göre hesaplanan
                yapi=yapi,
                kapasite=kapasite
            )

        # Yeni widget'ı ekle
        self.preview_title.parent().layout().addWidget(self.preview)

    # ---------- Actions ----------
    def _generate_plan(self):
        if not self.current_exam_id or not self.current_room:
            QMessageBox.warning(self, "Uyarı", "Lütfen sınav ve derslik seçiniz.")
            return
        try:
            # 1. Gerekli bilgileri al
            sinav_id = self.current_exam_id
            room = self.current_room
            derslik_id = room["derslik_id"]

            # 2. Sınava giren öğrencileri çek
            ogrenciler = Database.execute_query("""
                SELECT o.ogrenci_id
                FROM ogrencidersleri od
                JOIN sinavlar s ON s.ders_id = od.ders_id AND s.sinav_id = %s
                JOIN ogrenciler o ON o.ogrenci_id = od.ogrenci_id
                ORDER BY o.ogrenci_no
            """, (sinav_id,))

            if not ogrenciler:
                QMessageBox.warning(self, "Uyarı", "Bu sınava kayıtlı öğrenci bulunamadı.")
                return

            # 3. Derslik bilgilerini al
            enine = int(room['enine_sira_sayisi'])  # Sütun (masa) sayısı
            boyuna = int(room['boyuna_sira_sayisi'])  # Satır (masa) sayısı
            yapi = int(room['sira_yapisi'])  # Bir masadaki koltuk sayısı
            kapasite = int(room['kapasite'])

            # 4. Eski planı temizle (Sadece bu sınav ve bu derslik için)
            Database.execute_non_query(
                "DELETE FROM oturmaplani WHERE sinav_id = %s AND derslik_id = %s",
                (sinav_id, derslik_id)
            )

            # 5. Yeni planı oluştur (Toplu insert için liste)
            plan_values = []
            ogr_index = 0

            for r in range(1, boyuna + 1):  # Satırlar (boyuna)
                for c in range(1, enine + 1):  # Sütunlar (enine)
                    for k in range(1, yapi + 1):  # Masadaki koltuklar (yapi)

                        # Öğrenci bittiyse veya derslik kapasitesi dolduysa dur
                        if ogr_index >= len(ogrenciler) or len(plan_values) >= kapasite:
                            break

                        ogrenci_id = ogrenciler[ogr_index]['ogrenci_id']

                        # (sinav_id, ogrenci_id, derslik_id, sira_no, sutun_no, koltuk_no)
                        plan_values.append(
                            (sinav_id, ogrenci_id, derslik_id, r, c, k)
                        )
                        ogr_index += 1

                    if ogr_index >= len(ogrenciler) or len(plan_values) >= kapasite: break
                if ogr_index >= len(ogrenciler) or len(plan_values) >= kapasite: break

            # 6. Veritabanına toplu kayıt
            if plan_values:
                Database.execute_many("""
                    INSERT INTO oturmaplani (sinav_id, ogrenci_id, derslik_id, sira_no, sutun_no, koltuk_no)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sinav_id, ogrenci_id) DO NOTHING
                """, plan_values)

            QMessageBox.information(self, "Başarılı", f"{len(plan_values)} öğrenci bu dersliğe yerleştirildi.")
            self._load_rooms_for_exam()  # Tabloyu yenile

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Plan oluşturulurken hata:\n{e}")

    def _export_pdf(self):
        if not self.current_exam_id or not self.current_room:
            QMessageBox.warning(self, "Uyarı", "Lütfen sınav ve derslik seçiniz.")
            return

        try:
            # 1. Kayıt yeri seç
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Oturma Planı PDF Kaydet",
                f"OturmaPlani_{self.current_room['derslik_kodu']}.pdf",
                "PDF Dosyası (*.pdf)"
            )
            if not path:
                return

            # 2. Başlık bilgileri
            header = Database.execute_query("""
                SELECT 
                    s.sinav_tarihi, s.sinav_saati, s.sinav_turu,
                    d.ders_kodu, d.ders_adi,
                    dl.derslik_kodu, dl.derslik_adi
                FROM sinavlar s
                JOIN dersler d    ON d.ders_id = s.ders_id
                JOIN derslikler dl ON dl.derslik_id = %s
                WHERE s.sinav_id = %s
            """, (self.current_room["derslik_id"], self.current_exam_id))
            if not header:
                QMessageBox.warning(self, "Uyarı", "Başlık bilgileri bulunamadı.");
                return
            h = header[0]

            # 3. Oturma planı listesi
            rows = Database.execute_query("""
                SELECT op.sira_no, op.sutun_no, op.koltuk_no,
                       o.ogrenci_no,
                       o.ad_soyad
                FROM oturmaplani op
                JOIN ogrenciler o ON o.ogrenci_id = op.ogrenci_id
                WHERE op.sinav_id = %s AND op.derslik_id = %s
                ORDER BY op.sira_no, op.sutun_no, op.koltuk_no
            """, (self.current_exam_id, self.current_room["derslik_id"])) or []

            # 4. PDF Oluşturma
            doc = SimpleDocTemplate(path, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
            story = []
            styles = getSampleStyleSheet()

            # Başlık
            story.append(Paragraph("SINAV OTURMA PLANI", styles['Baslik']))
            story.append(Paragraph(f"<b>Ders:</b> {h['ders_kodu']} - {h['ders_adi']}", styles['AltBaslik']))
            story.append(Paragraph(f"<b>Sınav Türü:</b> {h['sinav_turu']}", styles['AltBaslik']))
            story.append(
                Paragraph(f"<b>Derslik:</b> {h['derslik_kodu']} - {h.get('derslik_adi', '')}", styles['AltBaslik']))
            saat_str = h["sinav_saati"].strftime('%H:%M') if h["sinav_saati"] else "--:--"
            tarih_str = h["sinav_tarihi"].strftime('%d.%m.%Y') if h["sinav_tarihi"] else "---"
            story.append(Paragraph(f"<b>Tarih / Saat:</b> {tarih_str} / {saat_str}", styles['AltBaslik']))

            # Ayraç
            story.append(Paragraph("<hr/>", styles['Normal']))

            # Tablo Verisi
            data = [
                ["Sıra", "Sütun (Masa)", "Koltuk", "Öğrenci No", "Ad Soyad"]
            ]

            style_tablo_ici = styles['TabloIci']

            for r in rows:
                data.append([
                    Paragraph(str(r['sira_no']), style_tablo_ici),
                    Paragraph(str(r['sutun_no']), style_tablo_ici),
                    Paragraph(str(r['koltuk_no']), style_tablo_ici),
                    Paragraph(str(r['ogrenci_no']), style_tablo_ici),
                    Paragraph(r['ad_soyad'], style_tablo_ici)
                ])

            if len(data) == 1:
                story.append(Paragraph("Bu dersliğe atanmış öğrenci bulunamadı.", styles['AltBaslik']))
            else:
                # Tablo Stili
                ts = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#27ae60")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Verdana' if font_registered else 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke, 0, (0, -1)),  # (Satır indeksi % 2 == 0)
                    ('BACKGROUND', (0, 2), (-1, -1), colors.white, 0, (1, -1)),  # (Satır indeksi % 2 == 1)
                ])

                # Alternatif satır renkleri için döngü
                for i in range(1, len(data)):
                    if i % 2 == 0:
                        ts.add('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F0F0F0"))
                    else:
                        ts.add('BACKGROUND', (0, i), (-1, i), colors.white)

                # Tabloyu oluştur
                table = Table(data, colWidths=[2 * cm, 2.5 * cm, 2 * cm, 3 * cm, 6.5 * cm])
                table.setStyle(ts)
                story.append(table)

            # PDF'i oluştur
            doc.build(story)
            QMessageBox.information(self, "Başarılı", f"PDF başarıyla kaydedildi:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "PDF Hatası", f"PDF oluşturulamadı:\n{e}")