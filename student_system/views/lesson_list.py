import re
import unicodedata
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QTableWidget, \
    QTableWidgetItem, QTextEdit, QHeaderView, QFrame
from student_system.core.database import Database

HEADER_SYNONYMS = {
    'ders_kodu': {
        'derskodu', 'ders kodu', 'dersin kodu', 'kod', 'kodu'
    },
    'ders_adi': {
        'dersadi', 'ders adi', 'dersin adi', 'dersin adı', 'ders adı', 'adi', 'adı'
    },
    'hoca_adi': {
        'dersi veren ogr elemani', 'dersi veren öğretim elemani', 'dersi veren öğretim elemanı',
        'dersi veren ogr. elemani', 'dersi veren ogr. üyesi', 'dersi veren öğretim üyesi',
        'dersi veren ogr. elemanı', 'hoca adi', 'hoca adı', 'öğretim üyesi', 'öğretim elemanı'
    }
}

SINIF_RE = re.compile(r'(\d+)\s*[\.\-]?\s*sınıf', re.IGNORECASE)


def norm(s: str) -> str:
    if s is None:
        return ''
    s = str(s).strip().lower()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def canonical_header(cell_text: str):
    key = norm(cell_text)
    for canonical, variants in HEADER_SYNONYMS.items():
        if key in {norm(v) for v in variants}:
            return canonical
    return None


