# student_system/views/seat_plan.py
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from student_system.core.database import Database
from student_system.views.classroom_seatmap import SeatMapWidget  # görsel önizleme için

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
        # Kullanıcının bölümüne göre filtrele (admin ise tümü)
        if self.pm.can_manage_all_departments():
            rows = Database.execute_query("""
                SELECT s.sinav_id, s.sinav_adi, s.sinav_tarihi, s.baslangic_saati
                FROM sinavlar s
                ORDER BY s.sinav_tarihi, s.baslangic_saati
            """)
        else:
            rows = Database.execute_query("""
                SELECT s.sinav_id, s.sinav_adi, s.sinav_tarihi, s.baslangic_saati
                FROM sinavlar s
                WHERE s.bolum_id = %s
                ORDER BY s.sinav_tarihi, s.baslangic_saati
            """, (self.user["bolum_id"],))

        self.cmb_exam.clear()
        for r in rows or []:
            label = f"{r['sinav_adi']} — {r['sinav_tarihi']} {str(r['baslangic_saati'])[:5]}"
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
                     FROM oturma_plani op
                     WHERE op.sinav_id = %s AND op.derslik_id = d.derslik_id
                   ),0) AS atanan
            FROM sinav_derslikleri sd
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
            row = self.tbl_rooms.rowCount(); self.tbl_rooms.insertRow(row)
            self.tbl_rooms.setItem(row, 0, QTableWidgetItem(f"{r['derslik_kodu']} - {r.get('derslik_adi') or ''}"))
            self.tbl_rooms.setItem(row, 1, QTableWidgetItem(str(r['kapasite'])))
            self.tbl_rooms.setItem(row, 2, QTableWidgetItem(f"{r['enine_sira_sayisi']}×{r['boyuna_sira_sayisi']}×{r['sira_yapisi']}"))
            self.tbl_rooms.setItem(row, 3, QTableWidgetItem(str(r['atanan'])))

        # varsayılan seçim
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
        self.preview_title.setText(f"Önizleme — {data['derslik_kodu']} ({data['kapasite']})")
        # SeatMapWidget’ı güncellemek için yeni bir instance yaratmak en kolayı:
        parent = self.preview.parent()
        parent.layout().removeWidget(self.preview)
        self.preview.deleteLater()
        self.preview = SeatMapWidget(
            enine=data['enine_sira_sayisi'],
            boyuna=data['boyuna_sira_sayisi'],
            yapi=data['sira_yapisi'],
            kapasite=data['kapasite']
        )
        parent.layout().addWidget(self.preview)

    # ---------- Actions ----------
    def _generate_plan(self):
        if not self.current_exam_id or not self.current_room:
            QMessageBox.warning(self, "Uyarı", "Lütfen sınav ve derslik seçiniz."); return

        # Buraya yerleştirme algoritmanızı çağırın:
        # 1) sinav_id için öğrencileri çek
        # 2) kapasite ve kısıtlara göre oturma_plani’na yaz
        # 3) atanan sayısını güncelle
        # Şimdilik sadece iskelet:
        try:
            # TODO: yerleştirme SQL/algoritma entegrasyonu
            QMessageBox.information(self, "Bilgi", "Oturma planı oluşturuldu/güncellendi (örnek).")
            self._load_rooms_for_exam()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Plan oluşturulurken hata:\n{e}")

    def _export_pdf(self):
        if not self.current_exam_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir sınav seçiniz."); return
        try:
            # TODO: ReportLab / WeasyPrint ile PDF üretimini burada yapacağız
            # - Salon oturma planı
            # - Gözetmen listesi
            # - Kapı etiketi
            QMessageBox.information(self, "PDF", "PDF üretimi (örnek). Birazdan dolduracağız.")
        except Exception as e:
            QMessageBox.critical(self, "PDF Hatası", f"PDF oluşturulamadı:\n{e}")
