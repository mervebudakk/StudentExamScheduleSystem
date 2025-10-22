# student_system/views/seat_plan.py
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from student_system.core.database import Database
from student_system.views.classroom_seatmap import SeatMapWidget  # görsel önizleme için
import math
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
        hl = QHBoxLayout(header); hl.setContentsMargins(18, 14, 18, 14)
        title = QLabel("💺 Oturma Planı")
        title.setStyleSheet("font-size:20px; font-weight:700;")
        hl.addWidget(title); hl.addStretch()

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
        tl = QHBoxLayout(toolbar); tl.setContentsMargins(14, 12, 14, 12)

        self.cmb_exam = QComboBox()
        self.cmb_exam.currentIndexChanged.connect(self._on_exam_changed)

        self.cmb_room = QComboBox()
        self.cmb_room.currentIndexChanged.connect(self._on_room_changed)

        tl.addWidget(QLabel("Sınav:")); tl.addWidget(self.cmb_exam, 4)
        tl.addSpacing(10)
        tl.addWidget(QLabel("Derslik:")); tl.addWidget(self.cmb_room, 3)
        root.addWidget(toolbar)

        # Sınav-Derslik listesi (seçilen sınavın tüm salonları)
        table_wrap = QFrame()
        table_wrap.setStyleSheet("QFrame { background:white; border:2px solid #ecf0f1; border-radius:12px; }")
        tv = QVBoxLayout(table_wrap); tv.setContentsMargins(10,10,10,10)

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
        pv = QVBoxLayout(preview_wrap); pv.setContentsMargins(12,12,12,12); pv.setSpacing(10)

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
            saat = str(r["sinav_saati"])[:5] if r["sinav_saati"] is not None else "--:--"
            label = f"{r['ders_kodu']} – {r['ders_adi']} ({r['sinav_turu']}) — {r['sinav_tarihi']} {saat}"
            self.cmb_exam.addItem(label, r["sinav_id"])

        if rows:
            self._on_exam_changed(0)

    def _on_exam_changed(self, _):
        self.current_exam_id = self.cmb_exam.currentData()
        self._load_rooms_for_exam()

    def _load_rooms_for_exam(self):
        self.rooms = Database.execute_query("""
            SELECT d.derslik_id, d.derslik_kodu, d.derslik_adi, d.kapasite,
                   d.enine_sira_sayisi, d.boyuna_sira_sayisi, d.sira_yapisi,
                   COALESCE((
                     SELECT COUNT(*)
                     FROM oturmaplani op
                     WHERE op.sinav_id = %s AND op.derslik_id = d.derslik_id
                   ),0) AS atanan
            FROM sinavderslikleri sd          -- <<< DÜZELTİLDİ
            JOIN derslikler d ON d.derslik_id = sd.derslik_id
            WHERE sd.sinav_id = %s
            ORDER BY d.derslik_kodu
        """, (self.current_exam_id, self.current_exam_id)) or []

        # combobox
        self.cmb_room.clear()
        for r in self.rooms:
            self.cmb_room.addItem(r["derslik_kodu"], r)

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
            self._on_room_changed(0)

    def _on_table_select(self):
        r = self.tbl_rooms.currentRow()
        if r < 0: return
        data = self.rooms[r]
        self._apply_preview(data)

    def _on_room_changed(self, _):
        data = self.cmb_room.currentData()
        if data:
            self._apply_preview(data)

    def _apply_preview(self, data):
        self.current_room = data

        enine = int(data['enine_sira_sayisi'])  # sıra grubu sayısı (kolon)
        yapi = int(data['sira_yapisi'])  # 2'li / 3'lü
        kapasite = int(data['kapasite'])

        # PDF kuralına göre efektif satır sayısı
        seats_per_row = enine * yapi  # her satırdaki oturak
        rows_needed = max(1, math.ceil(kapasite / seats_per_row))

        # Başlık
        self.preview_title.setText(
            f"Önizleme — {data['derslik_kodu']} ({kapasite})  "
            f"Oturma Düzeni: {rows_needed} satır × {enine} sıra grubu, {yapi}'li"
        )

        # Eski widget'ı değiştir
        parent = self.preview.parent()
        parent.layout().removeWidget(self.preview)
        self.preview.deleteLater()

        # SeatMapWidget kapasiteye göre çizsin: boyuna=rows_needed gönderiyoruz
        self.preview = SeatMapWidget(
            enine=enine,
            boyuna=rows_needed,  # <<< kritik: veri 'boyuna' yerine kapasiteye göre
            yapi=yapi,
            kapasite=kapasite
        )
        parent.layout().addWidget(self.preview)

    # ---------- Actions ----------
    def _generate_plan(self):
        if not self.current_exam_id or not self.current_room:
            QMessageBox.warning(self, "Uyarı", "Lütfen sınav ve derslik seçiniz.")
            return
        try:
            sql = """
            WITH P AS (
              SELECT 
                s.sinav_id,
                d.derslik_id,
                d.enine_sira_sayisi AS cols,
                d.boyuna_sira_sayisi AS rows,
                d.kapasite
              FROM sinavlar s
              JOIN derslikler d ON d.derslik_id = %(derslik_id)s
              WHERE s.sinav_id = %(sinav_id)s
            ),
            OGRENCI AS (
              SELECT o.ogrenci_id,
                     ROW_NUMBER() OVER (ORDER BY o.ogrenci_no) AS rn
              FROM ogrencidersleri od
              JOIN sinavlar s ON s.sinav_id = %(sinav_id)s AND s.ders_id = od.ders_id
              JOIN ogrenciler o ON o.ogrenci_id = od.ogrenci_id
            ),
            KOLTUK AS (
              SELECT 
                (g.i / (SELECT cols FROM P)) + 1 AS sira_no,
                (g.i % (SELECT cols FROM P)) + 1 AS sutun_no,
                ROW_NUMBER() OVER (ORDER BY g.i) AS rn
              FROM generate_series(0, (SELECT (rows*cols) FROM P) - 1) g(i)
            ),
            SECIM AS (
              SELECT 
                (SELECT sinav_id FROM P)   AS sinav_id,
                (SELECT derslik_id FROM P) AS derslik_id,
                K.sira_no, K.sutun_no, O.ogrenci_id
              FROM KOLTUK K
              JOIN OGRENCI O ON O.rn = K.rn
              WHERE K.rn <= LEAST( (SELECT rows*cols FROM P), (SELECT kapasite FROM P) )
            )
            INSERT INTO oturmaplani (sinav_id, ogrenci_id, derslik_id, sira_no, sutun_no, olusturma_tarihi)
            SELECT sinav_id, ogrenci_id, derslik_id, sira_no, sutun_no, NOW()
            FROM SECIM
            ON CONFLICT (sinav_id, derslik_id, ogrenci_id)
            DO UPDATE SET
              sira_no = EXCLUDED.sira_no,
              sutun_no = EXCLUDED.sutun_no,
              olusturma_tarihi = NOW();
            """
            Database.execute_query(sql, {
                "sinav_id": self.current_exam_id,
                "derslik_id": self.current_room["derslik_id"],
            })
            QMessageBox.information(self, "Başarılı", "Oturma planı oluşturuldu/güncellendi.")
            self._load_rooms_for_exam()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Plan oluşturulurken hata:\n{e}")

    def _export_pdf(self):
        if not self.current_exam_id or not self.current_room:
            QMessageBox.warning(self, "Uyarı", "Lütfen sınav ve derslik seçiniz.")
            return
        try:
            # 1) Başlık bilgileri (ders, tarih, saat, sınav türü, derslik)
            header = Database.execute_query("""
                SELECT 
                    s.sinav_id, s.sinav_tarihi, s.sinav_saati, s.sinav_turu,
                    d2.ders_kodu, d2.ders_adi,
                    dl.derslik_kodu, dl.derslik_adi,
                    dl.enine_sira_sayisi, dl.boyuna_sira_sayisi, dl.sira_yapisi, dl.kapasite
                FROM sinavlar s
                JOIN dersler d2    ON d2.ders_id = s.ders_id
                JOIN derslikler dl ON dl.derslik_id = %s
                WHERE s.sinav_id = %s
            """, (self.current_room["derslik_id"], self.current_exam_id))
            if not header:
                QMessageBox.warning(self, "Uyarı", "Başlık bilgileri bulunamadı.")
                return
            h = header[0]

            # 2) Oturma planı listesi (sıra/sütun + öğrenci)
            rows = Database.execute_query("""
                SELECT op.sira_no, op.sutun_no,
                       o.ogrenci_no,
                       (o.ad || ' ' || o.soyad) AS ogrenci_adi
                FROM oturmaplani op
                JOIN ogrenciler o ON o.ogrenci_id = op.ogrenci_id
                WHERE op.sinav_id = %s AND op.derslik_id = %s
                ORDER BY op.sira_no, op.sutun_no
            """, (self.current_exam_id, self.current_room["derslik_id"])) or []

            # 3) PDF düzen bilgisi (kapasiteye göre satır hesapla)
            enine = int(h["enine_sira_sayisi"])
            yapi = int(h["sira_yapisi"])
            kapasite = int(h["kapasite"])
            seats_per_row = enine * yapi
            rows_needed = max(1, math.ceil(kapasite / seats_per_row))

            # 4) Şimdilik doğrulama - (sonraki adımda ReportLab ile gerçek PDF basacağız)
            QMessageBox.information(
                self, "PDF",
                f"PDF verisi hazırlandı.\n\n"
                f"Ders: {h['ders_kodu']} – {h['ders_adi']} ({h['sinav_turu']})\n"
                f"Tarih/Saat: {h['sinav_tarihi']} {str(h['sinav_saati'])[:5]}\n"
                f"Derslik: {h['derslik_kodu']} – {h.get('derslik_adi') or ''}\n"
                f"Düzen: {rows_needed} satır × {enine} grup × {yapi}'li (kapasite: {kapasite})\n"
                f"Atanan öğrenci: {len(rows)}"
            )
            # TODO:
            # - Kapı etiketi
            # - Yerleşim şeması (rows_needed × enine, grup başına yapi adet)
            # - Öğrenci listesi (sira_no, sutun_no, ogrenci_no, ogrenci_adi)
            # için ReportLab/WeasyPrint ile gerçek PDF çıktısı oluştur

        except Exception as e:
            QMessageBox.critical(self, "PDF Hatası", f"PDF oluşturulamadı:\n{e}")

