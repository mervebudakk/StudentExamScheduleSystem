from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QSpinBox,
    QMessageBox, QFormLayout, QToolButton, QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from student_system.core.database import Database
from student_system.views.classroom_seatmap import ClassroomDetailPanel
from PyQt5.QtWidgets import QDialog
import re


class ClassroomManagement(QWidget):
    def __init__(self, user, permission_manager, parent=None):
        super().__init__(parent)
        self.user = user
        self.pm = permission_manager
        self.current_id = None
        self.form_visible = False

        self.setWindowTitle("Derslik Yönetimi")
        self.setMinimumSize(1200, 750)

        self.departments = self._fetch_departments()
        self._build_ui()
        self._load_table()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(25, 25, 25, 25)
        root.setSpacing(20)

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

        title = QLabel("Derslik Yönetimi")
        title.setStyleSheet("color: #2c3e50; font-size: 28px; font-weight: 700; border: none;")
        hl.addWidget(title)
        hl.addStretch()

        btn_new_top = QPushButton("+ Yeni Derslik Ekle")
        btn_new_top.clicked.connect(self._start_create)
        btn_new_top.setCursor(Qt.PointingHandCursor)
        btn_new_top.setFixedHeight(45)
        btn_new_top.setStyleSheet("""
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
        root.addWidget(header)

        toolbar_frame = QFrame()
        toolbar_frame.setStyleSheet("""
            QFrame {
                background: #ffffff;
                border: 1px solid #e1e8ed;
                border-radius: 12px;
            }
        """)
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setContentsMargins(20, 16, 20, 16)
        toolbar.setSpacing(12)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Derslik ara...")
        self.search.setFixedHeight(42)
        self.search.textChanged.connect(self._load_table)
        self.search.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e1e8ed;
                border-radius: 8px;
                padding: 0px 16px;
                font-size: 14px;
                background: #f8f9fa;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 1px solid #5d6dfa;
                background: #ffffff;
            }
        """)

        self.filter_dept = QComboBox()
        self.filter_dept.setFixedHeight(42)
        self._fill_dept_combo(self.filter_dept, include_all=True)
        self.filter_dept.currentIndexChanged.connect(self._load_table)
        self.filter_dept.setStyleSheet("""
            QComboBox {
                border: 1px solid #e1e8ed;
                border-radius: 8px;
                padding: 0px 16px;
                font-size: 14px;
                background: #f8f9fa;
                color: #2c3e50;
                min-width: 200px;
            }
            QComboBox:focus {
                border: 1px solid #5d6dfa;
                background: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 12px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #7f8c8d;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #e1e8ed;
                border-radius: 8px;
                background: white;
                selection-background-color: #f0f3ff;
                selection-color: #5d6dfa;
                padding: 4px;
            }
        """)

        toolbar.addWidget(self.search, 3)
        toolbar.addWidget(self.filter_dept, 2)
        toolbar.addStretch()
        root.addWidget(toolbar_frame)

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

        self.table = QTableWidget(0, 8)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalHeaderLabels(
            ["Kod", "Ad", "Kapasite", "Enine", "Boyuna", "Yapı", "Bölüm", "İşlemler"]
        )
        self.table.horizontalHeader().setStretchLastSection(False)  # StretchLastSection'ı kapatalım

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(QHeaderView.Interactive)

        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)

        self.table.setColumnWidth(7, 240)
        self.table.verticalHeader().setDefaultSectionSize(65)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.itemDoubleClicked.connect(self._open_detail_by_item)
        self.table.setStyleSheet("""
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
            QToolButton {
                border: none;
                padding: 6px 12px;
                color: #5a6c7d;
                font-weight: 500;
                font-size: 13px;
                border-radius: 6px;
                margin: 2px;
            }
            QToolButton:hover {
                background: #f0f3ff;
                color: #5d6dfa;
            }
        """)

        tv.addWidget(self.table)
        root.addWidget(table_frame)

        self.form_box = QFrame()
        self.form_box.setVisible(False)
        self.form_box.setStyleSheet("""
            QFrame { 
                background: white; 
                border: 1px solid #e1e8ed; 
                border-radius: 12px;
            }
            QLineEdit, QSpinBox, QComboBox {
                border: 1px solid #e1e8ed;
                border-radius: 8px;
                padding: 10px 14px;
                background: #f8f9fa;
                font-size: 14px;
                color: #2c3e50;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #5d6dfa;
                background: white;
            }
            QLabel {
                font-size: 14px;
                color: #5a6c7d;
                font-weight: 500;
            }
        """)
        fl = QFormLayout(self.form_box)
        fl.setLabelAlignment(Qt.AlignRight)
        fl.setContentsMargins(24, 20, 24, 20)
        fl.setSpacing(16)

        self.inp_code = QLineEdit()
        self.inp_code.setFixedHeight(42)
        self.inp_name = QLineEdit()
        self.inp_name.setFixedHeight(42)
        self.inp_capacity = QSpinBox()
        self.inp_capacity.setFixedHeight(42)
        self.inp_capacity.setRange(1, 5000)
        self.inp_enine = QSpinBox()
        self.inp_enine.setFixedHeight(42)
        self.inp_enine.setRange(1, 200)
        self.inp_boyuna = QSpinBox()
        self.inp_boyuna.setFixedHeight(42)
        self.inp_boyuna.setRange(1, 200)
        self.inp_yapi = QSpinBox()
        self.inp_yapi.setFixedHeight(42)
        self.inp_yapi.setRange(2, 4)
        self.inp_dept = QComboBox()
        self.inp_dept.setFixedHeight(42)
        self._fill_dept_combo(self.inp_dept, include_all=False)
        if not self.pm.can_manage_all_departments():
            self._select_dept(self.inp_dept, self.user["bolum_id"])
            self.inp_dept.setDisabled(True)

        fl.addRow("Derslik Kodu:", self.inp_code)
        fl.addRow("Derslik Adı:", self.inp_name)
        fl.addRow("Kapasite:", self.inp_capacity)
        fl.addRow("Enine Sıra:", self.inp_enine)
        fl.addRow("Boyuna Sıra:", self.inp_boyuna)
        fl.addRow("Sıra Yapısı (2/3/4):", self.inp_yapi)
        fl.addRow("Bölüm:", self.inp_dept)
        root.addWidget(self.form_box)

        btns = QHBoxLayout()
        btns.setSpacing(12)

        self.btn_save = QPushButton("Kaydet")
        self.btn_save.clicked.connect(self._save)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFixedHeight(45)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background: #10b981;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0px 32px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #059669;
            }
            QPushButton:pressed {
                background: #047857;
            }
        """)

        self.btn_cancel = QPushButton("Vazgeç")
        self.btn_cancel.clicked.connect(self._cancel_form)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setFixedHeight(45)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background: #f1f3f5;
                color: #5a6c7d;
                border: none;
                border-radius: 8px;
                padding: 0px 32px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e9ecef;
            }
            QPushButton:pressed {
                background: #dee2e6;
            }
        """)

        btn_new_bottom = QPushButton("+ Yeni Derslik Ekle")
        btn_new_bottom.clicked.connect(self._start_create)
        btn_new_bottom.setCursor(Qt.PointingHandCursor)
        btn_new_bottom.setFixedHeight(45)
        btn_new_bottom.setStyleSheet(btn_new_top.styleSheet())

        btns.addWidget(self.btn_save)
        btns.addWidget(self.btn_cancel)
        btns.addStretch()
        btns.addWidget(btn_new_bottom)
        root.addLayout(btns)

    def _fetch_departments(self):
        return Database.execute_query(
            "SELECT bolum_id AS id, bolum_adi AS ad FROM Bolumler WHERE aktif = TRUE ORDER BY bolum_adi"
        ) or []

    def _fill_dept_combo(self, combo: QComboBox, include_all=False):
        combo.clear()
        if include_all:
            combo.addItem("Tüm Bölümler", None)
        for d in self.departments:
            combo.addItem(d["ad"], d["id"])
        if include_all and not self.pm.can_manage_all_departments():
            self._select_dept(combo, self.user["bolum_id"])
            combo.setDisabled(True)

    def _select_dept(self, combo: QComboBox, dept_id):
        for i in range(combo.count()):
            if combo.itemData(i) == dept_id:
                combo.setCurrentIndex(i)
                break

    def _load_table(self):
        q = (self.search.text() or "").strip().lower()
        dept_id = self.filter_dept.currentData()

        where, params = [], []

        if q:
            if q.isdigit():
                where.append("(derslik_id = %s OR LOWER(derslik_kodu) LIKE %s)")
                params += [int(q), f"%{q}%"]
            else:
                where.append("(LOWER(derslik_kodu) LIKE %s OR LOWER(derslik_adi) LIKE %s)")
                like = f"%{q}%"
                params += [like, like]

        if dept_id:
            where.append("bolum_id = %s")
            params.append(dept_id)
        elif not self.pm.can_manage_all_departments():
            where.append("bolum_id = %s")
            params.append(self.user["bolum_id"])

        sql = """
            SELECT derslik_id, derslik_kodu, derslik_adi, kapasite,
                   enine_sira_sayisi, boyuna_sira_sayisi, sira_yapisi, bolum_id
            FROM Derslikler
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY derslik_kodu"

        rows = Database.execute_query(sql, tuple(params)) or []

        self.table.setRowCount(0)
        for r in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(r["derslik_kodu"]))
            self.table.setItem(row, 1, QTableWidgetItem(r["derslik_adi"] or ""))
            self.table.setItem(row, 2, QTableWidgetItem(str(r["kapasite"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(r["enine_sira_sayisi"])))
            self.table.setItem(row, 4, QTableWidgetItem(str(r["boyuna_sira_sayisi"])))
            self.table.setItem(row, 5, QTableWidgetItem(str(r["sira_yapisi"])))
            self.table.setItem(row, 6, QTableWidgetItem(self._dept_name(r["bolum_id"])))

            act = QWidget()
            h = QHBoxLayout(act)
            h.setContentsMargins(4, 4, 4, 4)
            h.setSpacing(4)

            btn_view = QToolButton()
            btn_view.setText("Detay")
            btn_view.setCursor(Qt.PointingHandCursor)
            btn_view.clicked.connect(lambda _, _id=r["derslik_id"]: self._open_detail(_id))

            btn_edit = QToolButton()
            btn_edit.setText("Düzenle")
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.clicked.connect(lambda _, _id=r["derslik_id"]: self._start_edit(_id))

            btn_del = QToolButton()
            btn_del.setText("Sil")
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(lambda _, _id=r["derslik_id"]: self._delete_by_id(_id))

            h.addWidget(btn_view)
            h.addWidget(btn_edit)
            h.addWidget(btn_del)
            h.addStretch()

            self.table.setCellWidget(row, 7, act)

        self._cancel_form(silent=True)

    def _dept_name(self, dept_id):
        for d in self.departments:
            if d["id"] == dept_id:
                return d["ad"]
        return "-"

    def _start_create(self):
        self.current_id = None
        self._show_form()
        self._clear_form_defaults()

    def _start_edit(self, derslik_id: int):
        r = Database.execute_query(
            """SELECT derslik_id, bolum_id, derslik_kodu, derslik_adi, kapasite,
                      enine_sira_sayisi, boyuna_sira_sayisi, sira_yapisi
               FROM Derslikler WHERE derslik_id=%s""", (derslik_id,)
        )
        if not r:
            QMessageBox.warning(self, "Bulunamadı", "Kayıt bulunamadı.")
            return

        row = r[0]
        self.current_id = row["derslik_id"]
        self._show_form()
        self.inp_code.setText(row["derslik_kodu"] or "")
        self.inp_name.setText(row["derslik_adi"] or "")
        self.inp_capacity.setValue(int(row["kapasite"] or 1))
        self.inp_enine.setValue(int(row["enine_sira_sayisi"] or 1))
        self.inp_boyuna.setValue(int(row["boyuna_sira_sayisi"] or 1))
        self.inp_yapi.setValue(int(row["sira_yapisi"] or 2))
        self._select_dept(self.inp_dept, row["bolum_id"])

    def _show_form(self):
        if not self.form_visible:
            self.form_box.setVisible(True)
            self.form_visible = True

    def _cancel_form(self, silent=False):
        self.form_box.setVisible(False)
        self.form_visible = False
        self.current_id = None
        if not silent:
            self._clear_form_defaults()

    def _clear_form_defaults(self):
        self.inp_code.clear()
        self.inp_name.clear()
        self.inp_capacity.setValue(30)
        self.inp_enine.setValue(7)
        self.inp_boyuna.setValue(9)
        self.inp_yapi.setValue(3)
        if self.pm.can_manage_all_departments() and self.inp_dept.count() > 0:
            self.inp_dept.setCurrentIndex(0)

    def _validate(self):
        if not self.inp_code.text().strip():
            return False, "Derslik kodu boş olamaz."
        if not self.inp_name.text().strip():
            return False, "Derslik adı boş olamaz."
        if self.inp_capacity.value() <= 0:
            return False, "Kapasite 0'dan büyük olmalı."
        if self.inp_enine.value() <= 0 or self.inp_boyuna.value() <= 0:
            return False, "Enine/Boyuna sıra sayısı 0'dan büyük olmalı."
        if self.inp_yapi.value() not in (2, 3, 4):
            return False, "Sıra yapısı 2, 3 veya 4 olmalı."
        return True, ""

    def _save(self):
        ok, msg = self._validate()
        if not ok:
            QMessageBox.warning(self, "Uyarı", msg)
            return

        dept_id = self.inp_dept.currentData()
        if not self.pm.can_manage_all_departments():
            dept_id = self.user["bolum_id"]

        if self.current_id is None:
            sql = """INSERT INTO Derslikler
                     (bolum_id, derslik_kodu, derslik_adi, kapasite,
                      enine_sira_sayisi, boyuna_sira_sayisi, sira_yapisi, aktif)
                     VALUES (%s,%s,%s,%s,%s,%s,%s, TRUE)"""
            Database.execute_non_query(sql, (
                dept_id,
                self.inp_code.text().strip(),
                self.inp_name.text().strip(),
                int(self.inp_capacity.value()),
                int(self.inp_enine.value()),
                int(self.inp_boyuna.value()),
                int(self.inp_yapi.value()),
            ))
            QMessageBox.information(self, "Bilgi", "Derslik eklendi.")
        else:
            sql = """UPDATE Derslikler SET
                        bolum_id=%s, derslik_kodu=%s, derslik_adi=%s, kapasite=%s,
                        enine_sira_sayisi=%s, boyuna_sira_sayisi=%s, sira_yapisi=%s
                     WHERE derslik_id=%s"""
            Database.execute_non_query(sql, (
                dept_id,
                self.inp_code.text().strip(),
                self.inp_name.text().strip(),
                int(self.inp_capacity.value()),
                int(self.inp_enine.value()),
                int(self.inp_boyuna.value()),
                int(self.inp_yapi.value()),
                self.current_id
            ))
            QMessageBox.information(self, "Bilgi", "Derslik güncellendi.")

        self._load_table()

    def _delete_by_id(self, derslik_id: int):
        if not self.pm.can_manage_all_departments():
            owner = Database.execute_query(
                "SELECT bolum_id FROM Derslikler WHERE derslik_id=%s", (derslik_id,)
            )
            if owner and owner[0]["bolum_id"] != self.user["bolum_id"]:
                QMessageBox.warning(self, "Yetki", "Bu dersliği silme yetkiniz yok.")
                return

        if QMessageBox.question(self, "Sil", "Seçili derslik silinsin mi?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        Database.execute_non_query("DELETE FROM Derslikler WHERE derslik_id=%s", (derslik_id,))
        QMessageBox.information(self, "Bilgi", "Derslik silindi.")
        self._load_table()

    def _open_detail_by_item(self, item):
        derslik_id = self.table.item(item.row(), 0).data(Qt.UserRole)
        if derslik_id:
            self._open_detail(derslik_id)

    def _open_detail(self, derslik_id: int):
        row = Database.execute_query("""
            SELECT derslik_id, bolum_id, derslik_kodu, derslik_adi, kapasite,
                   enine_sira_sayisi, boyuna_sira_sayisi, sira_yapisi
            FROM Derslikler WHERE derslik_id=%s
        """, (derslik_id,))
        if not row:
            QMessageBox.warning(self, "Bulunamadı", "Derslik bulunamadı.")
            return

        rec = row[0]
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Derslik Detayı — {rec['derslik_kodu']}")
        dlg.setMinimumSize(760, 540)

        panel = ClassroomDetailPanel(rec, dlg)
        lay = QVBoxLayout(dlg)
        lay.addWidget(panel)

        dlg.exec_()