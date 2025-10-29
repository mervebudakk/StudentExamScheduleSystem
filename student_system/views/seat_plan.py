# student_system/views/seat_plan.py
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QComboBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog
)
from student_system.core.database import Database
from student_system.views.classroom_seatmap import SeatMapWidget
import os

# --- PDF Kütüphaneleri ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
except ImportError:
    print("HATA: 'reportlab' kütüphanesi yüklü değil. Lütfen 'pip install reportlab' komutu ile yükleyin.")
    # Bu importlar olmadan PDF fonksiyonu çalışmayacaktır.
    pass

# --- Türkçe Karakterler için Font Kaydı ---
try:
    # Windows yolları
    font_paths = [
        "C:/Windows/Fonts/Verdana.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/Tahoma.ttf"
    ]
    font_registered = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('Verdana', font_path))
            font_registered = True
            break
    if not font_registered:
        print("Uyarı: Verdana/Arial fontu bulunamadı. PDF'te Türkçe karakter sorunu olabilir.")

    # PDF stilleri
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Baslik',
        fontName='Verdana' if font_registered else 'Helvetica-Bold',
        fontSize=14,
        alignment=TA_CENTER,
        spaceBottom=10
    ))
    styles.add(ParagraphStyle(
        name='AltBaslik',
        fontName='Verdana' if font_registered else 'Helvetica',
        fontSize=11,
        alignment=TA_LEFT,
        spaceBottom=5
    ))
    styles.add(ParagraphStyle(
        name='TabloIci',
        fontName='Verdana' if font_registered else 'Helvetica',
        fontSize=9
    ))
    if 'Normal' not in styles:
        styles.add(ParagraphStyle(name='Normal', fontName='Verdana' if font_registered else 'Helvetica', fontSize=10))

except Exception as e:
    print(f"PDF Font hatası: {e}")
    if 'styles' not in locals():
        styles = {}
        print("Acil Durum: PDF Stilleri yüklenemedi!")


# ---


