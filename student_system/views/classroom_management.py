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
        self.search = QLineEdit(); self.search.setPlaceholderText("ID/Kod/Ad ara...")
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

        # Tablo (şemaya uygun kolonlar)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Kod", "Ad", "Kapasite", "Enine", "Boyuna", "Yapı", "Bölüm", "Aktif"]
        )
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.cellClicked.connect(self._pick_row)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table)

        # Form (şemaya uygun alanlar)
        form_box = QFrame(); fl = QFormLayout(form_box); fl.setLabelAlignment(Qt.AlignRight)

        self.inp_code = QLineEdit()
        self.inp_name = QLineEdit()
        self.inp_capacity = QSpinBox(); self.inp_capacity.setRange(1, 5000)
        self.inp_enine = QSpinBox(); self.inp_enine.setRange(1, 200)
        self.inp_boyuna = QSpinBox(); self.inp_boyuna.setRange(1, 200)
        self.inp_yapi = QSpinBox(); self.inp_yapi.setRange(2, 4)  # 2/3/4 destekli
        self.inp_active = QCheckBox("Aktif"); self.inp_active.setChecked(True)

        self.inp_dept = QComboBox()
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
                combo.setCurrentIndex(i); break

    def _load_table(self):
        q = (self.search.text() or "").strip().lower()
        dept_id = self.filter_dept.currentData()
        only_active = self.only_active.isChecked()

        where, params = [], []

        if q:
            if q.isdigit():
                where.append("(derslik_id = %s OR LOWER(derslik_kodu) LIKE %s)"); params += [int(q), f"%{q}%"]
            else:
                where.append("(LOWER(derslik_kodu) LIKE %s OR LOWER(derslik_adi) LIKE %s)")
                like = f"%{q}%"; params += [like, like]

        if dept_id:
            where.append("bolum_id = %s"); params.append(dept_id)
        elif not self.pm.can_manage_all_departments():
            where.append("bolum_id = %s"); params.append(self.user["bolum_id"])

        if only_active:
            where.append("aktif = TRUE")

        sql = """
            SELECT derslik_id, derslik_kodu, derslik_adi, kapasite,
                   enine_sira_sayisi, boyuna_sira_sayisi, sira_yapisi,
                   bolum_id, aktif
            FROM Derslikler
        """
        if where: sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY derslik_kodu"

        rows = Database.execute_query(sql, tuple(params)) or []
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount(); self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(r["derslik_id"])))
            self.table.setItem(i, 1, QTableWidgetItem(r["derslik_kodu"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["derslik_adi"] or ""))
            self.table.setItem(i, 3, QTableWidgetItem(str(r["kapasite"])))
            self.table.setItem(i, 4, QTableWidgetItem(str(r["enine_sira_sayisi"])))
            self.table.setItem(i, 5, QTableWidgetItem(str(r["boyuna_sira_sayisi"])))
            self.table.setItem(i, 6, QTableWidgetItem(str(r["sira_yapisi"])))
            self.table.setItem(i, 7, QTableWidgetItem(self._dept_name(r["bolum_id"])))
            self.table.setItem(i, 8, QTableWidgetItem("Evet" if r["aktif"] else "Hayır"))

        self.current_id = None

    def _dept_name(self, dept_id):
        for d in self.departments:
            if d["id"] == dept_id: return d["ad"]
        return "-"

    def _pick_row(self, row, _col):
        def _safe_text(r, c):
            it = self.table.item(r, c)
            return it.text() if it is not None else ""

        try:
            id_item = self.table.item(row, 0)
            self.current_id = int(id_item.text()) if id_item and id_item.text().isdigit() else None
        except Exception:
            self.current_id = None

        self.inp_code.setText(_safe_text(row, 1))
        self.inp_name.setText(_safe_text(row, 2))

        cap = _safe_text(row, 3); self.inp_capacity.setValue(int(cap) if cap.isdigit() else 1)
        enine = _safe_text(row, 4); self.inp_enine.setValue(int(enine) if enine.isdigit() else 1)
        boyuna = _safe_text(row, 5); self.inp_boyuna.setValue(int(boyuna) if boyuna.isdigit() else 1)
        yapi = _safe_text(row, 6); self.inp_yapi.setValue(int(yapi) if yapi.isdigit() else 2)

        self._select_dept(self.inp_dept, self._dept_id_by_name(_safe_text(row, 7)))
        self.inp_active.setChecked(_safe_text(row, 8) == "Evet")

    def _dept_id_by_name(self, name):
        for d in self.departments:
            if d["ad"] == name: return d["id"]
        return None

    # ---------- Actions ----------
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
            QMessageBox.warning(self, "Uyarı", msg); return

        dept_id = self.inp_dept.currentData()
        if not self.pm.can_manage_all_departments():
            dept_id = self.user["bolum_id"]

        if self.current_id is None:
            # INSERT şemaya göre
            sql = """INSERT INTO Derslikler
                     (bolum_id, derslik_kodu, derslik_adi, kapasite,
                      enine_sira_sayisi, boyuna_sira_sayisi, sira_yapisi, aktif)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"""
            Database.execute_non_query(sql, (
                dept_id,
                self.inp_code.text().strip(),
                self.inp_name.text().strip(),
                int(self.inp_capacity.value()),
                int(self.inp_enine.value()),
                int(self.inp_boyuna.value()),
                int(self.inp_yapi.value()),
                self.inp_active.isChecked()
            ))
            QMessageBox.information(self, "Bilgi", "Derslik eklendi.")
        else:
            # UPDATE şemaya göre
            sql = """UPDATE Derslikler SET
                        bolum_id=%s,
                        derslik_kodu=%s,
                        derslik_adi=%s,
                        kapasite=%s,
                        enine_sira_sayisi=%s,
                        boyuna_sira_sayisi=%s,
                        sira_yapisi=%s,
                        aktif=%s
                     WHERE derslik_id=%s"""
            Database.execute_non_query(sql, (
                dept_id,
                self.inp_code.text().strip(),
                self.inp_name.text().strip(),
                int(self.inp_capacity.value()),
                int(self.inp_enine.value()),
                int(self.inp_boyuna.value()),
                int(self.inp_yapi.value()),
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
                "SELECT bolum_id FROM Derslikler WHERE derslik_id=%s", (self.current_id,)
            )
            if owner and owner[0]["bolum_id"] != self.user["bolum_id"]:
                QMessageBox.warning(self, "Yetki", "Bu dersliği silme yetkiniz yok."); return

        if QMessageBox.question(self, "Sil", "Seçili derslik silinsin mi?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return

        Database.execute_non_query("DELETE FROM Derslikler WHERE derslik_id=%s", (self.current_id,))
        QMessageBox.information(self, "Bilgi", "Derslik silindi.")
        self._clear(); self._load_table()

    def _clear(self):
        self.current_id = None
        self.inp_code.clear(); self.inp_name.clear()
        self.inp_capacity.setValue(30)
        self.inp_enine.setValue(7)
        self.inp_boyuna.setValue(9)
        self.inp_yapi.setValue(3)
        self.inp_active.setChecked(True)
        if self.pm.can_manage_all_departments():
            if self.inp_dept.count() > 0: self.inp_dept.setCurrentIndex(0)