class LessonListUploader(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8e44ad, stop:1 #9b59b6);
                border-radius: 12px;
                padding: 15px;
            }
        """)
        title_layout = QVBoxLayout(title_frame)

        title = QLabel(f"📚 {self.user['bolum_adi']} - Ders Listesi")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: white; background: transparent;")
        title_layout.addWidget(title)

        layout.addWidget(title_frame)

        table_label = QLabel("📘 Kayıtlı Dersler")
        table_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-top: 10px;")
        layout.addWidget(table_label)

        self.lesson_table = QTableWidget()
        self.lesson_table.setColumnCount(2)
        self.lesson_table.setHorizontalHeaderLabels(["Ders Kodu", "Ders Adı"])
        self.lesson_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lesson_table.setAlternatingRowColors(True)
        self.lesson_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.lesson_table.cellClicked.connect(self.show_students_for_lesson)
        self.lesson_table.setStyleSheet("""
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
                    stop:0 #8e44ad, stop:1 #9b59b6);
                color: white;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8e44ad, stop:1 #9b59b6);
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
        layout.addWidget(self.lesson_table)

        student_label = QLabel("👨‍🎓 Derse Kayıtlı Öğrenciler")
        student_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin-top: 10px;")
        layout.addWidget(student_label)

        self.student_info = QTextEdit()
        self.student_info.setReadOnly(True)
        self.student_info.setMaximumHeight(200)
        self.student_info.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #bdc3c7;
                border-radius: 10px;
                padding: 15px;
                font-size: 14px;
                color: #2c3e50;
            }
        """)
        layout.addWidget(self.student_info)

        self.upload_btn = QPushButton("📁 Excel Dosyası Seç ve Yükle")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.clicked.connect(self.upload_excel)
        self.upload_btn.setFixedHeight(50)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e67e22, stop:1 #d35400);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 15px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #d35400, stop:1 #ba4a00);
            }
            QPushButton:pressed {
                background: #a04000;
            }
        """)
        layout.addWidget(self.upload_btn)

        self.setLayout(layout)
        self.load_lessons()

    def load_lessons(self):
        dersler = Database.execute_query(
            "SELECT ders_kodu, ders_adi FROM dersler WHERE bolum_id = %s ORDER BY ders_kodu",
            (self.user['bolum_id'],)
        )
        self.lesson_table.setRowCount(len(dersler))
        for row, ders in enumerate(dersler):
            self.lesson_table.setItem(row, 0, QTableWidgetItem(ders['ders_kodu']))
            self.lesson_table.setItem(row, 1, QTableWidgetItem(ders['ders_adi']))

    def show_students_for_lesson(self, row, column):
        ders_kodu = self.lesson_table.item(row, 0).text()
        ders_adi = self.lesson_table.item(row, 1).text()

        query = """
            SELECT o.ogrenci_no, o.ad_soyad
            FROM ogrencidersleri od
            JOIN ogrenciler o ON o.ogrenci_id = od.ogrenci_id
            JOIN dersler d ON d.ders_id = od.ders_id
            WHERE d.ders_kodu = %s AND d.bolum_id = %s
            ORDER BY o.ogrenci_no
        """
        ogrenciler = Database.execute_query(query, (ders_kodu, self.user['bolum_id']))

        if not ogrenciler:
            html = f"""
            <div style='padding: 15px; font-family: Segoe UI;'>
                <div style='color: #e74c3c; font-size: 15px; font-weight: bold;'>
                    📘 {ders_kodu} - {ders_adi}
                </div>
                <div style='color: #95a5a6; font-size: 14px; margin-top: 10px;'>
                    Bu derse kayıtlı öğrenci bulunamadı.
                </div>
            </div>
            """
            self.student_info.setHtml(html)
            return

        html = f"""
        <div style='padding: 15px; font-family: Segoe UI;'>
            <div style='color: #8e44ad; font-size: 16px; font-weight: bold; margin-bottom: 12px;'>
                📘 {ders_kodu} - {ders_adi}
            </div>
            <div style='color: #2c3e50; font-size: 15px; font-weight: 600; margin-bottom: 8px;'>
                👨‍🎓 Dersi Alan Öğrenciler:
            </div>
        """

        for o in ogrenciler:
            html += f"""
            <div style='color: #34495e; font-size: 14px; margin-left: 20px; margin-bottom: 4px;'>
                • {o['ogrenci_no']} - {o['ad_soyad']}
            </div>
            """

        html += "</div>"
        self.student_info.setHtml(html)

    def upload_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)")
        if not path:
            return

        try:
            df = pd.read_excel(path, header=None)
            lessons = self.parse_lessons(df)
            self.insert_lessons_to_db(lessons)

        except Exception as e:
            self.show_error("Hata", f"Ders yüklenirken hata oluştu:\n{str(e)}")

    def parse_lessons(self, df: pd.DataFrame):
        lessons = []
        current_class = None
        current_type = 'Zorunlu'
        colmap = {}

        for _, row in df.iterrows():
            cells = [str(x).strip() if pd.notna(x) else "" for x in row.tolist()]
            if all(c == "" for c in cells):
                continue

            first = cells[0]
            first_norm = norm(first).upper()

            m = SINIF_RE.search(first.upper())
            if m:
                current_class = int(m.group(1))
                current_type = 'Zorunlu'
                colmap = {}
                continue

            if 'SECMELI' in first_norm or any('SECMELI' in norm(c).upper() for c in cells):
                current_type = 'Seçmeli'
                continue

            detected = {}
            for idx, cell in enumerate(cells):
                key = canonical_header(cell)
                if key and key not in detected:
                    detected[key] = idx

            if {'ders_kodu', 'ders_adi'}.issubset(detected.keys()):
                colmap = detected
                continue

            if current_class is None or not colmap:
                continue

            def take(key, default=""):
                idx = colmap.get(key)
                return (cells[idx] if idx is not None and idx < len(cells) else default).strip()

            ders_kodu = take('ders_kodu')
            ders_adi = take('ders_adi')
            hoca_adi = take('hoca_adi')

            if ders_kodu == "" and ders_adi == "":
                continue

            lessons.append({
                'ders_kodu': ders_kodu,
                'ders_adi': ders_adi,
                'hoca_adi': hoca_adi or 'Ders Veren Bölüm Öğretim Elemanları',
                'sinif': current_class,
                'tur': current_type
            })

        return lessons

    def insert_lessons_to_db(self, lessons):
        if not lessons:
            self.show_info("Bilgi", "Yüklenecek ders bulunamadı.")
            return

        bolum_id = self.user['bolum_id']
        inserted = 0

        try:
            for lesson in lessons:
                hoca = Database.execute_query(
                    "SELECT hoca_id FROM ogretimuyeleri WHERE ad_soyad = %s AND bolum_id = %s",
                    (lesson['hoca_adi'], bolum_id)
                )
                if not hoca:
                    Database.execute_non_query(
                        "INSERT INTO ogretimuyeleri (ad_soyad, bolum_id) VALUES (%s, %s)",
                        (lesson['hoca_adi'], bolum_id)
                    )
                    hoca = Database.execute_query(
                        "SELECT hoca_id FROM ogretimuyeleri WHERE ad_soyad = %s AND bolum_id = %s",
                        (lesson['hoca_adi'], bolum_id)
                    )
                hoca_id = hoca[0]['hoca_id']

                exists = Database.execute_query(
                    "SELECT ders_id FROM dersler WHERE ders_kodu = %s AND bolum_id = %s",
                    (lesson['ders_kodu'], bolum_id)
                )
                if exists:
                    continue

                Database.execute_non_query("""
                    INSERT INTO dersler (ders_kodu, ders_adi, bolum_id, hoca_id, sinif, tur, aktif)
                    VALUES (%s, %s, %s, %s, %s, %s, true)
                """, (lesson['ders_kodu'], lesson['ders_adi'], bolum_id, hoca_id, lesson['sinif'], lesson['tur']))
                inserted += 1

            self.show_success(
                "Başarılı",
                f"{len(lessons)} kaydın {inserted} tanesi eklendi (mevcut olanlar atlandı)."
            )
            self.load_lessons()

        except Exception as e:
            raise Exception(f"Veritabanı kaydı sırasında hata: {e}")

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

    def show_info(self, title, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(f"ℹ️ {title}")
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
                    stop:0 #3498db, stop:1 #2980b9);
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2980b9, stop:1 #21618c);
            }
        """)
        msg.exec_()