class SeatPlanView(QWidget):
    """
    MainDashboard içerik alanında çalışan 'Oturma Planı' ekranı.
    Ayrı pencere açmaz; tek bir QWidget’tır.
    """

    def __init__(self, user, permission_manager, parent=None):
        super().__init__(parent)
        self.user = user
        self.pm = permission_manager
        self.current_exam_id = None
        self.current_room = None
        self.rooms = []  # Seçili sınava ait tüm derslikleri tutar
        self.students = []  # Seçili sınava giren tüm öğrencileri tutar
        self._build_ui()
        self._load_exams()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # Üst başlık
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27ae60, stop:1 #16a085);
                border-radius: 12px;
            }
            QLabel { color:white; }
        """)
        hl = QHBoxLayout(header);
        hl.setContentsMargins(18, 14, 18, 14)
        title = QLabel("💺 Oturma Planı")
        title.setStyleSheet("font-size:20px; font-weight:700;")
        hl.addWidget(title);
        hl.addStretch()

        self.btn_generate = QPushButton("⚙️ Plan Oluştur/Güncelle (Tüm Derslikler)")
        self.btn_generate.clicked.connect(self._generate_plan_for_all_rooms)
        self.btn_generate.setCursor(Qt.PointingHandCursor)

        self.btn_pdf = QPushButton("⬇️ PDF İndir (Seçili Derslik)")
        self.btn_pdf.clicked.connect(self._export_pdf)
        self.btn_pdf.setCursor(Qt.PointingHandCursor)

        hl.addWidget(self.btn_generate)
        hl.addWidget(self.btn_pdf)
        root.addWidget(header)

        # Filtre/Seçim çubuğu
        toolbar = QFrame()
        toolbar.setStyleSheet("""
            QFrame { background:#ffffff; border:2px solid #ecf0f1; border-radius:12px; }
            QComboBox { border:2px solid #bdc3c7; border-radius:8px; padding:6px 10px; background:white; }
        """)
        tl = QHBoxLayout(toolbar);
        tl.setContentsMargins(14, 12, 14, 12)

        self.cmb_exam = QComboBox()
        self.cmb_exam.currentIndexChanged.connect(self._on_exam_changed)

        tl.addWidget(QLabel("Sınav:"));
        tl.addWidget(self.cmb_exam, 1)
        root.addWidget(toolbar)

        # Sınav-Derslik listesi
        table_wrap = QFrame()
        table_wrap.setStyleSheet("QFrame { background:white; border:2px solid #ecf0f1; border-radius:12px; }")
        tv = QVBoxLayout(table_wrap);
        tv.setContentsMargins(10, 10, 10, 10)

        self.lbl_room_info = QLabel("Sınava Atanan Derslikler")
        self.lbl_room_info.setStyleSheet("font-size:14px; font-weight:700; color:#2c3e50; padding: 5px;")
        tv.addWidget(self.lbl_room_info)

        self.tbl_rooms = QTableWidget(0, 4)
        self.tbl_rooms.setHorizontalHeaderLabels(["Derslik", "Kapasite", "Enine×Boyuna×Yapı", "Atanan Öğrenci"])
        self.tbl_rooms.horizontalHeader().setStretchLastSection(True)
        self.tbl_rooms.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_rooms.setEditTriggers(self.tbl_rooms.NoEditTriggers)
        self.tbl_rooms.setSelectionBehavior(self.tbl_rooms.SelectRows)
        self.tbl_rooms.itemSelectionChanged.connect(self._on_table_select)

        tv.addWidget(self.tbl_rooms)
        root.addWidget(table_wrap, 2)

        # Önizleme (SeatMapWidget)
        preview_wrap = QFrame()
        preview_wrap.setStyleSheet("QFrame { background:white; border:2px solid #ecf0f1; border-radius:12px; }")
        pv = QVBoxLayout(preview_wrap);
        pv.setContentsMargins(12, 1, 12, 1);
        pv.setSpacing(1)

        self.preview_title = QLabel("Derslik Oturum Önizlemesi (Görselleştirmek için tablodan derslik seçiniz.)")
        self.preview_title.setStyleSheet("font-size:14px; font-weight:700; color:#2c3e50;")
        pv.addWidget(self.preview_title, 0)

        self.preview = SeatMapWidget(enine=6, boyuna=10, yapi=3, kapasite=180, placements=None)  # varsayılan
        pv.addWidget(self.preview, 1)
        root.addWidget(preview_wrap, 5)

    # ---------- Data ----------
    def _load_exams(self):
        """Sınavları ComboBox'a yükler."""
        if self.pm.can_manage_all_departments():
            rows = Database.execute_query("""
                SELECT s.sinav_id, s.sinav_tarihi, s.sinav_saati, s.sinav_turu,
                       d.ders_kodu, d.ders_adi
                FROM sinavlar s
                JOIN dersler d ON d.ders_id = s.ders_id
                ORDER BY s.sinav_tarihi, s.sinav_saati
            """)
        else:
            rows = Database.execute_query("""
                SELECT s.sinav_id, s.sinav_tarihi, s.sinav_saati, s.sinav_turu,
                       d.ders_kodu, d.ders_adi
                FROM sinavlar s
                JOIN dersler d ON d.ders_id = s.ders_id
                WHERE s.bolum_id = %s
                ORDER BY s.sinav_tarihi, s.sinav_saati
            """, (self.user["bolum_id"],))

        self.cmb_exam.clear()
        self.cmb_exam.addItem("Lütfen bir sınav seçin...", None)
        for r in rows or []:
            saat_str = r["sinav_saati"].strftime('%H:%M') if r["sinav_saati"] else "--:--"
            tarih_str = r["sinav_tarihi"].strftime('%d.%m.%Y') if r["sinav_tarihi"] else "---"
            label = f"{r['ders_kodu']} – {r['ders_adi']} ({r['sinav_turu']}) — {tarih_str} {saat_str}"
            self.cmb_exam.addItem(label, r["sinav_id"])

        if rows:
            self.cmb_exam.setCurrentIndex(0)

    def _on_exam_changed(self, _):
        """Sınav seçildiğinde, o sınava ait derslikleri ve öğrencileri yükler."""
        self.current_exam_id = self.cmb_exam.currentData()
        if not self.current_exam_id:
            self._clear_selection()
            return

        # 1. Sınava atanan derslikleri yükle
        self.rooms = Database.execute_query("""
            SELECT d.derslik_id, d.derslik_kodu, d.derslik_adi, d.kapasite,
                   d.enine_sira_sayisi, d.boyuna_sira_sayisi, d.sira_yapisi,
                   COALESCE((
                     SELECT COUNT(*)
                     FROM oturmaplani op
                     WHERE op.sinav_id = sd.sinav_id AND op.derslik_id = d.derslik_id
                   ),0) AS atanan
            FROM sinavderslikleri sd
            JOIN derslikler d ON d.derslik_id = sd.derslik_id
            WHERE sd.sinav_id = %s
            ORDER BY d.derslik_kodu
        """, (self.current_exam_id,)) or []

        # 2. Sınava giren öğrencileri yükle
        self.students = Database.execute_query("""
            SELECT o.ogrenci_id
            FROM ogrencidersleri od
            JOIN sinavlar s ON s.ders_id = od.ders_id AND s.sinav_id = %s
            JOIN ogrenciler o ON o.ogrenci_id = od.ogrenci_id
            ORDER BY o.ogrenci_no
        """, (self.current_exam_id,)) or []

        # 3. Toplam bilgileri etikete yaz
        total_capacity = sum(r['kapasite'] for r in self.rooms)
        self.lbl_room_info.setText(
            f"Sınava Atanan Derslikler ({len(self.rooms)} derslik) | "
            f"Toplam Öğrenci: {len(self.students)} | "
            f"Toplam Kapasite: {total_capacity}"
        )

        # 4. Derslik tablosunu doldur
        self.tbl_rooms.setRowCount(0)
        for r in self.rooms:
            row = self.tbl_rooms.rowCount();
            self.tbl_rooms.insertRow(row)
            self.tbl_rooms.setItem(row, 0, QTableWidgetItem(f"{r['derslik_kodu']} - {r.get('derslik_adi') or ''}"))
            self.tbl_rooms.setItem(row, 1, QTableWidgetItem(str(r['kapasite'])))
            self.tbl_rooms.setItem(
                row, 2,
                QTableWidgetItem(f"{r['enine_sira_sayisi']}×{r['boyuna_sira_sayisi']} × {r['sira_yapisi']}'li")
            )
            atanan_item = QTableWidgetItem(str(r['atanan']))
            if r['atanan'] == 0:
                atanan_item.setForeground(Qt.red)
            elif r['atanan'] < r['kapasite']:
                atanan_item.setForeground(Qt.blue)
            else:
                atanan_item.setForeground(Qt.darkGreen)
            self.tbl_rooms.setItem(row, 3, atanan_item)

        if self.rooms:
            self.tbl_rooms.selectRow(0)
            self._on_table_select()
        else:
            self._clear_selection()

    def _clear_selection(self):
        """Ekranı temizler."""
        self.current_exam_id = None
        self.rooms = []
        self.students = []
        self.tbl_rooms.setRowCount(0)
        self.lbl_room_info.setText("Sınava Atanan Derslikler")
        self._apply_preview(None, None)

    def _on_table_select(self):
        """Tablodan bir derslik seçildiğinde önizlemeyi günceller."""
        selected_rows = self.tbl_rooms.selectionModel().selectedRows()
        if not selected_rows:
            self.current_room = None
            self._apply_preview(None, None)
            return

        selected_row_index = selected_rows[0].row()
        if selected_row_index < 0 or selected_row_index >= len(self.rooms):
            return

        data = self.rooms[selected_row_index]

        # Seçili derslik için öğrenci yerleşimlerini çek
        derslik_id = data.get("derslik_id")
        sinav_id = self.current_exam_id
        placements = None

        if derslik_id and sinav_id:
            placements = Database.execute_query("""
                SELECT op.sira_no, op.sutun_no, op.koltuk_no,
                       o.ogrenci_no, o.ad_soyad
                FROM oturmaplani op
                JOIN ogrenciler o ON o.ogrenci_id = op.ogrenci_id
                WHERE op.sinav_id = %s AND op.derslik_id = %s
                ORDER BY op.sira_no, op.sutun_no, op.koltuk_no
            """, (sinav_id, derslik_id)) or []

        self._apply_preview(data, placements)

    def _apply_preview(self, data, placements=None):
        """Önizleme widget'ını seçilen derslik verisiyle günceller."""
        self.current_room = data

        # Eski widget'ı güvenle kaldır
        if hasattr(self, 'preview') and self.preview:
            parent = self.preview.parent()
            if parent and parent.layout():
                parent.layout().removeWidget(self.preview)
            self.preview.deleteLater()
            self.preview = None

        if data is None:
            self.preview_title.setText("Derslik Oturum Önizlemesi (Görselleştirmek için tablodan seçin)")
            self.preview = SeatMapWidget(enine=1, boyuna=1, yapi=1, kapasite=0, placements=None)
        else:
            enine = int(data['enine_sira_sayisi'] or 1)
            boyuna = int(data['boyuna_sira_sayisi'] or 1)
            yapi = int(data['sira_yapisi'] or 1)
            kapasite = int(data['kapasite'] or 0)

            self.preview_title.setText(
                f"Önizleme — {data['derslik_kodu']} (Kapasite: {kapasite}) | "
                f"Düzen: {boyuna} satır × {enine} grup × {yapi}'li"
            )
            self.preview = SeatMapWidget(
                enine=enine,
                boyuna=boyuna,
                yapi=yapi,
                kapasite=kapasite,
                placements=placements
            )

        # Yeni widget'ı ekle
        self.preview_title.parent().layout().addWidget(self.preview)

    # ---------- Actions ----------
    def _generate_plan_for_all_rooms(self):
        """
        Seçili sınav için TÜM dersliklere öğrencileri dağıtır.
        """
        if not self.current_exam_id:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir sınav seçiniz.")
            return

        sinav_id = self.current_exam_id
        ogrenciler = self.students
        derslikler = self.rooms

        if not ogrenciler:
            QMessageBox.warning(self, "Uyarı", "Bu sınava kayıtlı öğrenci bulunamadı.")
            return

        if not derslikler:
            QMessageBox.warning(self, "Hata",
                                "Bu sınav için hiç derslik atanmamış. Önce 'Sınav Programı' ekranından derslik ataması yapın.")
            return

        total_capacity = sum(r['kapasite'] for r in derslikler)
        total_students = len(ogrenciler)

        if total_students > total_capacity:
            QMessageBox.critical(
                self,
                "Hata: Kapasite Yetersiz!",
                f"Bu sınav için kapasite yetersiz! \n\n"
                f"Sınava Giren Öğrenci: {total_students}\n"
                f"Toplam Derslik Kapasitesi: {total_capacity}\n"
                f"Gereken Fark: {total_students - total_capacity}\n\n"
                f"Planlama yapılamadı. Lütfen daha fazla derslik ekleyin."
            )
            return

        try:
            # 1. Eski planı temizle (Sadece bu sınav için)
            Database.execute_non_query(
                "DELETE FROM oturmaplani WHERE sinav_id = %s",
                (sinav_id,)
            )

            # 2. Öğrencileri tüm dersliklere dağıt
            plan_values = []
            ogr_index = 0

            for room in derslikler:
                derslik_id = room["derslik_id"]
                enine = int(room['enine_sira_sayisi'])
                boyuna = int(room['boyuna_sira_sayisi'])
                yapi = int(room['sira_yapisi'])
                kapasite = int(room['kapasite'])

                placed_in_this_room = 0


                for r in range(1, boyuna + 1):
                    for c in range(1, enine + 1):
                        for k in range(1, yapi + 1):  # k = koltuk_no (1-based)

                            # --- SOSYAL MESAFE KURAL KONTROLÜ ---
                            is_valid_seat = False
                            if yapi == 1:
                                is_valid_seat = True
                            elif yapi == 2:
                                # Forum mesajında "2lik sıralara ise sıranın sağ tarafına" diyordu.
                                # Bu k=2 (sağ taraf) anlamına gelir.
                                is_valid_seat = (k == 2)
                            elif yapi == 3 and (k == 1 or k == 3):  # 3'lünün kenarları (k=1, k=3)
                                is_valid_seat = True
                            elif yapi == 4 and (k == 1 or k == 4):  # 4'lünün kenarları (k=1, k=4)
                                is_valid_seat = True
                            # --- KURAL KONTROLÜ SONU ---

                            # SADECE ŞU DURUMLARDA ÖĞRENCİ ATA:
                            # 1. Koltuk geçerliyse (is_valid_seat == True)
                            # 2. Atanacak öğrenci kaldıysa (ogr_index < total_students)
                            # 3. Dersliğin (sınav) kapasitesi dolmadıysa (placed_in_this_room < kapasite)

                            if is_valid_seat and ogr_index < total_students and placed_in_this_room < kapasite:
                                ogrenci_id = ogrenciler[ogr_index]['ogrenci_id']

                                plan_values.append(
                                    (sinav_id, ogrenci_id, derslik_id, r, c, k)
                                )
                                ogr_index += 1
                                placed_in_this_room += 1

                            # 'else' durumunda (örn. 3'lünün ortası k=2 ise)
                            # hiçbir şey yapılmaz ve o koltuk veritabanına eklenmez (boş kalır).

                        # Kapasite veya öğrenci bittiyse iç döngüleri kır
                        if ogr_index >= total_students or placed_in_this_room >= kapasite: break
                    if ogr_index >= total_students or placed_in_this_room >= kapasite: break

                if ogr_index >= total_students:
                    break

                    # 3. Veritabanına toplu kayıt
            if plan_values:
                Database.execute_many("""
                    INSERT INTO oturmaplani (sinav_id, ogrenci_id, derslik_id, sira_no, sutun_no, koltuk_no)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (sinav_id, ogrenci_id) DO NOTHING
                """, plan_values)

            if ogr_index < total_students:
                QMessageBox.warning(
                    self,
                    "Uyarı: Kısmi Yerleştirme",
                    f"Tüm derslikler dolsa da öğrenciler açıkta kaldı!\n\n"
                    f"Toplam Öğrenci: {total_students}\n"
                    f"Yerleştirilen Öğrenci: {ogr_index}\n"
                    f"Açıkta Kalan: {total_students - ogr_index}\n\n"
                    f"Bunun nedeni (Enine*Boyuna*Yapı) düzeninin kapasiteden küçük olması olabilir."
                )
            else:
                QMessageBox.information(self, "Başarılı",
                                        f"Tüm dersliklere toplam {ogr_index} öğrenci başarıyla yerleştirildi.")

            self._on_exam_changed(self.cmb_exam.currentIndex())

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Plan oluşturulurken hata:\n{e}")

    def _export_pdf(self):
        """Sadece tablodan seçili olan derslik için PDF alır."""

        try:
            _ = SimpleDocTemplate, A4, cm, Paragraph, Table, TableStyle, colors, styles
        except NameError:
            QMessageBox.critical(self, "Hata",
                                 "'reportlab' kütüphanesi bulunamadı veya düzgün yüklenemedi.\n"
                                 "PDF oluşturulamaz. Lütfen terminalden 'pip install reportlab' komutunu çalıştırın.")
            return

        if not self.current_exam_id or not self.current_room:
            QMessageBox.warning(self, "Uyarı", "Lütfen PDF'ini almak için tablodan bir derslik seçiniz.")
            return

        derslik_id = self.current_room["derslik_id"]

        try:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Oturma Planı PDF Kaydet",
                f"OturmaPlani_{self.current_room['derslik_kodu']}.pdf",
                "PDF Dosyası (*.pdf)"
            )
            if not path:
                return

            header_sql = """
                SELECT 
                    s.sinav_tarihi, s.sinav_saati, s.sinav_turu,
                    d.ders_kodu, d.ders_adi,
                    dl.derslik_kodu, dl.derslik_adi
                FROM sinavlar s
                JOIN dersler d    ON d.ders_id = s.ders_id
                JOIN derslikler dl ON dl.derslik_id = %s
                WHERE s.sinav_id = %s
            """
            header = Database.execute_query(header_sql, (derslik_id, self.current_exam_id))
            if not header:
                QMessageBox.warning(self, "Uyarı", "Sınav başlık bilgileri bulunamadı.");
                return
            h = header[0]

            rows_sql = """
                SELECT op.sira_no, op.sutun_no, op.koltuk_no,
                       o.ogrenci_no,
                       o.ad_soyad
                FROM oturmaplani op
                JOIN ogrenciler o ON o.ogrenci_id = op.ogrenci_id
                WHERE op.sinav_id = %s AND op.derslik_id = %s
                ORDER BY op.sira_no, op.sutun_no, op.koltuk_no
            """
            rows = Database.execute_query(rows_sql, (self.current_exam_id, derslik_id)) or []

            if not rows:
                QMessageBox.warning(
                    self,
                    "Uyarı: Plan Boş",
                    f"'{h['derslik_kodu']}' dersliği için oluşturulmuş bir oturma planı (veya atanmış öğrenci) bulunamadı.\n\n"
                    "Lütfen önce 'Plan Oluştur/Güncelle' butonuna basın."
                )
                return

            doc = SimpleDocTemplate(path, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
            story = []

            style_baslik = styles.get('Baslik', ParagraphStyle(name='FallbackBaslik', fontSize=14, alignment=TA_CENTER))
            style_alt_baslik = styles.get('AltBaslik',
                                          ParagraphStyle(name='FallbackAltBaslik', fontSize=11, alignment=TA_LEFT))
            style_normal = styles.get('Normal', ParagraphStyle(name='FallbackNormal', fontSize=10))
            style_tablo_ici = styles.get('TabloIci', ParagraphStyle(name='FallbackTabloIci', fontSize=9))

            # Başlık
            story.append(Paragraph("SINAV OTURMA PLANI", style_baslik))
            story.append(Paragraph(f"<b>Ders:</b> {h['ders_kodu']} - {h['ders_adi']}", style_alt_baslik))
            story.append(Paragraph(f"<b>Sınav Türü:</b> {h['sinav_turu']}", style_alt_baslik))
            story.append(
                Paragraph(f"<b>Derslik:</b> {h['derslik_kodu']} - {h.get('derslik_adi', '')}", style_alt_baslik))
            saat_str = h["sinav_saati"].strftime('%H:%M') if h["sinav_saati"] else "--:--"
            tarih_str = h["sinav_tarihi"].strftime('%d.%m.%Y') if h["sinav_tarihi"] else "---"
            story.append(Paragraph(f"<b>Tarih / Saat:</b> {tarih_str} / {saat_str}", style_alt_baslik))
            story.append(Paragraph("<hr/>", style_normal))

            # Tablo Verisi
            data = [
                ["Sıra", "Sütun (Masa)", "Koltuk", "Öğrenci No", "Ad Soyad"]
            ]

            for r in rows:
                data.append([
                    Paragraph(str(r['sira_no']), style_tablo_ici),
                    Paragraph(str(r['sutun_no']), style_tablo_ici),
                    Paragraph(str(r['koltuk_no']), style_tablo_ici),
                    Paragraph(str(r['ogrenci_no']), style_tablo_ici),
                    Paragraph(r['ad_soyad'], style_tablo_ici)
                ])

            # Tablo Stili
            ts = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#27ae60")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Verdana' if font_registered else 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ])
            for i in range(1, len(data)):
                if i % 2 == 0:
                    ts.add('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F0F0F0"))
                else:
                    ts.add('BACKGROUND', (0, i), (-1, i), colors.white)

            table = Table(data, colWidths=[2 * cm, 2.5 * cm, 2 * cm, 3 * cm, 6.5 * cm])
            table.setStyle(ts)
            story.append(table)

            doc.build(story)
            QMessageBox.information(self, "Başarılı", f"PDF başarıyla kaydedildi:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "PDF Hatası", f"PDF oluşturulamadı:\n{e}")