from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox, QSpinBox,
    QMessageBox, QFormLayout, QCheckBox
)
from PyQt5.QtCore import Qt
from student_system.core.database import Database


class ClassroomManagement(QWidget):
    def __init__(self, user, permission_manager, parent=None):
        super().__init__(parent)
        self.user = user
        self.pm = permission_manager
        self.current_id = None

        self.setWindowTitle("Derslik Yönetimi")
        self.setMinimumSize(1000, 650)

        self.departments = self._fetch_departments()
        self._build_ui()
        self._load_table()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # Başlık
        header = QFrame()
        hl = QHBoxLayout(header)
        title = QLabel("🏫  Derslik Yönetimi")
        title.setStyleSheet("color:#27ae60; font-size:20px; font-weight:bold;")
        hl.addWidget(title); hl.addStretch()
        root.addWidget(header)

        # Üst araç çubuğu: arama + filtre + yenile
        toolbar = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("Ad/Kod/Bina ara...")
        self.search.textChanged.connect(self._load_table)

        self.filter_dept = QComboBox()
        self._fill_dept_combo(self.filter_dept, include_all=True)
        self.filter_dept.currentIndexChanged.connect(self._load_table)

        self.only_active = QCheckBox("Sadece aktif")
        self.only_active.setChecked(True)
        self.only_active.stateChanged.connect(self._load_table)

        btn_refresh = QPushButton("↻ Yenile"); btn_refresh.clicked.connect(self._load_table)

        toolbar.addWidget(self.search, 2)
        toolbar.addWidget(self.filter_dept, 1)
        toolbar.addWidget(self.only_active)
        toolbar.addStretch()
        toolbar.addWidget(btn_refresh)
        root.addLayout(toolbar)

        # Tablo
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Ad", "Kapasite", "Bina", "Kat", "Bölüm", "Aktif"]
        )
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.cellClicked.connect(self._pick_row)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        # Form
        form_box = QFrame(); fl = QFormLayout(form_box); fl.setLabelAlignment(Qt.AlignRight)

        self.inp_name = QLineEdit()
        self.inp_building = QLineEdit()
        self.inp_floor = QSpinBox(); self.inp_floor.setRange(-5, 50)
        self.inp_capacity = QSpinBox(); self.inp_capacity.setRange(1, 2000)
        self.inp_active = QCheckBox("Aktif"); self.inp_active.setChecked(True)

        self.inp_dept = QComboBox()
        self._fill_dept_combo(self.inp_dept, include_all=False)
        # Bölüm yetkisi yoksa kilitle ve kendi bölümünü sabitle
        if not self.pm.can_manage_all_departments():
            self._select_dept(self.inp_dept, self.user["bolum_id"])
            self.inp_dept.setDisabled(True)

        fl.addRow("Derslik Adı:", self.inp_name)
        fl.addRow("Bina:", self.inp_building)
        fl.addRow("Kat:", self.inp_floor)
        fl.addRow("Kapasite:", self.inp_capacity)
        fl.addRow("Bölüm:", self.inp_dept)
        fl.addRow("", self.inp_active)
        root.addWidget(form_box)

        # Butonlar
        btns = QHBoxLayout()
        self.btn_save = QPushButton("Kaydet"); self.btn_save.clicked.connect(self._save)
        self.btn_clear = QPushButton("Temizle"); self.btn_clear.clicked.connect(self._clear)
        self.btn_del = QPushButton("Sil"); self.btn_del.clicked.connect(self._delete)
        btns.addWidget(self.btn_save); btns.addWidget(self.btn_clear); btns.addStretch(); btns.addWidget(self.btn_del)
        root.addLayout(btns)

    # ---------- Data ----------
    def _fetch_departments(self):
        return Database.execute_query(
            "SELECT bolum_id AS id, bolum_adi AS ad FROM bolumler WHERE aktif = TRUE ORDER BY bolum_adi"
        ) or []

    def _fill_dept_combo(self, combo: QComboBox, include_all=False):
        combo.clear()
        if include_all:
            combo.addItem("Tüm Bölümler", None)
        for d in self.departments:
            combo.addItem(d["ad"], d["id"])
        if include_all and not self.pm.can_manage_all_departments():
            # filtrede sabitle
            self._select_dept(combo, self.user["bolum_id"])
            combo.setDisabled(True)

    def _select_dept(self, combo: QComboBox, dept_id):
        for i in range(combo.count()):
            if combo.itemData(i) == dept_id:
                combo.setCurrentIndex(i); break

    def _load_table(self):
        q = (self.search.text() or "").strip().lower()
        dept_id = self.filter_dept.currentData()
        only_active = self.only_active.isChecked()

        where, params = [], []

        if q:
            if q.isdigit():
                where.append("derslik_id = %s"); params.append(int(q))
            else:
                where.append("(LOWER(derslik_adi) LIKE %s OR LOWER(bina) LIKE %s)")
                like = f"%{q}%"; params += [like, like]

        if dept_id:
            where.append("bolum_id = %s"); params.append(dept_id)
        elif not self.pm.can_manage_all_departments():
            where.append("bolum_id = %s"); params.append(self.user["bolum_id"])

        if only_active:
            where.append("aktif = TRUE")

        sql = "SELECT derslik_id, derslik_adi, kapasite, bina, kat, bolum_id, aktif FROM derslikler"
        if where: sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY bina NULLS LAST, kat NULLS LAST, derslik_adi"

        rows = Database.execute_query(sql, tuple(params)) or []
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount(); self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(r["derslik_id"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["derslik_adi"]))
            self.table.setItem(i, 2, QTableWidgetItem(str(r["kapasite"])))
            self.table.setItem(i, 3, QTableWidgetItem(r["bina"] or ""))
            self.table.setItem(i, 4, QTableWidgetItem("" if r["kat"] is None else str(r["kat"])))
            self.table.setItem(i, 5, QTableWidgetItem(self._dept_name(r["bolum_id"])))
            self.table.setItem(i, 6, QTableWidgetItem("Evet" if r["aktif"] else "Hayır"))

        self.current_id = None

    def _dept_name(self, dept_id):
        for d in self.departments:
            if d["id"] == dept_id: return d["ad"]
        return "-"

    def _pick_row(self, row, _col):
        try:
            id_item = self.table.item(row, 0)
            if id_item is None:
                self.current_id = None
                return
            self.current_id = int(id_item.text())
        except Exception:
            self.current_id = None
            return

        # Koruyucu erişimler
        def _safe_text(r, c):
            it = self.table.item(r, c)
            return it.text() if it is not None else ""

        self.inp_name.setText(_safe_text(row, 1))
        cap_txt = _safe_text(row, 2)
        self.inp_capacity.setValue(int(cap_txt) if cap_txt.isdigit() else 0)
        self.inp_building.setText(_safe_text(row, 3))

        kat_txt = _safe_text(row, 4)
        try:
            self.inp_floor.setValue(int(kat_txt) if kat_txt else 0)
        except Exception:
            self.inp_floor.setValue(0)

        dept_name = _safe_text(row, 5)
        self._select_dept(self.inp_dept, self._dept_id_by_name(dept_name))

        self.inp_active.setChecked(_safe_text(row, 6) == "Evet")

    def _dept_id_by_name(self, name):
        for d in self.departments:
            if d["ad"] == name: return d["id"]
        return None

    # ---------- Actions ----------
    def _validate(self):
        if not self.inp_name.text().strip():
            return False, "Derslik adı boş olamaz."
        if self.inp_capacity.value() <= 0:
            return False, "Kapasite 0'dan büyük olmalı."
        return True, ""

    def _save(self):
        ok, msg = self._validate()
        if not ok:
            QMessageBox.warning(self, "Uyarı", msg); return

        dept_id = self.inp_dept.currentData()
        if not self.pm.can_manage_all_departments():
            dept_id = self.user["bolum_id"]

        if self.current_id is None:
            sql = """INSERT INTO derslikler
                     (derslik_adi, kapasite, bina, kat, bolum_id, aktif)
                     VALUES (%s,%s,%s,%s,%s,%s)"""
            Database.execute_non_query(sql, (
                self.inp_name.text().strip(),
                int(self.inp_capacity.value()),
                self.inp_building.text().strip() or None,
                int(self.inp_floor.value()),
                dept_id,
                self.inp_active.isChecked()
            ))
            QMessageBox.information(self, "Bilgi", "Derslik eklendi.")
        else:
            sql = """UPDATE derslikler SET
                        derslik_adi=%s, kapasite=%s, bina=%s, kat=%s,
                        bolum_id=%s, aktif=%s
                     WHERE derslik_id=%s"""
            Database.execute_non_query(sql, (
                self.inp_name.text().strip(),
                int(self.inp_capacity.value()),
                self.inp_building.text().strip() or None,
                int(self.inp_floor.value()),
                dept_id,
                self.inp_active.isChecked(),
                self.current_id
            ))
            QMessageBox.information(self, "Bilgi", "Derslik güncellendi.")
        self._clear(); self._load_table()

    def _delete(self):
        if self.current_id is None:
            QMessageBox.warning(self, "Uyarı", "Silmek için tablodan bir derslik seçin."); return

        # Bölüm sahipliği kontrolü
        if not self.pm.can_manage_all_departments():
            owner = Database.execute_query(
                "SELECT bolum_id FROM derslikler WHERE derslik_id=%s", (self.current_id,)
            )
            if owner and owner[0]["bolum_id"] != self.user["bolum_id"]:
                QMessageBox.warning(self, "Yetki", "Bu dersliği silme yetkiniz yok."); return

        if QMessageBox.question(self, "Sil", "Seçili derslik silinsin mi?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        Database.execute_non_query("DELETE FROM derslikler WHERE derslik_id=%s", (self.current_id,))
        QMessageBox.information(self, "Bilgi", "Derslik silindi.")
        self._clear(); self._load_table()

    def _clear(self):
        self.current_id = None
        self.inp_name.clear(); self.inp_building.clear()
        self.inp_floor.setValue(0); self.inp_capacity.setValue(30)
        self.inp_active.setChecked(True)
        if self.pm.can_manage_all_departments():
            if self.inp_dept.count() > 0: self.inp_dept.setCurrentIndex(0)
