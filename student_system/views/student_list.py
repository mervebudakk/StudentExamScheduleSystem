import re
import unicodedata
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QProgressBar
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
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.worker = None

        if not self.user or not self.user.get("bolum_id"):
            QMessageBox.critical(self, "Hata", "Bölüm bilgisi olmayan kullanıcı işlem yapamaz.")
            return

        layout = QVBoxLayout(self)
        self.title = QLabel(f"🎓 {self.user['bolum_adi']} - Öğrenci Listesi Yükleyici")
        self.title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(self.title)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        btn = QPushButton("📁 Excel Dosyası Seç ve Yükle")
        btn.clicked.connect(self.upload_excel)
        layout.addWidget(btn)

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
