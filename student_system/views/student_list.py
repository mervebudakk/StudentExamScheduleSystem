import re
import unicodedata
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QProgressBar, \
    QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QTextEdit, QHeaderView, QFrame
from PyQt5.QtGui import QFont
from student_system.core.database import Database

HEADER_SYNONYMS = {
    'ogrenci_no': {'ogrenci no', 'ogrencino', 'ogrenci_numarasi', 'numara', 'öğrenci no', 'öğrenci numarası', 'no'},
    'ad_soyad': {'ad soyad', 'ogrenci ad soyad', 'öğrenci adı', 'öğrenci isim', 'isim', 'ad', 'soyad'},
    'sinif': {'sınıf', 'sinif', 'ogrenci sinifi', 'öğrenci sınıfı', 'ogrenci sınıf'},
    'ders': {'ders', 'ders kodu', 'derskodu', 'dersin kodu', 'kod'}
}


def normalize(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return s.strip()


def canonical_header(cell_text: str):
    key = normalize(cell_text)
    for canonical, variants in HEADER_SYNONYMS.items():
        if key in {normalize(v) for v in variants}:
            return canonical
    return None


class StudentUploadWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, students, bolum_id):
        super().__init__()
        self.students = students
        self.bolum_id = bolum_id

    def run(self):
        try:
            inserted_students = 0
            inserted_relations = 0

            ogrenci_values = [
                (s["ogrenci_no"], s["ad_soyad"], self.bolum_id, s["sinif"])
                for s in self.students
            ]
            Database.execute_many("""
                INSERT INTO ogrenciler (ogrenci_no, ad_soyad, bolum_id, sinif)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ogrenci_no) DO NOTHING
            """, ogrenci_values)

            ogrenci_map = {
                row["ogrenci_no"]: row["ogrenci_id"]
                for row in Database.execute_query("SELECT ogrenci_id, ogrenci_no FROM ogrenciler WHERE bolum_id = %s",
                                                  (self.bolum_id,))
            }

            ders_map = {
                row["ders_kodu"]: row["ders_id"]
                for row in
                Database.execute_query("SELECT ders_id, ders_kodu FROM dersler WHERE bolum_id = %s", (self.bolum_id,))
            }

            relation_values = []
            for idx, s in enumerate(self.students):
                ogr_id = ogrenci_map.get(s["ogrenci_no"])
                ders_id = ders_map.get(s["ders_kodu"])
                if ogr_id and ders_id:
                    relation_values.append((ogr_id, ders_id))

                if idx % 100 == 0:
                    self.progress.emit(int(idx / len(self.students) * 100))

            Database.execute_many("""
                INSERT INTO ogrencidersleri (ogrenci_id, ders_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
            """, relation_values)

            inserted_students = len(ogrenci_values)
            inserted_relations = len(relation_values)
            self.progress.emit(100)
            self.finished.emit(inserted_students, inserted_relations)

        except Exception as e:
            self.error.emit(str(e))


