import re
import unicodedata
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QProgressBar,QHBoxLayout, QLineEdit, QTableWidget, QTableWidgetItem, QTextEdit
from student_system.core.database import Database

# Başlık eşleşmeleri
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


# 🧵 Arka planda yüklemeyi yapacak Worker Thread
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

            # 1️⃣ Öğrencileri toplu ekle
            ogrenci_values = [
                (s["ogrenci_no"], s["ad_soyad"], self.bolum_id, s["sinif"])
                for s in self.students
            ]
            Database.execute_many("""
                INSERT INTO ogrenciler (ogrenci_no, ad_soyad, bolum_id, sinif)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ogrenci_no) DO NOTHING
            """, ogrenci_values)

            # 2️⃣ Tüm öğrencilerin ID’lerini al
            ogrenci_map = {
                row["ogrenci_no"]: row["ogrenci_id"]
                for row in Database.execute_query("SELECT ogrenci_id, ogrenci_no FROM ogrenciler WHERE bolum_id = %s", (self.bolum_id,))
            }

            # 3️⃣ Tüm derslerin ID’lerini al
            ders_map = {
                row["ders_kodu"]: row["ders_id"]
                for row in Database.execute_query("SELECT ders_id, ders_kodu FROM dersler WHERE bolum_id = %s", (self.bolum_id,))
            }

            relation_values = []
            for idx, s in enumerate(self.students):
                ogr_id = ogrenci_map.get(s["ogrenci_no"])
                ders_id = ders_map.get(s["ders_kodu"])
                if ogr_id and ders_id:
                    relation_values.append((ogr_id, ders_id))

                if idx % 100 == 0:
                    self.progress.emit(int(idx / len(self.students) * 100))

            # 4️⃣ Öğrenci-ders ilişkilerini toplu ekle
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


# 📁 Ana PyQt arayüzü
class StudentListUploader(QWidget):
    def load_students(self):
        """Veritabanındaki öğrencileri tabloya yükler."""
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
        """Öğrenci numarasına göre arama yapar ve aldığı dersleri listeler."""
        ogr_no = self.search_box.text().strip()
        if not ogr_no:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir öğrenci numarası girin.")
            return

        ogrenci = Database.execute_query("""
            SELECT ogrenci_id, ad_soyad FROM ogrenciler
            WHERE ogrenci_no = %s AND bolum_id = %s
        """, (ogr_no, self.user["bolum_id"]))

        if not ogrenci:
            self.result_area.setText("❌ Öğrenci bulunamadı.")
            return

        ogr = ogrenci[0]
        dersler = Database.execute_query("""
            SELECT d.ders_adi, d.ders_kodu
            FROM ogrencidersleri od
            JOIN dersler d ON od.ders_id = d.ders_id
            WHERE od.ogrenci_id = %s
            ORDER BY d.ders_kodu
        """, (ogr["ogrenci_id"],))

        text = f"👤 Öğrenci: {ogr['ad_soyad']}\n📘 Aldığı Dersler:\n"
        for d in dersler:
            text += f"- {d['ders_adi']} (Kodu: {d['ders_kodu']})\n"

        self.result_area.setText(text if dersler else "📭 Bu öğrenciye ait ders kaydı yok.")
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.worker = None

        if not self.user or not self.user.get("bolum_id"):
            QMessageBox.critical(self, "Hata", "Bölüm bilgisi olmayan kullanıcı işlem yapamaz.")
            return

        layout = QVBoxLayout(self)

        # 📌 Başlık
        self.title = QLabel(f"🎓 {self.user['bolum_adi']} - Öğrenci Listesi")
        self.title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(self.title)

        # 🔍 Arama kutusu + buton
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("👤 Öğrenci numarasını girin...")
        search_button = QPushButton("Ara")
        search_button.clicked.connect(self.search_student)
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(search_button)
        layout.addLayout(search_layout)

        # 📊 Öğrenci Tablosu
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Öğrenci No", "Ad Soyad", "Sınıf"])
        layout.addWidget(self.table)

        # 📋 Arama Sonucu Gösterimi
        self.result_area = QTextEdit()
        self.result_area.setReadOnly(True)
        self.result_area.setStyleSheet("background:#f9f9f9; padding:8px; font-size:14px;")
        layout.addWidget(self.result_area)

        # 📁 Excel yükleme butonu (altta küçük bölüm)
        btn = QPushButton("📁 Excel Dosyası Seç ve Yükle")
        btn.clicked.connect(self.upload_excel)
        layout.addWidget(btn)

        # Başlangıçta tabloyu doldur
        self.load_students()

    def upload_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)")
        if not path:
            return

        try:
            df = pd.read_excel(path, header=0)
            students = self.parse_students(df)

            # 🧵 Thread başlat
            self.worker = StudentUploadWorker(students, self.user["bolum_id"])
            self.worker.progress.connect(self.on_progress)
            self.worker.finished.connect(self.on_finished)
            self.worker.error.connect(self.on_error)
            self.worker.start()

        except Exception as e:
            QMessageBox.critical(self, "❌ Hata", f"Öğrenci listesi okunurken hata oluştu:\n{str(e)}")

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
        QMessageBox.information(self, "✅ Yükleme Tamamlandı",
                                f"📌 {ogr_count} öğrenci işlendi\n🔗 {rel_count} öğrenci-ders ilişkisi eklendi")

    def on_error(self, msg):
        QMessageBox.critical(self, "❌ Hata", f"Yükleme sırasında hata oluştu:\n{msg}")
