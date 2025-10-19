import re
import unicodedata
import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
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
    """Türkçe karakterleri/boşlukları normalize edip karşılaştırma anahtarı üret."""
    if s is None:
        return ''
    s = str(s).strip().lower()
    # Unicode ayrıştırma (ı/İ vs) → ascii benzeri
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    # Noktalama ve boşlukları sadeleştir
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def canonical_header(cell_text: str):
    """Bir hücredeki metnin hangi standart başlığa denk geldiğini bul."""
    key = norm(cell_text)
    for canonical, variants in HEADER_SYNONYMS.items():
        if key in {norm(v) for v in variants}:
            return canonical
    return None


class ExcelUploader(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        if not self.user or not self.user.get('bolum_id'):
            QMessageBox.critical(self, "Hata", "Bölüm bilgisi olmayan bir kullanıcı bu işlemi yapamaz.")
            return

        layout = QVBoxLayout(self)
        title = QLabel(f"📚 {self.user['bolum_adi']} - Ders Listesi Yükleyici")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #27ae60;")
        layout.addWidget(title)

        btn = QPushButton("Excel Dosyası Seç")
        btn.clicked.connect(self.upload_excel)
        layout.addWidget(btn)

    # ----------------- Ana Akış -----------------

    def upload_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)")
        if not path:
            return

        try:
            df = pd.read_excel(path, header=None)
            lessons = self.parse_lessons(df)
            self.insert_lessons_to_db(lessons)

        except Exception as e:
            QMessageBox.critical(self, "❌ Hata", f"Ders yüklenirken hata oluştu:\n{str(e)}")

    def parse_lessons(self, df: pd.DataFrame):
        """
        Excel → ders listesi
        Kurallar:
        - 'X. Sınıf' satırı sınıfı ayarlar, ardından gelecek ilk 'başlık satırı' kolon indekslerini belirler.
        - 'SEÇMELİ' görüldüğünde tür 'Seçmeli' olur (yeni sınıf gelene kadar).
        - Başlık satırı: en az 'ders_kodu' ve 'ders_adi' eşleşmeleri içermeli.
        """
        lessons = []
        current_class = None
        current_type = 'Zorunlu'
        colmap = {}  # {'ders_kodu': idx, 'ders_adi': idx, 'hoca_adi': idx}

        for _, row in df.iterrows():
            # Tüm satırı string'e çevirip normalize edilmiş bir liste üretelim
            cells = [str(x).strip() if pd.notna(x) else "" for x in row.tolist()]
            if all(c == "" for c in cells):
                continue

            first = cells[0]
            first_norm = norm(first).upper()

            # 1) Sınıf satırı?
            m = SINIF_RE.search(first.upper())
            if m:
                current_class = int(m.group(1))
                current_type = 'Zorunlu'   # sınıf değişince reset
                colmap = {}
                continue

            # 2) Seçmeli bildirimi?
            if 'SECMELI' in first_norm or any('SECMELI' in norm(c).upper() for c in cells):
                current_type = 'Seçmeli'
                # Bazı dosyalarda hemen altında tekrar başlık satırı gelebilir → colmap reset yok.
                continue

            # 3) Başlık satırı mı?
            detected = {}
            for idx, cell in enumerate(cells):
                key = canonical_header(cell)
                if key and key not in detected:
                    detected[key] = idx

            if {'ders_kodu', 'ders_adi'}.issubset(detected.keys()):
                # En az bu ikisi bulunmalı → başlık satırıdır.
                colmap = detected
                # hoca_adi yoksa bile veri satırına geçebiliriz (opsiyonel)
                continue

            # 4) Veri satırı
            if current_class is None or not colmap:
                # Henüz sınıf ya da başlık okunmadı → veri değil
                continue

            def take(key, default=""):
                idx = colmap.get(key)
                return (cells[idx] if idx is not None and idx < len(cells) else default).strip()

            ders_kodu = take('ders_kodu')
            ders_adi  = take('ders_adi')
            hoca_adi  = take('hoca_adi')

            # Boş/başlık kırıntısı satırlarını ele
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

    # ----------------- DB Kayıt -----------------

    def insert_lessons_to_db(self, lessons):
        if not lessons:
            QMessageBox.information(self, "Bilgi", "Yüklenecek ders bulunamadı.")
            return

        bolum_id = self.user['bolum_id']
        inserted = 0

        try:
            for lesson in lessons:
                # 1) Hoca (varsa getir, yoksa ekle)
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

                # 2) Ders zaten var mı?
                exists = Database.execute_query(
                    "SELECT ders_id FROM dersler WHERE ders_kodu = %s AND bolum_id = %s",
                    (lesson['ders_kodu'], bolum_id)
                )
                if exists:
                    continue

                # 3) Yeni ders
                Database.execute_non_query("""
                    INSERT INTO dersler (ders_kodu, ders_adi, bolum_id, hoca_id, sinif, tur, aktif)
                    VALUES (%s, %s, %s, %s, %s, %s, true)
                """, (lesson['ders_kodu'], lesson['ders_adi'], bolum_id, hoca_id, lesson['sinif'], lesson['tur']))
                inserted += 1

            QMessageBox.information(
                self, "✅ Başarılı",
                f"{len(lessons)} kaydın {inserted} tanesi eklendi (mevcut olanlar atlandı)."
            )
        except Exception as e:
            raise Exception(f"Veritabanı kaydı sırasında hata: {e}")