class StudentListUploader(QWidget):
    def load_students(self):
        students = Database.execute_query("""
            SELECT ogrenci_no, ad_soyad, sinif
            FROM ogrenciler
            WHERE bolum_id = %s
            ORDER BY ogrenci_no
        """, (self.user["bolum_id"],))
        self.table.setRowCount(len(students))
        for row, s in enumerate(students):
            self.table.setItem(row, 0, QTableWidgetItem(str(s["ogrenci_no"])))
            self.table.setItem(row, 1, QTableWidgetItem(s["ad_soyad"]))
            self.table.setItem(row, 2, QTableWidgetItem(str(s["sinif"])))

    def search_student(self):
        ogr_no = self.search_box.text().strip()
        if not ogr_no:
            self.show_warning("Uyarı", "Lütfen bir öğrenci numarası girin.")
            return

        ogrenci = Database.execute_query("""
            SELECT ogrenci_id, ad_soyad FROM ogrenciler
            WHERE ogrenci_no = %s AND bolum_id = %s
        """, (ogr_no, self.user["bolum_id"]))

        if not ogrenci:
            self.result_area.setHtml(
                "<div style='color: #e74c3c; font-size: 15px; padding: 15px;'>❌ Öğrenci bulunamadı.</div>")
            return

        ogr = ogrenci[0]
        dersler = Database.execute_query("""
            SELECT d.ders_adi, d.ders_kodu
            FROM ogrencidersleri od
            JOIN dersler d ON od.ders_id = d.ders_id
            WHERE od.ogrenci_id = %s
            ORDER BY d.ders_kodu
        """, (ogr["ogrenci_id"],))

        html = f"""
        <div style='padding: 15px; font-family: Segoe UI;'>
            <div style='color: #16a085; font-size: 16px; font-weight: bold; margin-bottom: 12px;'>
                👤 Öğrenci: {ogr['ad_soyad']}
            </div>
            <div style='color: #2c3e50; font-size: 15px; font-weight: 600; margin-bottom: 8px;'>
                📘 Aldığı Dersler:
            </div>
        """

        if dersler:
            for d in dersler:
                html += f"""
                <div style='color: #34495e; font-size: 14px; margin-left: 20px; margin-bottom: 4px;'>
                    • {d['ders_adi']} <span style='color: #7f8c8d;'>(Kodu: {d['ders_kodu']})</span>
                </div>
                """
        else:
            html += "<div style='color: #95a5a6; font-size: 14px; margin-left: 20px;'>📭 Bu öğrenciye ait ders kaydı yok.</div>"

        html += "</div>"
        self.result_area.setHtml(html)

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27ae60, stop:1 #16a085);
                border-radius: 12px;
                padding: 15px;
            }
        """)
        title_layout = QVBoxLayout(title_frame)

        self.title = QLabel(f"🎓 {self.user['bolum_adi']} - Öğrenci Listesi")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 22px; font-weight: bold; color: white; background: transparent;")
        title_layout.addWidget(self.title)

        layout.addWidget(title_frame)

        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        search_layout = QHBoxLayout(search_frame)
        search_layout.setSpacing(10)

        search_label = QLabel("🔍")
        search_label.setStyleSheet("font-size: 20px; background: transparent; border: none;")

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Öğrenci numarasını girin...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 12px 15px;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 2px solid #16a085;
                background-color: white;
            }
        """)
        self.search_box.returnPressed.connect(self.search_student)

        search_button = QPushButton("Ara")
        search_button.setCursor(Qt.PointingHandCursor)
        search_button.clicked.connect(self.search_student)
        search_button.setFixedHeight(45)
        search_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16a085, stop:1 #138d75);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0 25px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #138d75, stop:1 #117a65);
            }
            QPushButton:pressed {
                background: #0e6655;
            }
        """)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box, 1)
        search_layout.addWidget(search_button)

        layout.addWidget(search_frame)

        table_label = QLabel("📋 Kayıtlı Öğrenciler")
        table_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-top: 10px;")
        layout.addWidget(table_label)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Öğrenci No", "Ad Soyad", "Sınıf"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 10px;
                gridline-color: #ecf0f1;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px;
                color: #2c3e50;
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #16a085, stop:1 #138d75);
                color: white;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27ae60, stop:1 #16a085);
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }
            QTableWidget::item:alternate {
                background-color: #f8f9fa;
            }
        """)
        layout.addWidget(self.table)

        result_label = QLabel("📄 Arama Sonucu")
        result_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-top: 10px;")
        layout.addWidget(result_label)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setMaximumHeight(180)
        self.result_area.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 10px;
                padding: 10px;
                font-size: 14px;
                color: #2c3e50;
            }
        """)
        layout.addWidget(self.result_area)

        self.upload_btn = QPushButton("📁 Excel Dosyası Seç ve Yükle")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.clicked.connect(self.upload_excel)
        self.upload_btn.setFixedHeight(50)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2980b9, stop:1 #21618c);
            }
            QPushButton:pressed {
                background: #1a5276;
            }
        """)
        layout.addWidget(self.upload_btn)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                background-color: #f8f9fa;
                height: 25px;
                color: #2c3e50;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27ae60, stop:0.5 #16a085, stop:1 #138d75);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress)

        # Başlangıçta tabloyu doldur
        self.load_students()

    def upload_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)")
        if not path:
            return

        try:
            df = pd.read_excel(path, header=0)
            students = self.parse_students(df)

            self.progress.setVisible(True)
            self.progress.setValue(0)

            self.worker = StudentUploadWorker(students, self.user["bolum_id"])
            self.worker.progress.connect(self.on_progress)
            self.worker.finished.connect(self.on_finished)
            self.worker.error.connect(self.on_error)
            self.worker.start()

        except Exception as e:
            self.show_error("Hata", f"Öğrenci listesi okunurken hata oluştu:\n{str(e)}")

    def parse_students(self, df: pd.DataFrame):
        colmap = {}
        for idx, col in enumerate(df.columns):
            key = canonical_header(col)
            if key and key not in colmap:
                colmap[key] = idx

        required = {"ogrenci_no", "ad_soyad", "sinif", "ders"}
        if not required.issubset(colmap.keys()):
            raise ValueError(f"Gerekli sütunlar eksik. Bulunanlar: {list(colmap.keys())}")

        students = []
        for _, row in df.iterrows():
            ogr_no = str(row[colmap["ogrenci_no"]]).strip()
            ad_soyad = str(row[colmap["ad_soyad"]]).strip()
            sinif_raw = str(row[colmap["sinif"]]).strip()
            ders_kodu = str(row[colmap["ders"]]).strip()

            if not ogr_no or not ad_soyad or not ders_kodu:
                continue

            m = re.search(r'(\d+)', sinif_raw)
            sinif_num = int(m.group(1)) if m else None

            students.append({
                "ogrenci_no": ogr_no,
                "ad_soyad": ad_soyad,
                "sinif": sinif_num,
                "ders_kodu": ders_kodu
            })

        return students

    def on_progress(self, value):
        self.progress.setValue(value)

    def on_finished(self, ogr_count, rel_count):
        self.progress.setVisible(False)
        self.show_success("Yükleme Tamamlandı",
                          f"📌 {ogr_count} öğrenci işlendi\n🔗 {rel_count} öğrenci-ders ilişkisi eklendi")
        self.load_students()

    def on_error(self, msg):
        self.progress.setVisible(False)
        self.show_error("Hata", f"Yükleme sırasında hata oluştu:\n{msg}")

    def show_error(self, title, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(f"❌ {title}")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #2c3e50;
                font-size: 13px;
                min-width: 300px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #c0392b, stop:1 #a93226);
            }
        """)
        msg.exec_()

    def show_success(self, title, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(f"✅ {title}")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #2c3e50;
                font-size: 13px;
                min-width: 300px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27ae60, stop:1 #229954);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #229954, stop:1 #1e8449);
            }
        """)
        msg.exec_()

    def show_warning(self, title, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle(f"⚠️ {title}")
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #2c3e50;
                font-size: 13px;
                min-width: 300px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f39c12, stop:1 #e67e22);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e67e22, stop:1 #d35400);
            }
        """)
        msg.exec_()