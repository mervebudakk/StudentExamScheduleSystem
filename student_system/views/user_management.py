from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QDialog, QLineEdit, QComboBox, QFormLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from student_system.core.database import Database
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

        title = QLabel("👤 Kullanıcı Yönetimi")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:20px;font-weight:bold;color:#667eea;")
        main_layout.addWidget(title)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Ad Soyad", "Email", "Bölüm"])
        self.table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ Kullanıcı Ekle")
        self.btn_add.clicked.connect(self.open_add_user_dialog)

        self.btn_delete = QPushButton("🗑 Kullanıcıyı Pasif Yap")
        self.btn_delete.clicked.connect(self.deactivate_user)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        main_layout.addLayout(btn_layout)

    def load_users(self):
        rows = Database.execute_query("""
            SELECT k.kullanici_id, k.ad_soyad, k.email, b.bolum_adi, k.aktif
            FROM Kullanicilar k
            JOIN Bolumler b ON k.bolum_id = b.bolum_id
            ORDER BY k.aktif DESC, k.kullanici_id ASC
        """)

        self.table.setRowCount(len(rows or []))
        for i, r in enumerate(rows or []):
            self.table.setItem(i, 0, QTableWidgetItem(r["ad_soyad"] or ""))
            self.table.setItem(i, 1, QTableWidgetItem(r["email"]))
            self.table.setItem(i, 2, QTableWidgetItem(r["bolum_adi"]))

            if not r["aktif"]:
                for c in range(3):
                    self.table.item(i, c).setForeground(QColor("gray"))

            self.table.setRowHeight(i, 35)

    def open_add_user_dialog(self):
        dialog = AddUserDialog(self)
        dialog.exec_()
        self.load_users()

    def deactivate_user(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Uyarı", "Bir kullanıcı seçin!")
            return

        email = self.table.item(row, 1).text()

        Database.execute_non_query("""
            UPDATE Kullanicilar SET aktif = FALSE WHERE email = %s
        """, (email,))

        QMessageBox.information(self, "Tamam", "Kullanıcı pasif hale getirildi ✅")
        self.load_users()


class AddUserDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Yeni Kullanıcı Ekle")
        self.build_ui()

    def build_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.txt_name = QLineEdit()
        self.txt_email = QLineEdit()
        self.cmb_dep = QComboBox()

        deps = Database.execute_query("SELECT bolum_id, bolum_adi FROM Bolumler WHERE aktif = TRUE")
        for d in deps or []:
            self.cmb_dep.addItem(d["bolum_adi"], d["bolum_id"])

        form.addRow("Ad Soyad:", self.txt_name)
        form.addRow("Email:", self.txt_email)
        form.addRow("Bölüm:", self.cmb_dep)
        layout.addLayout(form)

        btn_save = QPushButton("✅ Kaydet ve Şifre Gönder")
        btn_save.clicked.connect(self.save_user)
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

Lütfen ilk girişten sonra şifrenizi değiştiriniz.
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
            QMessageBox.warning(self, "Hata", "Tüm alanları doldurun!")
            return

        exists = Database.execute_query(
            "SELECT * FROM Kullanicilar WHERE email = %s", (email,)
        )
        if exists:
            QMessageBox.warning(self, "Hata", "Bu email zaten kayıtlı!")
            return

        password = self.generate_password()
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        Database.execute_non_query("""
            INSERT INTO Kullanicilar (email, sifre_hash, ad_soyad, bolum_id, rol_id, aktif)
            VALUES (%s, %s, %s, %s, 2, TRUE)
        """, (email, hashed, name, bolum_id))

        email_sent = self.send_email(email, password)

        if not email_sent:
            QMessageBox.warning(self, "Mail Uyarısı", "Kullanıcı eklendi fakat mail gönderilemedi!")
        else:
            QMessageBox.information(self, "Başarılı", "Kullanıcı eklendi ✅ Şifre mail ile gönderildi!")

        self.close()
