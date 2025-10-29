import re
import unicodedata
import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QTableWidget, \
    QTableWidgetItem, QTextEdit, QHeaderView, QFrame, QHBoxLayout
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
        self.setMinimumSize(1200, 750)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: none;
                border-radius: 0px;
            }
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 20)

        title = QLabel(f"{self.user['bolum_adi']} - Ders Listesi İşlemleri")
        title.setStyleSheet("color: #2c3e50; font-size: 28px; font-weight: 700; border: none;")
        hl.addWidget(title)
        hl.addStretch()

        self.upload_btn = QPushButton("Excel Dosyası Yükle")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.clicked.connect(self.upload_excel)
        self.upload_btn.setFixedHeight(45)
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
        hl.addWidget(self.upload_btn)

        layout.addWidget(header)

        table_label = QLabel("Kayıtlı Dersler")
        table_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #5a6c7d; margin-top: 4px;")
        layout.addWidget(table_label)

        table_frame = QFrame()
        table_frame.setStyleSheet("""
            QFrame { 
                background: white; 
                border: 1px solid #e1e8ed; 
                border-radius: 12px;
            }
        """)
        tv = QVBoxLayout(table_frame)
        tv.setContentsMargins(1, 1, 1, 1)

        self.lesson_table = QTableWidget()
        self.lesson_table.setColumnCount(2)
        self.lesson_table.setHorizontalHeaderLabels(["Ders Kodu", "Ders Adı"])
        self.lesson_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.lesson_table.setAlternatingRowColors(True)
        self.lesson_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.lesson_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.lesson_table.cellClicked.connect(self.show_students_for_lesson)
        self.lesson_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: none;
                gridline-color: #f0f3f5;
                alternate-background-color: #f8f9fa;
                font-size: 14px;
                border-radius: 12px;
            }
            QHeaderView::section {
                background: #f8f9fa;
                color: #5a6c7d;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #e1e8ed;
                font-weight: 600;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #f0f3f5;
                color: #2c3e50;
            }
            QTableWidget::item:selected {
                background: #f0f3ff;
                color: #5d6dfa;
            }
            QTableWidget::item:focus {
                outline: none; 
            }
        """)
        tv.addWidget(self.lesson_table)
        layout.addWidget(table_frame)

        student_label = QLabel("Derse Kayıtlı Öğrenciler")
        student_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #5a6c7d; margin-top: 8px;")
        layout.addWidget(student_label)

        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame { 
                background: white; 
                border: 1px solid #e1e8ed; 
                border-radius: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(1, 1, 1, 1)

        self.student_info = QTextEdit()
        self.student_info.setReadOnly(True)
        self.student_info.setStyleSheet("""
            QTextEdit {
                background: white;
                border: none;
                border-radius: 12px;
                padding: 16px;
                font-size: 14px;
                color: #2c3e50;
            }
        """)
        info_layout.addWidget(self.student_info)
        layout.addWidget(info_frame)

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
            <div style='padding: 8px; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif;'>
                <div style='color: #5d6dfa; font-size: 15px; font-weight: 600; margin-bottom: 12px;'>
                    {ders_kodu} - {ders_adi}
                </div>
                <div style='color: #95a5a6; font-size: 14px;'>
                    Bu derse kayıtlı öğrenci bulunamadı.
                </div>
            </div>
            """
            self.student_info.setHtml(html)
            return

        html = f"""
        <div style='padding: 8px; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif;'>
            <div style='color: #5d6dfa; font-size: 15px; font-weight: 600; margin-bottom: 12px;'>
                {ders_kodu} - {ders_adi}
            </div>
            <div style='color: #5a6c7d; font-size: 14px; font-weight: 500; margin-bottom: 10px;'>
                Dersi Alan Öğrenciler:
            </div>
        """

        for o in ogrenciler:
            html += f"""
            <div style='color: #2c3e50; font-size: 14px; margin-left: 16px; margin-bottom: 6px; line-height: 1.6;'>
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
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background: white;
            }
            QMessageBox QLabel {
                color: #2c3e50;
                font-size: 14px;
                min-width: 350px;
            }
            QPushButton {
                background: #ef4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #dc2626;
            }
        """)
        msg.exec_()

    def show_success(self, title, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background: white;
            }
            QMessageBox QLabel {
                color: #2c3e50;
                font-size: 14px;
                min-width: 350px;
            }
            QPushButton {
                background: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #059669;
            }
        """)
        msg.exec_()

    def show_info(self, title, message):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox {
                background: white;
            }
            QMessageBox QLabel {
                color: #2c3e50;
                font-size: 14px;
                min-width: 350px;
            }
            QPushButton {
                background: #5d6dfa;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: #4c5de8;
            }
        """)
        msg.exec_()