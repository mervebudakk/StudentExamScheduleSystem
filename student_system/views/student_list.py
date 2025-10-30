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
        self.show_student_details(ogr_no)

    def show_student_details(self, ogr_no):
        if not ogr_no:
            self.show_warning("Uyarı", "Lütfen bir öğrenci numarası girin.")
            return

        ogrenci = Database.execute_query("""
                SELECT ogrenci_id, ad_soyad FROM ogrenciler
                WHERE ogrenci_no = %s AND bolum_id = %s
            """, (ogr_no, self.user["bolum_id"]))

        if not ogrenci:
            self.result_area.setHtml(
                "<div style='color: #e74c3c; font-size: 14px; padding: 12px;'>❌ Öğrenci bulunamadı.</div>")
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
            <div style='padding: 12px; font-family: Segoe UI, Arial;'>
                <div style='color: #2ecc71; font-size: 15px; font-weight: 600; margin-bottom: 10px;'>
                    👤 Öğrenci: {ogr['ad_soyad']}
                </div>
                <div style='color: #34495e; font-size: 14px; font-weight: 600; margin-bottom: 6px;'>
                    📘 Aldığı Dersler:
                </div>
            """

        if dersler:
            for d in dersler:
                html += f"""
                    <div style='color: #34495e; font-size: 13px; margin-left: 16px; margin-bottom: 3px;'>
                        • {d['ders_adi']} <span style='color: #95a5a6;'>(Kodu: {d['ders_kodu']})</span>
                    </div>
                    """
        else:
            html += "<div style='color: #95a5a6; font-size: 13px; margin-left: 16px;'>📭 Bu öğrenciye ait ders kaydı yok.</div>"

        html += "</div>"
        self.result_area.setHtml(html)

    def filter_student_table(self, filter_text):
        filter_text = filter_text.strip()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                student_id = item.text()
                if not student_id.startswith(filter_text):
                    self.table.setRowHidden(row, True)
                else:
                    self.table.setRowHidden(row, False)

    def on_table_row_clicked(self, row, column):
        ogr_no_item = self.table.item(row, 0)
        if ogr_no_item:
            ogr_no = ogr_no_item.text()
            self.search_box.setText(ogr_no)
            self.show_student_details(ogr_no)

    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(18)

        title_label = QLabel(f"{self.user['bolum_adi']} - Öğrenci Listesi İşlemleri")
        title_label.setAlignment(Qt.AlignLeft)
        title_label.setStyleSheet("""
                font-size: 24px; 
                font-weight: 600; 
                color: #2c3e50; 
                margin-bottom: 5px;
                padding: 0;
            """)
        layout.addWidget(title_label)

        search_container = QFrame()
        search_container.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 0;
                }
            """)
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(15, 12, 15, 12)
        search_layout.setSpacing(10)

        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 18px; background: transparent; border: none; padding: 0;")

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Öğrenci numarası ara...")
        self.search_box.setStyleSheet("""
                QLineEdit {
                    padding: 10px 12px;
                    border: 1px solid #dcdde1;
                    border-radius: 6px;
                    font-size: 14px;
                    background-color: #f8f9fa;
                    color: #2c3e50;
                }
                QLineEdit:focus {
                    border: 1px solid #5dade2;
                    background-color: white;
                    outline: none;
                }
            """)

        self.search_box.returnPressed.connect(self.search_student)
        self.search_box.textChanged.connect(self.filter_student_table)

        search_btn = QPushButton("Ara")
        search_btn.setCursor(Qt.PointingHandCursor)
        search_btn.clicked.connect(self.search_student)
        search_btn.setFixedHeight(40)
        search_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5dade2;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0 24px;
                    font-size: 14px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #3498db;
                }
                QPushButton:pressed {
                    background-color: #2980b9;
                }
            """)

        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_box, 1)
        search_layout.addWidget(search_btn)

        layout.addWidget(search_container)

        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setMaximumHeight(160)
        self.result_area.setStyleSheet("""
                QTextEdit {
                    background-color: #f8f9fa;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 8px;
                    font-size: 13px;
                    color: #2c3e50;
                }
            """)
        layout.addWidget(self.result_area)

        table_header = QLabel("Kayıtlı Öğrenciler")
        table_header.setStyleSheet("font-size: 16px; font-weight: 600; color: #2c3e50; margin-top: 8px; padding: 0;")
        layout.addWidget(table_header)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Öğrenci No", "Ad Soyad", "Sınıf"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setStyleSheet("""
                QTableWidget {
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    gridline-color: #ecf0f1;
                    font-size: 13px;
                }
                QTableWidget::item {
                    padding: 10px;
                    color: #2c3e50;
                    border-bottom: 1px solid #f0f0f0;
                }
                QTableWidget::item:selected {
                    background-color: #e8f4f8;
                    color: #2c3e50;
                }
                QHeaderView::section {
                    background-color: #f5f6fa;
                    color: #2c3e50;
                    padding: 12px;
                    border: none;
                    border-bottom: 2px solid #dcdde1;
                    font-weight: 600;
                    font-size: 13px;
                    text-align: left;
                }
                QTableWidget::item:alternate {
                    background-color: #fafbfc;
                }
            """)

        self.table.cellClicked.connect(self.on_table_row_clicked)

        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.upload_btn = QPushButton("Excel Dosyası Yükle")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.clicked.connect(self.upload_excel)
        self.upload_btn.setFixedHeight(44)
        self.upload_btn.setStyleSheet("""
                QPushButton {
                    background: #5d6dfa;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 0px 24px;
                    font-size: 14px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #4c5de8;
                }
                QPushButton:pressed {
                    background: #3b4cd7;
                }
            """)

        save_btn = QPushButton("Kaydet")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2ecc71;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 500;
                    padding: 0 28px;
                }
                QPushButton:hover {
                    background-color: #27ae60;
                }
                QPushButton:pressed {
                    background-color: #229954;
                }
            """)

        cancel_btn = QPushButton("Vazgeç")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setFixedHeight(44)
        cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #7f8c8d;
                    border: 1px solid #bdc3c7;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 500;
                    padding: 0 28px;
                }
                QPushButton:hover {
                    background-color: #ecf0f1;
                    color: #5a6c7d;
                }
                QPushButton:pressed {
                    background-color: #dcdde1;
                }
            """)

        button_layout.addWidget(self.upload_btn)
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    text-align: center;
                    background-color: #f8f9fa;
                    height: 24px;
                    color: #2c3e50;
                    font-weight: 500;
                    font-size: 12px;
                }
                QProgressBar::chunk {
                    background-color: #2ecc71;
                    border-radius: 5px;
                }
            """)
        layout.addWidget(self.progress)

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
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 20px;
                    font-weight: 500;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #c0392b;
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
                    background-color: #2ecc71;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 20px;
                    font-weight: 500;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #27ae60;
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
                    background-color: #f39c12;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 20px;
                    font-weight: 500;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #e67e22;
                }
            """)
        msg.exec_()