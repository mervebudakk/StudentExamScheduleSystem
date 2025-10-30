import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QLineEdit, QComboBox, QFormLayout,
    QHeaderView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from student_system.core.database import Database
from student_system.utils.helpers import (
    show_warning_message,
    show_info_message,
    show_confirmation_dialog
)

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import bcrypt


class UserManagement(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._init_ui()
        self.load_users()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Kullanıcı Yönetimi")
        title.setAlignment(Qt.AlignLeft)
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(title)

        filter_container = QWidget()
        filter_container.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setSpacing(15)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Kullanıcı ara...")
        self.search_box.textChanged.connect(self.apply_filters)
        self.search_box.setStyleSheet("""
            QLineEdit {
                padding: 10px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
        """)
        filter_layout.addWidget(self.search_box, 2)

        self.cmb_filter = QComboBox()
        self.cmb_filter.addItem("Tüm Bölümler", None)
        deps = Database.execute_query(
            "SELECT bolum_id, bolum_adi FROM Bolumler WHERE aktif = TRUE ORDER BY bolum_adi"
        )
        for d in deps or []:
            self.cmb_filter.addItem(d["bolum_adi"], d["bolum_id"])
        self.cmb_filter.currentIndexChanged.connect(self.apply_filters)
        self.cmb_filter.setStyleSheet("""
            QComboBox {
                padding: 10px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background-color: white;
                min-width: 200px;
            }
            QComboBox:focus {
                border: 2px solid #667eea;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
        """)
        filter_layout.addWidget(self.cmb_filter, 1)

        main_layout.addWidget(filter_container)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Ad Soyad", "Email", "Bölüm"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #667eea;
                color: white;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #e0e0e0;
                font-weight: 600;
                color: #2c3e50;
                font-size: 13px;
            }
            QTableWidget::item:alternate {
                background-color: #fafbfc;
            }
        """)
        main_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_add = QPushButton("+ Yeni Kullanıcı")
        self.btn_add.clicked.connect(self.show_add_user_dialog)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5568d3;
            }
            QPushButton:pressed {
                background-color: #4c5cba;
            }
        """)

        self.btn_passive = QPushButton("Pasif Yap")
        self.btn_passive.clicked.connect(self.deactivate_user)
        self.btn_passive.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #d97706;
            }
            QPushButton:pressed {
                background-color: #b45309;
            }
        """)

        self.btn_delete = QPushButton("Sil")
        self.btn_delete.clicked.connect(self.delete_user)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_passive)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

    def load_users(self):
        self.all_users = Database.execute_query("""
            SELECT k.kullanici_id, k.ad_soyad, k.email, b.bolum_adi, k.aktif,
                   k.bolum_id
            FROM Kullanicilar k
            JOIN Bolumler b ON k.bolum_id = b.bolum_id
            ORDER BY k.aktif DESC, k.ad_soyad ASC
        """)
        self.apply_filters()

    def apply_filters(self):
        search_text = self.search_box.text().lower()
        filter_bolum = self.cmb_filter.currentData()

        filtered = []
        for r in self.all_users or []:
            if (filter_bolum is None or r["bolum_id"] == filter_bolum) and \
               (search_text in r["ad_soyad"].lower() or search_text in r["email"].lower()):
                filtered.append(r)

        self.display_users(filtered)

    def display_users(self, users):
        self.table.setRowCount(len(users))

        for i, r in enumerate(users):
            self.table.setItem(i, 0, QTableWidgetItem(r["ad_soyad"]))
            self.table.setItem(i, 1, QTableWidgetItem(r["email"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["bolum_adi"]))

            if not r["aktif"]:
                for c in range(3):
                    item = self.table.item(i, c)
                    item.setForeground(QColor("#9ca3af"))
                    font = item.font()
                    font.setItalic(True)
                    item.setFont(font)

            self.table.setRowHeight(i, 50)

    def get_selected_email(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self.table.item(row, 1).text()

    def show_add_user_dialog(self):
        dialog = AddUserDialog(self)
        dialog.exec_()
        self.load_users()

    def deactivate_user(self):
        email = self.get_selected_email()
        if not email:
            show_warning_message(self, "Uyarı", "Lütfen bir kullanıcı seçin!")
            return

        Database.execute_non_query("UPDATE Kullanicilar SET aktif = FALSE WHERE email = %s", (email,))
        show_info_message(self, "Başarılı", "Kullanıcı pasif hale getirildi.")
        self.load_users()

    def delete_user(self):
        email = self.get_selected_email()
        if not email:
            show_warning_message(self, "Uyarı", "Lütfen silmek için bir kullanıcı seçin!")
            return

        if show_confirmation_dialog(self, "Silme Onayı", f"{email} kullanıcısı tamamen silinsin mi?"):
            Database.execute_non_query("DELETE FROM Kullanicilar WHERE email = %s", (email,))
            show_info_message(self, "Başarılı", "Kullanıcı silindi 🗑")
            self.load_users()


class AddUserDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Yeni Kullanıcı Ekle")
        self.setMinimumWidth(450)
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Yeni Kullanıcı Oluştur")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 10px;
        """)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(15)
        form.setLabelAlignment(Qt.AlignRight)

        self.txt_name = QLineEdit()
        self.txt_name.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
        """)

        self.txt_email = QLineEdit()
        self.txt_email.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
            }
        """)

        self.cmb_dep = QComboBox()
        deps = Database.execute_query("SELECT bolum_id, bolum_adi FROM Bolumler WHERE aktif = TRUE ORDER BY bolum_adi")
        for d in deps or []:
            self.cmb_dep.addItem(d["bolum_adi"], d["bolum_id"])
        self.cmb_dep.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
                font-size: 14px;
            }
            QComboBox:focus {
                border: 2px solid #667eea;
            }
        """)

        form.addRow("Ad Soyad:", self.txt_name)
        form.addRow("Email:", self.txt_email)
        form.addRow("Bölüm:", self.cmb_dep)
        layout.addLayout(form)

        btn_save = QPushButton("Kaydet ve Şifre Gönder")
        btn_save.clicked.connect(self.save_user)
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #667eea;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #5568d3;
            }
            QPushButton:pressed {
                background-color: #4c5cba;
            }
        """)
        layout.addWidget(btn_save)

    def generate_password(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    def send_email(self, email, password):
        try:
            smtp_server = "smtp.gmail.com"
            port = 587
            sender_email = "merome813@gmail.com"
            app_password = "jzew liml hpqe xaiy"

            msg = MIMEMultipart()
            msg["Subject"] = "Hesabınız Oluşturuldu - Sınav Sistemi"
            msg["From"] = sender_email
            msg["To"] = email

            body = f"""
Merhaba,

Sınav yönetim sistemine hesabınız oluşturulmuştur.

Giriş bilgileriniz:
Email: {email}
Şifre: {password}

Lütfen ilk girişte şifrenizi değiştiriniz.
"""
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, email, msg.as_string())
            server.quit()

            return True
        except Exception as e:
            print("Mail gönderme hatası:", e)
            return False

    def save_user(self):
        name = self.txt_name.text().strip()
        email = self.txt_email.text().strip()
        bolum_id = self.cmb_dep.currentData()

        if not name or not email:
            show_warning_message(self, "Hata", "Tüm alanları doldurun!")
            return

        exists = Database.execute_query("SELECT 1 FROM Kullanicilar WHERE email = %s", (email,))
        if exists:
            show_warning_message(self, "Hata", "Bu email zaten kayıtlı!")
            return

        password = self.generate_password()
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        Database.execute_non_query("""
            INSERT INTO Kullanicilar (email, sifre_hash, ad_soyad, bolum_id, rol_id, aktif)
            VALUES (%s, %s, %s, %s, 2, TRUE)
        """, (email, hashed, name, bolum_id))

        if self.send_email(email, password):
            show_info_message(self, "Başarılı", "Kullanıcı eklendi ve şifre email ile gönderildi.")
        else:
            show_warning_message(self, "Uyarı", "Kullanıcı eklendi fakat mail gönderilemedi!")

        self.close()