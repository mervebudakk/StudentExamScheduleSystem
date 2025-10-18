import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
import pandas as pd
import re
from student_system.core.database import Database


class ExcelUploader(QWidget):
    # Değişiklik: init metodu artık 'user' parametresi alıyor
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user  # Giriş yapan kullanıcı bilgisi saklanıyor

        # Kullanıcının bölüm bilgisi olup olmadığını kontrol et
        if not self.user or not self.user.get('bolum_id'):
            QMessageBox.critical(self, "Hata", "Bölüm bilgisi olmayan bir kullanıcı bu işlemi yapamaz.")
            return

        layout = QVBoxLayout()
        title = QLabel(f"📚 {self.user['bolum_adi']} - Ders Listesi Yükleyici")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #27ae60;")
        layout.addWidget(title)
        upload_btn = QPushButton("Excel Dosyası Seç")
        upload_btn.clicked.connect(self.upload_excel)
        layout.addWidget(upload_btn)
        self.setLayout(layout)

    def upload_excel(self):
        file, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)")
        if not file:
            return

        try:
            # Excel'i başlık satırı olmadan oku
            df = pd.read_excel(file, header=None)

            lessons_to_process = []
            current_class = None
            current_type = 'Zorunlu'  # Varsayılan tür

            # Excel'deki her bir satırı gez
            for index, row in df.iterrows():
                # Satırın ilk hücresini al ve boş olup olmadığını kontrol et
                first_cell = str(row[0])
                if pd.isna(row[0]):
                    continue

                first_cell_upper = first_cell.upper()

                # Bu bir "SINIF" başlık satırı mı?
                if 'SINIF' in first_cell_upper:
                    # Satırdan sayıyı (1, 2, 3, 4) bul
                    match = re.search(r'\d+', first_cell)
                    if match:
                        current_class = int(match.group(0))
                    continue  # Bu satırda ders bilgisi yok, sonraki satıra geç

                # Bu bir "SEÇMELİ" başlık satırı mı?
                if 'SEÇMELİ' in first_cell_upper:
                    current_type = 'Seçmeli'
                    continue  # Bu satırda ders bilgisi yok, sonraki satıra geç

                # Eğer yukarıdakiler değilse, bu bir ders verisi içeren satırdır
                if not current_class:
                    raise ValueError(
                        "Ders listesi başlamadan önce bir 'Sınıf' başlığı bulunamadı (örn: 1. SINIF DERSLERİ).")

                # Ders bilgilerini al
                ders_kodu = str(row[0])
                ders_adi = str(row[1])
                hoca_adi = str(row[2])

                # Ders kodu veya adı boşsa bu satırı atla
                if not ders_kodu or not ders_adi:
                    continue

                # İşlenecek dersler listesine ekle
                lessons_to_process.append({
                    'ders_kodu': ders_kodu,
                    'ders_adi': ders_adi,
                    'hoca_adi': hoca_adi,
                    'sinif': current_class,
                    'tur': current_type
                })

            # Toplanan tüm dersleri veritabanına işle
            self.insert_lessons_to_db(lessons_to_process)

        except Exception as e:
            QMessageBox.critical(self, "❌ Hata", f"Ders yüklenirken hata oluştu:\n{str(e)}")

    def insert_lessons_to_db(self, lessons):
        if not lessons:
            QMessageBox.warning(self, "Bilgi", "Yüklenecek ders bulunamadı.")
            return

        bolum_id = self.user['bolum_id']
        inserted_count = 0

        # Transaction yönetimi için bu kısmı Database katmanında yapmak daha iyi olur
        # Şimdilik burada basitçe yapıyoruz
        try:
            for lesson in lessons:
                # Hoca ID'sini al veya yeni hoca ekle
                hoca = Database.execute_query(
                    "SELECT hoca_id FROM ogretimuyeleri WHERE ad_soyad = %s AND bolum_id = %s",
                    (lesson["hoca_adi"], bolum_id)
                )
                if not hoca:
                    result = Database.execute_query(
                        "INSERT INTO ogretimuyeleri (ad_soyad, bolum_id) VALUES (%s, %s) RETURNING hoca_id",
                        (lesson["hoca_adi"], bolum_id)
                    )
                    hoca_id = result[0]["hoca_id"]
                else:
                    hoca_id = hoca[0]["hoca_id"]

                # Dersleri ekle, varsa es geç (ON CONFLICT)
                result = Database.execute_query("""
                    INSERT INTO dersler (ders_kodu, ders_adi, bolum_id, hoca_id, sinif, tur, aktif)
                    VALUES (%s, %s, %s, %s, %s, %s, true)
                    ON CONFLICT (ders_kodu) DO NOTHING
                    RETURNING ders_id
                """, (
                    lesson["ders_kodu"], lesson["ders_adi"], bolum_id,
                    hoca_id, lesson["sinif"], lesson["tur"]
                ))

                if result:  # Eğer yeni kayıt eklendiyse result boş gelmez
                    inserted_count += 1

            QMessageBox.information(self, "✅ Başarılı",
                                    f"{len(lessons)} dersten {inserted_count} tanesi başarıyla yüklendi/güncellendi!")

        except Exception as e:
            # Normalde burada Database.rollback() çağrılmalı
            raise Exception(f"Veritabanına kayıt sırasında hata oluştu: {e}")