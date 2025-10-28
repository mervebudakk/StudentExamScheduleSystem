# student_system/views/exam_scheduler.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QDateEdit, QCheckBox, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, QDate
from student_system.core.database import Database
import json
from datetime import datetime, timedelta, time
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from datetime import datetime
import pandas as pd


# psycopg2 importları aşağıdan kaldırıldı, artık Database sınıfı üzerinden yönetiliyor.

class ExamScheduler(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        if not self.user or not self.user.get("bolum_id"):
            QMessageBox.critical(self, "Hata", "Bölüm bilgisi olmayan kullanıcı işlem yapamaz.")
            return

        self.setLayout(self._build_ui())
        self._load_lessons()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout()

        title = QLabel(f"📅 {self.user['bolum_adi']} – Sınav Programı Oluştur")
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#27ae60;")
        root.addWidget(title)

        main = QHBoxLayout()
        root.addLayout(main)

        # SOL: Kısıtlar
        left = QVBoxLayout()
        main.addLayout(left, 1)

        # 1) Ders Seçimi
        gb_lessons = QGroupBox("1) Ders Seçimi")
        v1 = QVBoxLayout(gb_lessons)
        self.lesson_list = QListWidget()
        self.lesson_list.setSelectionMode(self.lesson_list.NoSelection)
        v1.addWidget(self.lesson_list)

        btns = QHBoxLayout()
        self.btn_all = QPushButton("Tümünü Seç")
        self.btn_none = QPushButton("Tümünü Kaldır")
        self.btn_all.clicked.connect(lambda: self._toggle_all(True))
        self.btn_none.clicked.connect(lambda: self._toggle_all(False))
        btns.addWidget(self.btn_all);
        btns.addWidget(self.btn_none)
        v1.addLayout(btns)
        left.addWidget(gb_lessons)

        # 2) Tarih ve Günler
        gb_dates = QGroupBox("2) Sınav Tarihleri ve Günleri")
        f2 = QFormLayout(gb_dates)
        self.date_from = QDateEdit(QDate.currentDate());
        self.date_from.setCalendarPopup(True)
        self.date_to = QDateEdit(QDate.currentDate().addDays(14));
        self.date_to.setCalendarPopup(True)
        f2.addRow("Başlangıç:", self.date_from)
        f2.addRow("Bitiş:", self.date_to)

        days_row = QHBoxLayout()
        # hafta içi default açık, hafta sonu hariç tutulabilir
        self.chk_mon = QCheckBox("Pzt");
        self.chk_mon.setChecked(True)
        self.chk_tue = QCheckBox("Sal");
        self.chk_tue.setChecked(True)
        self.chk_wed = QCheckBox("Çar");
        self.chk_wed.setChecked(True)
        self.chk_thu = QCheckBox("Per");
        self.chk_thu.setChecked(True)
        self.chk_fri = QCheckBox("Cum");
        self.chk_fri.setChecked(True)
        self.chk_sat = QCheckBox("Cmt");
        self.chk_sat.setChecked(False)
        self.chk_sun = QCheckBox("Paz");
        self.chk_sun.setChecked(False)
        for w in [self.chk_mon, self.chk_tue, self.chk_wed, self.chk_thu, self.chk_fri, self.chk_sat, self.chk_sun]:
            days_row.addWidget(w)
        f2.addRow("Dahil Günler:", days_row)
        left.addWidget(gb_dates)

        # 3) Tür, 4) Süre, 5) Bekleme, 6) Çakışma
        gb_other = QGroupBox("Diğer Ayarlar")
        f3 = QFormLayout(gb_other)
        self.cmb_type = QComboBox();
        self.cmb_type.addItems(["Vize", "Final", "Bütünleme"])
        self.spin_duration = QSpinBox();
        self.spin_duration.setRange(30, 240);
        self.spin_duration.setValue(75)
        self.spin_break = QSpinBox();
        self.spin_break.setRange(0, 120);
        self.spin_break.setValue(15)
        self.chk_no_overlap = QCheckBox("Aynı anda sınav olmasın (tüm dersler tek slotta çakışmasın)")
        f3.addRow("Sınav Türü:", self.cmb_type)
        f3.addRow("Varsayılan Süre (dk):", self.spin_duration)
        f3.addRow("Bekleme Süresi (dk):", self.spin_break)
        f3.addRow(self.chk_no_overlap)
        left.addWidget(gb_other)

        # Oluştur butonu
        self.btn_generate = QPushButton("🚀 Programı Oluştur")
        self.btn_generate.clicked.connect(self._on_generate_clicked)
        left.addWidget(self.btn_generate)

        self.export_button = QPushButton("📤 Programı İndir")
        self.export_button.clicked.connect(self.export_to_excel)
        left.addWidget(self.export_button)

        # SAĞ: Önizleme Tablosu
        right = QVBoxLayout()
        main.addLayout(right, 1)

        self.preview = QTableWidget(0, 6)
        self.preview.setHorizontalHeaderLabels(["Ders Kodu", "Ders Adı", "Tarih", "Saat", "Sınıf", "Derslik"])
        self.preview.horizontalHeader().setStretchLastSection(True)
        right.addWidget(QLabel("📋 Program Önizlemesi"))
        right.addWidget(self.preview)

        return root

    # ---------- Dersleri yükle ----------
    def _load_lessons(self):
        rows = Database.execute_query("""
            SELECT ders_id, ders_kodu, ders_adi, sinif
            FROM dersler
            WHERE bolum_id = %s AND aktif = true
            ORDER BY sinif, ders_kodu
        """, (self.user["bolum_id"],))
        self.lesson_list.clear()
        for r in rows or []:
            item = QListWidgetItem(f"{r['ders_kodu']} – {r['ders_adi']} (Sınıf: {r['sinif']})")
            item.setData(Qt.UserRole, r)  # tüm satırı sakla
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)  # default: programa dahil
            self.lesson_list.addItem(item)

    def _toggle_all(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.lesson_list.count()):
            self.lesson_list.item(i).setCheckState(state)

    # ---------- Kısıtları topla & doğrula ----------
    def _collect_constraints(self):
        # seçili dersler
        selected = []
        for i in range(self.lesson_list.count()):
            it = self.lesson_list.item(i)
            if it.checkState() == Qt.Checked:
                selected.append(it.data(Qt.UserRole))
        if not selected:
            raise ValueError("Programa dahil edilecek en az bir ders seçmelisiniz.")

        d_from = self.date_from.date().toPyDate()
        d_to = self.date_to.date().toPyDate()
        if d_to < d_from:
            raise ValueError("Bitiş tarihi başlangıçtan önce olamaz.")

        # dahil günler (0=pzt ... 6=paz)
        allowed_weekdays = []
        for idx, w in enumerate(
                [self.chk_mon, self.chk_tue, self.chk_wed, self.chk_thu, self.chk_fri, self.chk_sat, self.chk_sun]
        ):
            if w.isChecked():
                allowed_weekdays.append(idx)

        if not allowed_weekdays:
            raise ValueError("En az bir gün seçmelisiniz.")

        return {
            "bolum_id": self.user["bolum_id"],
            "sinav_turu": self.cmb_type.currentText(),
            "varsayilan_sure": self.spin_duration.value(),
            "varsayilan_bekleme": self.spin_break.value(),
            "baslangic_tarihi": d_from,
            "bitis_tarihi": d_to,
            "allowed_weekdays": allowed_weekdays,
            "ayni_anda_sinav_engelle": self.chk_no_overlap.isChecked(),
            "dersler": selected
        }

    def _on_generate_clicked(self):
        DEFAULT_SLOTS = [
            time(10, 0), time(12, 30), time(14, 0),
            time(15, 30), time(16, 45), time(17, 45)
        ]
        try:
            cons = self._collect_constraints()

            # 🔹 Günleri hesapla
            start, end = cons["baslangic_tarihi"], cons["bitis_tarihi"]
            allowed_days = cons["allowed_weekdays"]
            days = []
            d = start
            while d <= end:
                if d.weekday() in allowed_days:
                    days.append(d)
                d += timedelta(days=1)
            if not days:
                raise ValueError("Belirtilen aralıkta uygun gün yok!")

            # 🔹 Derslikleri al
            rooms = Database.execute_query("""
                SELECT derslik_id, derslik_adi, kapasite
                FROM derslikler
                WHERE bolum_id = %s
                ORDER BY kapasite ASC
            """, (cons["bolum_id"],))
            if not rooms:
                raise ValueError("Tanımlı derslik bulunamadı!")

            # 🔹 Öğrenci-ders ilişkilerini al
            relations = Database.execute_query("""
                SELECT od.ogrenci_id, od.ders_id
                FROM ogrencidersleri od
                JOIN ogrenciler o ON o.ogrenci_id = od.ogrenci_id
                WHERE o.bolum_id = %s
            """, (cons["bolum_id"],))

            ogrenci_ders = {}
            for r in relations:
                ogrenci_ders.setdefault(r["ders_id"], set()).add(r["ogrenci_id"])

            # 🔹 Başlangıç boş program
            program = []
            used_slots = {}  # {tarih: [slot]}
            class_days = {}  # {sinif: [tarih]}

            for ders in cons["dersler"]:
                ders_id = ders["ders_id"]
                ogrenciler = ogrenci_ders.get(ders_id, set())
                sinif = ders["sinif"]

                yerlesmis = False
                for day in days:
                    # Aynı sınıf o gün sınav yapmış mı? (Dokümandaki kısıt)
                    if sinif in class_days and day in class_days[sinif]:
                        # Basit kısıt: Aynı sınıf aynı gün 1'den fazla sınav olmasın
                        # (Daha iyisi: 2'den fazla olmasın)
                        if class_days[sinif].count(day) >= 2:
                            continue

                    for slot in DEFAULT_SLOTS:
                        # Aynı saatte öğrenciler çakışıyor mu?
                        conflict = False
                        for p in program:
                            if p["tarih"] == day and p["saat"] == slot.strftime("%H:%M"):
                                ortak = ogrenciler.intersection(ogrenci_ders.get(p["ders_id"], set()))
                                if ortak:
                                    conflict = True
                                    break
                        if conflict:
                            continue

                        # Derslik bul
                        secilen = None
                        kapasite = len(ogrenciler) if ogrenciler else 30
                        for r in rooms:
                            if r["kapasite"] >= kapasite:
                                secilen = r
                                break
                        if not secilen:
                            # En büyük dersliği ata (sığmasa bile)
                            secilen = rooms[-1] if rooms else None
                            if not secilen:
                                raise ValueError(f"{ders['ders_adi']} için derslik yok!")
                            print(
                                f"Uyarı: {ders['ders_adi']} kapasitesi ({kapasite}) en büyük dersliğe ({secilen['kapasite']}) sığmıyor.")

                        # Eşleşme bulundu
                        program.append({
                            "ders_id": ders_id,
                            "ders_kodu": ders["ders_kodu"],
                            "ders_adi": ders["ders_adi"],
                            "sinif": sinif,
                            "tarih": day,
                            "saat": slot.strftime("%H:%M"),
                            "derslik": secilen["derslik_adi"]
                        })

                        # Kullanılmış slot/sınıf gününü işaretle
                        used_slots.setdefault(day, []).append(slot)
                        class_days.setdefault(sinif, []).append(day)
                        yerlesmis = True
                        break

                    if yerlesmis:
                        break

                if not yerlesmis:
                    print(f"Uyarı: {ders['ders_adi']} yerleştirilemedi, uygun gün/slot bulunamadı.")

            # 🔹 Veritabanına kayıt
            # Önce eski planı sil (aynı bölüm ve sınav türü için)
            Database.execute_non_query(
                "DELETE FROM sinavlar WHERE bolum_id = %s AND sinav_turu = %s",
                (cons["bolum_id"], cons["sinav_turu"])
            )

            plan_values = []
            for item in program:
                plan_values.append((
                    item["ders_id"], cons["bolum_id"], cons["sinav_turu"],
                    item["tarih"], item["saat"], cons["varsayilan_sure"], cons["varsayilan_bekleme"]
                ))

            Database.execute_many("""
                INSERT INTO sinavlar
                (ders_id, bolum_id, sinav_turu, sinav_tarihi, sinav_saati, sure, bekleme_suresi, durum)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Planlandı')
            """, plan_values)

            # 🔹 Derslik atamalarını yap
            self.assign_exam_rooms()

            rows = Database.execute_query("""
                SELECT d.ders_kodu, d.ders_adi, s.sinav_tarihi, s.sinav_saati, d.sinif, 
                       STRING_AGG(dl.derslik_kodu, ', ') AS derslikler
                FROM Sinavlar s
                JOIN Dersler d ON s.ders_id = d.ders_id
                LEFT JOIN SinavDerslikleri sd ON s.sinav_id = sd.sinav_id
                LEFT JOIN Derslikler dl ON sd.derslik_id = dl.derslik_id
                WHERE s.bolum_id = %s AND s.sinav_turu = %s
                GROUP BY d.ders_kodu, d.ders_adi, s.sinav_tarihi, s.sinav_saati, d.sinif
                ORDER BY s.sinav_tarihi, s.sinav_saati
            """, (cons["bolum_id"], cons["sinav_turu"]))

            self.preview.setRowCount(len(rows))
            for i, r in enumerate(rows):
                self.preview.setItem(i, 0, QTableWidgetItem(r["ders_kodu"]))
                self.preview.setItem(i, 1, QTableWidgetItem(r["ders_adi"]))
                tarih_str = r["sinav_tarihi"].strftime("%d.%m.%Y") if r["sinav_tarihi"] else "---"
                saat_str = r["sinav_saati"].strftime("%H:%M") if r["sinav_saati"] else "--:--"
                self.preview.setItem(i, 2, QTableWidgetItem(tarih_str))
                self.preview.setItem(i, 3, QTableWidgetItem(saat_str))
                self.preview.setItem(i, 4, QTableWidgetItem(str(r["sinif"])))
                self.preview.setItem(i, 5, QTableWidgetItem(r["derslikler"] or "-"))

            QMessageBox.information(self, "Başarılı", f"{len(rows)} sınav planlandı ✅")

        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def export_to_excel(self):
        """Planlanan sınav programını biçimlendirilmiş, tarihe göre sıralı ve öğretim elemanı bilgili Excel olarak dışa aktarır"""
        try:
            if self.preview.rowCount() == 0:
                QMessageBox.warning(self, "Uyarı", "Henüz oluşturulmuş bir sınav programı yok.")
                return

            path, _ = QFileDialog.getSaveFileName(
                self,
                "Sınav Programını Kaydet",
                f"{self.user['bolum_adi']}_{self.cmb_type.currentText()}_Programi.xlsx",
                "Excel Dosyası (*.xlsx)"
            )
            if not path:
                return

            # --- Gerekli kütüphaneler ---
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
            from openpyxl.utils import get_column_letter
            from datetime import datetime
            import pandas as pd

            # --- Veritabanı bağlantısı (DÜZELTİLDİ) ---
            conn = Database.get_connection()
            cur = conn.cursor()

            # --- Verileri al ve tarih/saat'e göre sırala ---
            data = []
            for row in range(self.preview.rowCount()):
                ders_kodu = self.preview.item(row, 0).text()
                ders_adi = self.preview.item(row, 1).text()
                tarih = self.preview.item(row, 2).text()
                saat = self.preview.item(row, 3).text()
                sinif = self.preview.item(row, 4).text()
                derslik = self.preview.item(row, 5).text()

                # Hoca adını çek
                cur.execute("""
                    SELECT ou.ad_soyad
                    FROM Dersler d
                    LEFT JOIN OgretimUyeleri ou ON d.hoca_id = ou.hoca_id
                    WHERE d.ders_kodu = %s AND d.bolum_id = %s
                """, (ders_kodu, self.user['bolum_id']))
                result = cur.fetchone()
                ogretim_elemani = result[0] if result and result[0] else "-"

                try:
                    tarih_dt = datetime.strptime(tarih, "%d.%m.%Y")
                except ValueError:
                    tarih_dt = datetime.strptime(tarih, "%Y-%m-%d")

                try:
                    saat_dt = datetime.strptime(saat, "%H:%M")
                except:
                    saat_dt = datetime.strptime("00:00", "%H:%M")

                data.append([tarih_dt, saat_dt, ders_kodu, ders_adi, ogretim_elemani, sinif, derslik])

            df = pd.DataFrame(data,
                              columns=["Tarih", "Saat", "Ders Kodu", "Ders Adı", "Öğretim Elemanı", "Sınıf", "Derslik"])
            df = df.sort_values(by=["Tarih", "Saat"]).reset_index(drop=True)

            # --- Excel biçimlendirme ---
            wb = Workbook()
            ws = wb.active
            ws.title = "Sınav Programı"

            bolum_adi = self.user.get("bolum_adi", "Bölüm")
            sinav_turu = self.cmb_type.currentText() if hasattr(self, "cmb_type") else "Sınav"
            baslik = f"{bolum_adi.upper()} BÖLÜMÜ {sinav_turu.upper()} SINAV PROGRAMI"

            ws.merge_cells("A1:G1")
            ws["A1"] = baslik
            ws["A1"].font = Font(bold=True, size=14)
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
            ws["A1"].fill = PatternFill("solid", fgColor="F4B084")  # Turuncu Başlık

            headers = ["Tarih", "Sınav Saati", "Ders Adı", "Öğretim Elemanı", "Sınıf", "Derslik"]
            ws.append(headers)
            header_fill = PatternFill("solid", fgColor="F4B084")
            border_style = Border(
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="thin")
            )
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=2, column=col_idx)
                cell.font = Font(bold=True)
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border_style

            # Sütun genişlikleri
            ws.column_dimensions[get_column_letter(1)].width = 15  # Tarih
            ws.column_dimensions[get_column_letter(2)].width = 15  # Saat
            ws.column_dimensions[get_column_letter(3)].width = 35  # Ders Adı
            ws.column_dimensions[get_column_letter(4)].width = 25  # Hoca
            ws.column_dimensions[get_column_letter(5)].width = 10  # Sınıf
            ws.column_dimensions[get_column_letter(6)].width = 25  # Derslik

            # --- Tarihe göre gruplama ---
            current_row = 3
            renk_index = 0
            renkler = ["FFFFFF", "FFF2CC"]  # Beyaz, Açık Sarı

            for tarih, grup in df.groupby("Tarih"):
                first_row = current_row
                tarih_str = tarih.strftime("%d.%m.%Y")
                gun_rengi = PatternFill("solid", fgColor=renkler[renk_index % len(renkler)])

                for _, row in grup.iterrows():
                    ws.cell(row=current_row, column=2, value=row["Saat"].strftime("%H:%M"))
                    ws.cell(row=current_row, column=3, value=row["Ders Adı"])
                    ws.cell(row=current_row, column=4, value=row["Öğretim Elemanı"])
                    ws.cell(row=current_row, column=5, value=row["Sınıf"])
                    ws.cell(row=current_row, column=6, value=row["Derslik"])

                    # Hücre biçimleri
                    for col in range(2, 7):
                        cell = ws.cell(row=current_row, column=col)
                        cell.border = border_style
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        cell.fill = gun_rengi

                    current_row += 1

                # Tarih hücresi
                if current_row - 1 >= first_row:
                    ws.merge_cells(start_row=first_row, start_column=1, end_row=current_row - 1, end_column=1)
                date_cell = ws.cell(row=first_row, column=1)
                date_cell.value = tarih_str
                date_cell.alignment = Alignment(text_rotation=90, horizontal="center", vertical="center")
                date_cell.border = border_style
                date_cell.font = Font(bold=True)
                date_cell.fill = gun_rengi

                renk_index += 1

            for r in range(1, ws.max_row + 1):
                ws.row_dimensions[r].height = 20

            wb.save(path)
            cur.close()
            conn.close()

            QMessageBox.information(self, "Başarılı", f"📘 Öğretim elemanlı sınav programı kaydedildi:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel çıktısı oluşturulamadı:\n{str(e)}")

    def assign_exam_rooms(self):
        """SinavDerslikleri tablosunu otomatik doldurur"""
        try:
            from datetime import datetime, timedelta

            # --- Veritabanı bağlantısı (DÜZELTİLDİ) ---
            conn = Database.get_connection()
            cur = conn.cursor()

            # 🔹 Aktif derslikleri çek (kapasiteye göre BÜYÜKTEN KÜÇÜĞE)
            cur.execute("""
                SELECT derslik_id, derslik_adi, kapasite
                FROM Derslikler
                WHERE aktif = true AND bolum_id = %s
                ORDER BY kapasite DESC
            """, (self.user["bolum_id"],))
            derslikler = cur.fetchall()
            if not derslikler:
                print("⚠️ Aktif derslik bulunamadı.")
                cur.close();
                conn.close()
                return

            # 🔹 Bölüme ait sınavları (planlanan türdeki) çek
            sinav_turu = self.cmb_type.currentText()
            cur.execute("""
                SELECT s.sinav_id, s.ders_id, s.sinav_tarihi, s.sinav_saati
                FROM Sinavlar s
                WHERE s.bolum_id = %s AND s.durum = 'Planlandı' AND s.sinav_turu = %s
                ORDER BY s.sinav_tarihi, s.sinav_saati
            """, (self.user["bolum_id"], sinav_turu))
            sinavlar = cur.fetchall()
            if not sinavlar:
                print("⚠️ Henüz sınav bulunamadı.")
                cur.close();
                conn.close()
                return

            # 🔹 Öğrenci sayılarını al
            cur.execute("""
                SELECT ders_id, COUNT(ogrenci_id) as ogrenci_sayisi
                FROM ogrencidersleri
                GROUP BY ders_id
            """)
            ogrenci_sayilari = {r[0]: r[1] for r in cur.fetchall()}

            # 🔹 Derslik program geçmişi
            derslik_programi = {d[0]: {} for d in derslikler}  # {derslik_id: {tarih: [saat]}}

            atanan = 0
            for sinav_id, ders_id, tarih, saat in sinavlar:
                if isinstance(saat, str):
                    saat_time = datetime.strptime(saat, "%H:%M").time()
                else:
                    saat_time = saat

                if isinstance(tarih, datetime):
                    tarih_date = tarih.date()
                else:
                    tarih_date = tarih

                # Bu sınav için gereken kapasite
                gereken_kapasite = ogrenci_sayilari.get(ders_id, 0)

                # Derslikleri dolaş
                uygun_derslik_bulundu = False
                for derslik_id, derslik_adi, kapasite in derslikler:
                    if kapasite < gereken_kapasite:
                        continue  # Bu derslik küçük, atla

                    # O derslikte o gün sınav var mı kontrol et
                    gunluk_program = derslik_programi.get(derslik_id, {}).get(tarih_date, [])

                    # Çakışma var mı? (Basit saat çakışması)
                    if saat_time in gunluk_program:
                        continue  # Bu slot dolu

                    # Uygun derslik bulundu
                    uygun_derslik_bulundu = True
                    derslik_programi.setdefault(derslik_id, {}).setdefault(tarih_date, []).append(saat_time)

                    cur.execute("""
                        INSERT INTO SinavDerslikleri (sinav_id, derslik_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (sinav_id, derslik_id))

                    atanan += 1
                    break  # Bu sınav için derslik atandı, sonraki sınava geç

                if not uygun_derslik_bulundu:
                    # Hiçbir derslik uymadı (ya hepsi dolu ya da hepsi küçük)
                    # En büyük dersliği ata (kapasite yetmese bile)
                    en_buyuk_derslik = derslikler[0]
                    cur.execute("""
                        INSERT INTO SinavDerslikleri (sinav_id, derslik_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (sinav_id, en_buyuk_derslik[0]))
                    atanan += 1
                    print(
                        f"UYARI: {tarih_date} {saat_time} sınavı ({gereken_kapasite} kişi) için uygun derslik bulunamadı, en büyüğe atandı.")

            conn.commit()
            cur.close()
            conn.close()
            print(f"✅ {atanan} sınav-derslik ataması yapıldı.")

        except Exception as e:
            print(f"❌ Derslik atama hatası: {e}")