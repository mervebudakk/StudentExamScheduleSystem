from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QGroupBox, QFormLayout, QDateEdit, QCheckBox, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QFileDialog, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor, QPalette
from student_system.core.database import Database
import json
from datetime import datetime, timedelta, time
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd


class ExamScheduler(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user

        if not self.user or not self.user.get("bolum_id"):
            QMessageBox.critical(self, "Hata", "Bölüm bilgisi olmayan kullanıcı işlem yapamaz.")
            return

        self._init_ui()
        self._apply_modern_styles()
        self._load_lessons()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(25, 25, 25, 25)

        self._create_header(main_layout)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        self._create_left_panel(content_layout)
        self._create_right_panel(content_layout)

        main_layout.addLayout(content_layout)

    def _create_header(self, parent_layout):
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QVBoxLayout(header_frame)

        title = QLabel(f"📅 {self.user['bolum_adi']}")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel("Sınav Programı Oluşturma Sistemi")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        parent_layout.addWidget(header_frame)

    def _create_left_panel(self, parent_layout):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("scrollArea")

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(15)

        self._create_lesson_selection_group(left_layout)
        self._create_date_settings_group(left_layout)
        self._create_exam_settings_group(left_layout)
        self._create_action_buttons(left_layout)

        left_layout.addStretch()
        scroll_area.setWidget(left_widget)
        parent_layout.addWidget(scroll_area, 2)

    def _create_lesson_selection_group(self, parent_layout):
        group = QGroupBox("📚 Ders Seçimi")
        group.setObjectName("modernGroup")
        layout = QVBoxLayout(group)

        self.lesson_list = QListWidget()
        self.lesson_list.setObjectName("lessonList")
        self.lesson_list.setSelectionMode(QListWidget.NoSelection)
        layout.addWidget(self.lesson_list)

        button_layout = QHBoxLayout()

        self.btn_all = QPushButton("✓ Tümünü Seç")
        self.btn_all.setObjectName("primaryButton")
        self.btn_all.clicked.connect(lambda: self._toggle_all(True))

        self.btn_none = QPushButton("✗ Tümünü Kaldır")
        self.btn_none.setObjectName("secondaryButton")
        self.btn_none.clicked.connect(lambda: self._toggle_all(False))

        button_layout.addWidget(self.btn_all)
        button_layout.addWidget(self.btn_none)
        layout.addLayout(button_layout)

        parent_layout.addWidget(group)

    def _create_date_settings_group(self, parent_layout):
        group = QGroupBox("📆 Tarih ve Gün Ayarları")
        group.setObjectName("modernGroup")
        form_layout = QFormLayout(group)
        form_layout.setSpacing(10)

        self.date_from = QDateEdit(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        self.date_from.setObjectName("dateEdit")

        self.date_to = QDateEdit(QDate.currentDate().addDays(14))
        self.date_to.setCalendarPopup(True)
        self.date_to.setObjectName("dateEdit")

        form_layout.addRow("Başlangıç Tarihi:", self.date_from)
        form_layout.addRow("Bitiş Tarihi:", self.date_to)

        days_label = QLabel("Sınav Günleri:")
        days_label.setObjectName("formLabel")
        form_layout.addRow(days_label)

        days_layout = QHBoxLayout()
        days_layout.setSpacing(5)

        self.chk_mon = self._create_day_checkbox("Pzt", True)
        self.chk_tue = self._create_day_checkbox("Sal", True)
        self.chk_wed = self._create_day_checkbox("Çar", True)
        self.chk_thu = self._create_day_checkbox("Per", True)
        self.chk_fri = self._create_day_checkbox("Cum", True)
        self.chk_sat = self._create_day_checkbox("Cmt", False)
        self.chk_sun = self._create_day_checkbox("Paz", False)

        for checkbox in [self.chk_mon, self.chk_tue, self.chk_wed, self.chk_thu,
                         self.chk_fri, self.chk_sat, self.chk_sun]:
            days_layout.addWidget(checkbox)

        form_layout.addRow(days_layout)
        parent_layout.addWidget(group)

    def _create_day_checkbox(self, text, checked):
        checkbox = QCheckBox(text)
        checkbox.setObjectName("dayCheckbox")
        checkbox.setChecked(checked)
        return checkbox

    def _create_exam_settings_group(self, parent_layout):
        group = QGroupBox("⚙️ Sınav Ayarları")
        group.setObjectName("modernGroup")
        form_layout = QFormLayout(group)
        form_layout.setSpacing(10)

        self.cmb_type = QComboBox()
        self.cmb_type.setObjectName("comboBox")
        self.cmb_type.addItems(["Vize", "Final", "Bütünleme"])

        self.spin_duration = QSpinBox()
        self.spin_duration.setObjectName("spinBox")
        self.spin_duration.setRange(30, 240)
        self.spin_duration.setValue(75)
        self.spin_duration.setSuffix(" dakika")

        self.spin_break = QSpinBox()
        self.spin_break.setObjectName("spinBox")
        self.spin_break.setRange(0, 120)
        self.spin_break.setValue(15)
        self.spin_break.setSuffix(" dakika")

        self.chk_no_overlap = QCheckBox("Sınavlar çakışmasın")
        self.chk_no_overlap.setObjectName("settingsCheckbox")

        form_layout.addRow("Sınav Türü:", self.cmb_type)
        form_layout.addRow("Sınav Süresi:", self.spin_duration)
        form_layout.addRow("Bekleme Süresi:", self.spin_break)
        form_layout.addRow(self.chk_no_overlap)

        parent_layout.addWidget(group)

    def _create_action_buttons(self, parent_layout):
        self.btn_generate = QPushButton("🚀 Programı Oluştur")
        self.btn_generate.setObjectName("generateButton")
        self.btn_generate.setMinimumHeight(50)
        self.btn_generate.clicked.connect(self._on_generate_clicked)

        self.export_button = QPushButton("📥 Excel Olarak İndir")
        self.export_button.setObjectName("exportButton")
        self.export_button.setMinimumHeight(45)
        self.export_button.clicked.connect(self.export_to_excel)

        parent_layout.addWidget(self.btn_generate)
        parent_layout.addWidget(self.export_button)

    def _create_right_panel(self, parent_layout):
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)

        preview_label = QLabel("📋 Program Önizlemesi")
        preview_label.setObjectName("sectionTitle")
        right_layout.addWidget(preview_label)

        self.preview = QTableWidget(0, 6)
        self.preview.setObjectName("previewTable")
        self.preview.setHorizontalHeaderLabels([
            "Ders Kodu", "Ders Adı", "Tarih", "Saat", "Sınıf", "Derslik"
        ])
        self.preview.horizontalHeader().setStretchLastSection(True)
        self.preview.setAlternatingRowColors(True)

        right_layout.addWidget(self.preview)
        parent_layout.addWidget(right_widget, 3)

    def _apply_modern_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa;
                color: #2c3e50;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
            }

            #headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 12px;
                padding: 25px 20px;
                min-height: 100px;
            }

            #mainTitle {
                font-size: 24px;
                font-weight: bold;
                color: white;
                margin: 8px 5px;
                padding: 5px;
            }

            #subtitle {
                font-size: 15px;
                color: rgba(255, 255, 255, 0.95);
                margin: 8px 5px;
                padding: 5px;
            }

            #modernGroup {
                background-color: white;
                border: 1px solid #e1e8ed;
                border-radius: 10px;
                padding: 15px;
                font-weight: bold;
                font-size: 14px;
            }

            #modernGroup::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 5px 10px;
                color: #667eea;
            }

            #lessonList {
                background-color: #fafbfc;
                border: 1px solid #e1e8ed;
                border-radius: 8px;
                padding: 8px;
                min-height: 200px;
            }

            #lessonList::item {
                padding: 8px;
                border-radius: 5px;
                margin: 2px 0px;
            }

            #lessonList::item:hover {
                background-color: #e8f0fe;
            }

            #lessonList::item:checked {
                background-color: #d3e3fd;
            }

            QPushButton {
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 500;
                border: none;
            }

            #primaryButton {
                background-color: #667eea;
                color: white;
            }

            #primaryButton:hover {
                background-color: #5568d3;
            }

            #primaryButton:pressed {
                background-color: #4451b8;
            }

            #secondaryButton {
                background-color: #e1e8ed;
                color: #2c3e50;
            }

            #secondaryButton:hover {
                background-color: #cbd5e0;
            }

            #generateButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #11998e, stop:1 #38ef7d);
                color: white;
                font-size: 15px;
                font-weight: bold;
            }

            #generateButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0e8070, stop:1 #2dd863);
            }

            #exportButton {
                background-color: #f39c12;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }

            #exportButton:hover {
                background-color: #e67e22;
            }

            QComboBox, QSpinBox, QDateEdit {
                background-color: white;
                border: 1px solid #e1e8ed;
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 35px;
            }

            QComboBox:hover, QSpinBox:hover, QDateEdit:hover {
                border: 1px solid #667eea;
            }

            QComboBox:focus, QSpinBox:focus, QDateEdit:focus {
                border: 2px solid #667eea;
            }

            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }

            QCheckBox {
                spacing: 8px;
            }

            #dayCheckbox {
                background-color: white;
                border: 1px solid #e1e8ed;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 45px;
            }

            #dayCheckbox:checked {
                background-color: #667eea;
                color: white;
            }

            #dayCheckbox::indicator {
                width: 0px;
                height: 0px;
            }

            #settingsCheckbox {
                padding: 8px;
                font-weight: 500;
            }

            #previewTable {
                background-color: white;
                border: 1px solid #e1e8ed;
                border-radius: 10px;
                gridline-color: #e1e8ed;
            }

            #previewTable::item {
                padding: 10px;
            }

            #previewTable::item:alternate {
                background-color: #f8f9fa;
            }

            QHeaderView::section {
                background-color: #667eea;
                color: white;
                padding: 12px;
                border: none;
                font-weight: bold;
            }

            #sectionTitle {
                font-size: 16px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px 5px;
            }

            QScrollArea {
                border: none;
                background-color: transparent;
            }

            QScrollBar:vertical {
                background: #f5f7fa;
                width: 12px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical {
                background: #cbd5e0;
                border-radius: 6px;
                min-height: 30px;
            }

            QScrollBar::handle:vertical:hover {
                background: #a0aec0;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QFormLayout QLabel {
                font-weight: 500;
                color: #4a5568;
            }
        """)

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
            item.setData(Qt.UserRole, r)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.lesson_list.addItem(item)

    def _toggle_all(self, checked):
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.lesson_list.count()):
            self.lesson_list.item(i).setCheckState(state)

    def _collect_constraints(self):
        selected = []
        for i in range(self.lesson_list.count()):
            item = self.lesson_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))

        if not selected:
            raise ValueError("Programa dahil edilecek en az bir ders seçmelisiniz.")

        d_from = self.date_from.date().toPyDate()
        d_to = self.date_to.date().toPyDate()

        if d_to < d_from:
            raise ValueError("Bitiş tarihi başlangıçtan önce olamaz.")

        allowed_weekdays = []
        checkboxes = [self.chk_mon, self.chk_tue, self.chk_wed, self.chk_thu,
                      self.chk_fri, self.chk_sat, self.chk_sun]

        for idx, checkbox in enumerate(checkboxes):
            if checkbox.isChecked():
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
            "secili_dersler": selected
        }

    def _on_generate_clicked(self):
        try:
            constraints = self._collect_constraints()
            schedule = self._generate_schedule(constraints)
            self._update_preview(schedule)
            self.assign_exam_rooms()

            QMessageBox.information(
                self,
                "Başarılı",
                f"✅ {len(schedule)} adet sınav başarıyla planlandı!"
            )
        except ValueError as e:
            QMessageBox.warning(self, "Uyarı", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Program oluşturulurken hata: {str(e)}")

    def _generate_schedule(self, c):
        conn = Database.get_connection()
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM Sinavlar 
            WHERE bolum_id = %s AND sinav_turu = %s
        """, (c["bolum_id"], c["sinav_turu"]))

        slots = self._build_time_slots(c)
        schedule = []

        if c["ayni_anda_sinav_engelle"]:
            for i, ders in enumerate(c["secili_dersler"]):
                if i >= len(slots):
                    break
                tarih, saat_obj = slots[i]
                schedule.append((ders, tarih, saat_obj))
        else:
            schedule = self._greedy_schedule(c, slots)

        for ders, tarih, saat_obj in schedule:
            cur.execute("""
                INSERT INTO Sinavlar 
                (ders_id, bolum_id, sinav_turu, sinav_tarihi, sinav_saati, durum)
                VALUES (%s, %s, %s, %s, %s, 'Planlandı')
            """, (ders["ders_id"], c["bolum_id"], c["sinav_turu"],
                  tarih, saat_obj))

        conn.commit()
        cur.close()
        conn.close()

        return schedule

    def _build_time_slots(self, c):
        slots = []
        current_date = c["baslangic_tarihi"]
        base_time = time(9, 0)

        while current_date <= c["bitis_tarihi"]:
            if current_date.weekday() in c["allowed_weekdays"]:
                current_time = datetime.combine(current_date, base_time)

                while current_time.hour < 17:
                    slots.append((current_date, current_time.time()))

                    minutes_to_add = c["varsayilan_sure"] + c["varsayilan_bekleme"]
                    current_time += timedelta(minutes=minutes_to_add)

            current_date += timedelta(days=1)

        return slots

    def _greedy_schedule(self, c, slots):
        schedule = []
        ders_ogrenci = {}

        conn = Database.get_connection()
        cur = conn.cursor()

        for ders in c["secili_dersler"]:
            cur.execute("""
                SELECT ogrenci_id 
                FROM ogrencidersleri 
                WHERE ders_id = %s
            """, (ders["ders_id"],))
            ders_ogrenci[ders["ders_id"]] = {row[0] for row in cur.fetchall()}

        cur.close()
        conn.close()

        slot_idx = 0
        for ders in c["secili_dersler"]:
            placed = False

            for i in range(slot_idx, len(slots)):
                tarih, saat_obj = slots[i]
                conflict = False

                for scheduled_ders, s_tarih, s_saat in schedule:
                    if s_tarih == tarih and s_saat == saat_obj:
                        ders_ogrenci_ids = ders_ogrenci.get(ders["ders_id"], set())
                        scheduled_ogrenci_ids = ders_ogrenci.get(scheduled_ders["ders_id"], set())

                        if ders_ogrenci_ids & scheduled_ogrenci_ids:
                            conflict = True
                            break

                if not conflict:
                    schedule.append((ders, tarih, saat_obj))
                    slot_idx = i
                    placed = True
                    break

            if not placed and slots:
                schedule.append((ders, slots[-1][0], slots[-1][1]))

        return schedule

    def _update_preview(self, schedule):
        self.preview.setRowCount(0)

        for ders, tarih, saat_obj in schedule:
            row = self.preview.rowCount()
            self.preview.insertRow(row)

            self.preview.setItem(row, 0, QTableWidgetItem(ders["ders_kodu"]))
            self.preview.setItem(row, 1, QTableWidgetItem(ders["ders_adi"]))
            self.preview.setItem(row, 2, QTableWidgetItem(tarih.strftime("%d.%m.%Y")))
            self.preview.setItem(row, 3, QTableWidgetItem(saat_obj.strftime("%H:%M")))
            self.preview.setItem(row, 4, QTableWidgetItem(str(ders.get("sinif", ""))))
            self.preview.setItem(row, 5, QTableWidgetItem("Atanacak"))

    def export_to_excel(self):
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "Excel Dosyası Kaydet", "",
                "Excel Files (*.xlsx)"
            )
            if not path:
                return

            conn = Database.get_connection()
            cur = conn.cursor()

            sinav_turu = self.cmb_type.currentText()

            cur.execute("""
                SELECT 
                    s.sinav_tarihi AS tarih,
                    s.sinav_saati AS saat,
                    d.ders_adi AS ders_adi,
                    COALESCE(ou.ad_soyad, 'Atanmamış') AS ogretim_elemani,
                    COALESCE(STRING_AGG(dl.derslik_adi, ', '), 'Atanmamış') AS derslik
                FROM Sinavlar s
                JOIN Dersler d ON s.ders_id = d.ders_id
                LEFT JOIN OgretimUyeleri ou ON d.hoca_id = ou.hoca_id
                LEFT JOIN SinavDerslikleri sd ON s.sinav_id = sd.sinav_id
                LEFT JOIN Derslikler dl ON sd.derslik_id = dl.derslik_id
                WHERE s.bolum_id = %s AND s.sinav_turu = %s
                GROUP BY s.sinav_id, d.ders_adi, ou.ad_soyad, s.sinav_tarihi, s.sinav_saati
                ORDER BY s.sinav_tarihi ASC, s.sinav_saati ASC
            """, (self.user["bolum_id"], sinav_turu))

            rows = cur.fetchall()

            if not rows:
                QMessageBox.warning(self, "Uyarı", "Oluşturulmuş sınav programı yok!")
                return

            df = pd.DataFrame(rows, columns=["Tarih", "Saat", "Ders Adı", "Öğretim Elemanı", "Derslik"])

            wb = Workbook()
            ws = wb.active
            ws.title = f"{sinav_turu} Programı"

            turuncu_baslik = "F4B084"
            turuncu_gun = "FCE4D6"
            beyaz = "FFFFFF"

            border = Border(
                left=Side(style="thin"), right=Side(style="thin"),
                top=Side(style="thin"), bottom=Side(style="thin")
            )

            # ---- Ana Başlık ----
            ws.merge_cells("A1:E1")
            ws["A1"] = f"{self.user['bolum_adi']} {sinav_turu.upper()} SINAV PROGRAMI"
            ws["A1"].font = Font(bold=True, size=14)
            ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
            ws["A1"].fill = PatternFill("solid", fgColor=turuncu_baslik)

            # ---- Tablo Başlıkları ----
            headers = ["Tarih", "Sınav Saati", "Ders Adı", "Öğretim Elemanı", "Derslik"]
            ws.append(headers)

            for c in range(1, 6):
                cell = ws.cell(row=2, column=c)
                cell.font = Font(bold=True)
                cell.fill = PatternFill("solid", fgColor=turuncu_baslik)
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = border

            renk_sira = 0
            satir = 3

            for tarih, grup in df.groupby("Tarih"):
                gun_rengi = PatternFill("solid", fgColor=(turuncu_gun if renk_sira % 2 == 0 else beyaz))
                renk_sira += 1

                first_row = satir

                for _, row in grup.iterrows():
                    ws.cell(satir, 2, str(row["Saat"]))
                    ws.cell(satir, 3, row["Ders Adı"])
                    ws.cell(satir, 4, row["Öğretim Elemanı"])
                    ws.cell(satir, 5, row["Derslik"])

                    for c in range(2, 6):
                        cell = ws.cell(row=satir, column=c)
                        cell.fill = gun_rengi
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                        cell.border = border

                    satir += 1

                ws.merge_cells(start_row=first_row, start_column=1, end_row=satir - 1, end_column=1)
                date_cell = ws.cell(first_row, 1)
                date_cell.value = tarih.strftime("%d.%m.%Y")
                date_cell.font = Font(bold=True)
                date_cell.border = border
                date_cell.fill = gun_rengi
                date_cell.alignment = Alignment(text_rotation=90, horizontal="center", vertical="center")

            # Otomatik genişlik
            widths = [15, 15, 40, 30, 25]
            for i, w in enumerate(widths, 1):
                ws.column_dimensions[get_column_letter(i)].width = w

            wb.save(path)
            QMessageBox.information(self, "Başarılı", f"✅ Excel kaydedildi:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hata oluştu:\n{str(e)}")

    def assign_exam_rooms(self):
        """
        Sınavları dersliklere atar - Birden fazla derslik gerekiyorsa böler
        Öğrenci sayısına göre minimum derslik kullanımı sağlar
        """
        try:
            conn = Database.get_connection()
            cur = conn.cursor()

            cur.execute("""
                SELECT derslik_id, derslik_adi, kapasite
                FROM Derslikler
                WHERE aktif = true AND bolum_id = %s
                ORDER BY kapasite DESC
            """, (self.user["bolum_id"],))
            derslikler = cur.fetchall()

            if not derslikler:
                QMessageBox.warning(self, "Uyarı", "Aktif derslik bulunamadı!")
                cur.close()
                conn.close()
                return

            sinav_turu = self.cmb_type.currentText()
            cur.execute("""
                SELECT s.sinav_id, s.ders_id, s.sinav_tarihi, s.sinav_saati, d.ders_adi
                FROM Sinavlar s
                JOIN Dersler d ON s.ders_id = d.ders_id
                WHERE s.bolum_id = %s AND s.durum = 'Planlandı' AND s.sinav_turu = %s
                ORDER BY s.sinav_tarihi, s.sinav_saati
            """, (self.user["bolum_id"], sinav_turu))
            sinavlar = cur.fetchall()

            if not sinavlar:
                QMessageBox.warning(self, "Uyarı", "Henüz sınav bulunamadı!")
                cur.close()
                conn.close()
                return

            cur.execute("""
                SELECT ders_id, COUNT(ogrenci_id) as ogrenci_sayisi
                FROM OgrenciDersleri
                GROUP BY ders_id
            """)
            ogrenci_sayilari = {r[0]: r[1] for r in cur.fetchall()}

            derslik_programi = {d[0]: {} for d in derslikler}
            son_kullanilan_derslikler = {}

            toplam_atama = 0
            uyari_listesi = []

            for sinav_id, ders_id, tarih, saat, ders_adi in sinavlar:
                if isinstance(saat, str):
                    saat_time = datetime.strptime(saat, "%H:%M").time()
                else:
                    saat_time = saat

                if isinstance(tarih, datetime):
                    tarih_date = tarih.date()
                else:
                    tarih_date = tarih

                ogrenci_sayisi = ogrenci_sayilari.get(ders_id, 0)

                if ogrenci_sayisi == 0:
                    uyari_listesi.append(f"⚠️ {ders_adi}: Öğrenci bulunamadı, atlanıyor.")
                    continue

                onceki_slot_derslikler = son_kullanilan_derslikler.get((tarih_date, saat_time), set())

                gereken_derslikler = self._select_optimal_classrooms(
                    derslikler=derslikler,
                    ogrenci_sayisi=ogrenci_sayisi,
                    tarih_date=tarih_date,
                    saat_time=saat_time,
                    derslik_programi=derslik_programi,
                    onceki_slot_derslikler=onceki_slot_derslikler
                )

                if not gereken_derslikler:
                    uyari_listesi.append(
                        f"❌ {ders_adi} ({ogrenci_sayisi} öğrenci): "
                        f"Uygun derslik bulunamadı! Tüm derslikler dolu veya kapasite yetersiz."
                    )
                    continue

                atanan_derslik_adlari = []
                toplam_atanan_kapasite = 0

                for derslik_id, derslik_adi, kapasite in gereken_derslikler:
                    derslik_programi.setdefault(derslik_id, {}).setdefault(tarih_date, []).append(saat_time)

                    son_kullanilan_derslikler.setdefault((tarih_date, saat_time), set()).add(derslik_id)

                    cur.execute("""
                        INSERT INTO SinavDerslikleri (sinav_id, derslik_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                    """, (sinav_id, derslik_id))

                    atanan_derslik_adlari.append(f"{derslik_adi}({kapasite})")
                    toplam_atanan_kapasite += kapasite
                    toplam_atama += 1

                derslik_str = " + ".join(atanan_derslik_adlari)

                if toplam_atanan_kapasite < ogrenci_sayisi:
                    uyari_listesi.append(
                        f"⚠️ {ders_adi}: {ogrenci_sayisi} öğrenci, "
                        f"atanan kapasite: {toplam_atanan_kapasite} → {derslik_str}"
                    )
                else:
                    print(f"✅ {ders_adi}: {ogrenci_sayisi} öğrenci → {derslik_str}")

            conn.commit()
            cur.close()
            conn.close()

            mesaj = f"✅ Toplam {toplam_atama} derslik ataması yapıldı."

            if uyari_listesi:
                mesaj += f"\n\n⚠️ {len(uyari_listesi)} uyarı:\n" + "\n".join(uyari_listesi[:5])
                if len(uyari_listesi) > 5:
                    mesaj += f"\n... ve {len(uyari_listesi) - 5} uyarı daha"

            QMessageBox.information(self, "Derslik Atama Tamamlandı", mesaj)

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Derslik atama hatası: {str(e)}")
            import traceback
            traceback.print_exc()

    def _select_optimal_classrooms(self, derslikler, ogrenci_sayisi, tarih_date,
                                   saat_time, derslik_programi, onceki_slot_derslikler):
        """
        Verilen öğrenci sayısını karşılayacak minimum sayıda derslik seçer

        Args:
            derslikler: Tüm derslikler listesi (kapasite DESC sıralı)
            ogrenci_sayisi: Dersi alan öğrenci sayısı
            tarih_date: Sınav tarihi
            saat_time: Sınav saati
            derslik_programi: Mevcut derslik programı
            onceki_slot_derslikler: Bir önceki slotta kullanılan derslikler

        Returns:
            List[Tuple]: Seçilen derslikler [(derslik_id, derslik_adi, kapasite), ...]
        """

        uygun_derslikler = []
        for derslik_id, derslik_adi, kapasite in derslikler:
            gunluk_program = derslik_programi.get(derslik_id, {}).get(tarih_date, [])

            if saat_time in gunluk_program:
                continue

            if derslik_id in onceki_slot_derslikler:
                continue

            uygun_derslikler.append((derslik_id, derslik_adi, kapasite))

        if not uygun_derslikler:
            return []

        secilen_derslikler = []
        kalan_ogrenci = ogrenci_sayisi

        for derslik in uygun_derslikler:
            derslik_id, derslik_adi, kapasite = derslik
            secilen_derslikler.append(derslik)
            kalan_ogrenci -= kapasite

            if kalan_ogrenci <= 0:
                break

        if kalan_ogrenci > 0:
            print(f"⚠️ {ogrenci_sayisi} öğrenci için yeterli derslik yok. "
                  f"Eksik kapasite: {kalan_ogrenci}")

        return secilen_derslikler
