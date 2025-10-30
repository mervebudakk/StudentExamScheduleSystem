import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QBrush
from student_system.core.database import Database
from PyQt5.QtWidgets import QSizePolicy, QCompleter

# --- İMPORTLAR ---
from student_system.utils.helpers import show_error_message, show_info_message, is_valid_email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import string
import bcrypt
import os
from PyQt5.QtGui import QIcon

# --- İMPORTLAR SONU ---


class LoginWindow(QMainWindow):
    """Modern ve temiz giriş ekranı"""

    def __init__(self):
        super().__init__()
        self.current_user = None
        self.main_dashboard = None
        self.init_ui()

    def showEvent(self, event):
        """Pencere gösterildiğinde arka planı ayarla ve pencereyi ekran boyutuna getir."""
        super().showEvent(event)

        # Ekran boyutunu al ve pencereyi o boyuta getir
        screen_geom = QApplication.primaryScreen().availableGeometry()  # taskbar'ı hesaba kat
        self.setGeometry(screen_geom)  # pencereyi ekranın kullanılabilir alanına genişlet

        # Eğer tam kaplama istersen (tam ekran, görev çubuğu hariç):
        # self.showFullScreen()

        # Arka planı güncelle
        self.set_background()

        # Hızlı debug çıktısı
        print("SHOW EVENT - window size:", self.size())

    def resizeEvent(self, event):
        """Pencere boyutu değiştiğinde arka planı yeniden ayarla"""
        super().resizeEvent(event)
        self.set_background()

    def set_background(self):
        """Arka plan resmini tam ekrana sığdır ve ortala"""
        import os
        banner_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'banner.jpg')
        banner_path = os.path.abspath(banner_path)

        if os.path.exists(banner_path):
            original_pixmap = QPixmap(banner_path)

            # Pencere boyutuna göre resmi ölçeklendir ve ORTALA
            scaled_pixmap = original_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation
            )

            # Resmi ortalamak için crop işlemi
            x_offset = (scaled_pixmap.width() - self.width()) // 2
            y_offset = (scaled_pixmap.height() - self.height()) // 2

            cropped_pixmap = scaled_pixmap.copy(
                x_offset,
                y_offset,
                self.width(),
                self.height()
            )

            palette = QPalette()
            palette.setBrush(QPalette.Window, QBrush(cropped_pixmap))
            self.setPalette(palette)

    def init_ui(self):
        """Arayüzü oluştur"""
        # Pencere ayarları
        self.setWindowTitle('Sınav Takvimi Sistemi - Giriş')

        # Pencere simgesi ekle
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'kalem.png')
        icon_path = os.path.abspath(icon_path)

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Ana widget
        central_widget = QWidget()
        central_widget.setStyleSheet("background-color: transparent;")
        self.setCentralWidget(central_widget)

        # Ana layout Yatay (QHBoxLayout) - Form ortalanacak
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Form container (ortada duracak)
        form_container = QWidget()
        form_container.setStyleSheet("background-color: transparent;")
        form_container.setFixedWidth(500)

        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)

        # Logo/İkon alanı
        logo_section = self.create_logo_section()

        # Form kartı
        form_card = self.create_form_card()

        form_layout.addStretch(1)
        form_layout.addWidget(logo_section)
        form_layout.addWidget(form_card)
        form_layout.addStretch(1)

        form_container.setLayout(form_layout)

        # Formu yatayda ortalamak için
        main_layout.addStretch(1)
        main_layout.addWidget(form_container)
        main_layout.addStretch(1)

        central_widget.setLayout(main_layout)

    def create_logo_section(self):
        """Logo/Başlık bölümü"""
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: rgba(39, 174, 96, 0.85);
                border-radius: 20px 20px 0px 0px;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(30, 30, 30, 20)

        # İkon
        icon = QLabel('🎓')
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 72px; background-color: transparent;")

        # Ana başlık
        title = QLabel('Sınav Takvimi Sistemi')
        title.setAlignment(Qt.AlignCenter)
        title.setWordWrap(True)
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 30px;
                font-weight: bold;
                background-color: transparent;
                padding: 5px;
            }
        """)

        # Üniversite adı
        university = QLabel('Kocaeli Üniversitesi')
        university.setAlignment(Qt.AlignCenter)
        university.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: 600;
                background-color: transparent;
                margin-top: 5px;
            }
        """)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(university)

        container.setLayout(layout)
        return container

    def create_form_card(self):
        """Form kartı - Beyaz arka plan"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.98);
                border-radius: 0px 0px 20px 20px;
                padding: 0px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(45, 40, 45, 40)
        layout.setSpacing(15)

        # Başlık
        form_title = QLabel('Hoş Geldiniz')
        form_title.setAlignment(Qt.AlignCenter)
        form_title.setStyleSheet("""
            QLabel {
                color: #27ae60;
                font-size: 26px;
                font-weight: bold;
                margin-bottom: 2;
                background-color: transparent;
            }
        """)

        email_container = self.create_input_field(
            'E-posta Adresi',
            'admin@kocaeli.edu.tr',
            is_password=False
        )
        self.email_input = email_container.findChild(QLineEdit)

        # 🔥 Daha akıllı otomatik tamamlama
        domain = "@kocaeli.edu.tr"
        completer = QCompleter([domain], self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        self.email_input.setCompleter(completer)
        self._domain_completer = completer

        def update_completion(text):
            if "@" not in text:
                completer.model().setStringList([text + domain])
            else:
                completer.model().setStringList([])

        self.email_input.textChanged.connect(update_completion)

        password_container = self.create_input_field(
            'Şifre',
            'Şifrenizi girin',
            is_password=True
        )
        self.password_input = password_container.findChild(QLineEdit)
        self.password_input.returnPressed.connect(self.handle_login)

        # Şifremi Unuttum Butonu
        self.forgot_password_btn = QPushButton("Şifremi Unuttum🔑")
        self.forgot_password_btn.setCursor(Qt.PointingHandCursor)
        self.forgot_password_btn.clicked.connect(self.handle_forgot_password)
        self.forgot_password_btn.setStyleSheet("""
            QPushButton {
                text-align: right;
                color: #27ae60;
                font-size: 14px;
                border: none;
                background-color: transparent;
                padding: 0px;
                margin-top: -5px; 
            }
            QPushButton:hover {
                color: #229954;
                text-decoration: underline;
            }
            QPushButton:disabled {
                color: #95a5a6;
            }
        """)

        # Butonu sağa hizalamak için bir layout
        forgot_pass_layout = QHBoxLayout()
        forgot_pass_layout.addStretch()
        forgot_pass_layout.addWidget(self.forgot_password_btn)

        # Giriş butonu
        self.login_btn = QPushButton('GİRİŞ YAP')
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)
        self.login_btn.setFixedHeight(52)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 12px;
                font-size: 17px;
                font-weight: bold;
                letter-spacing: 1.5px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)

        layout.addWidget(form_title)
        layout.addWidget(email_container)
        layout.addWidget(password_container)
        layout.addLayout(forgot_pass_layout)
        layout.addSpacing(20)
        layout.addWidget(self.login_btn)

        card.setLayout(layout)
        return card

    def create_input_field(self, label_text, placeholder, is_password=False):
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")

        container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        container.setMinimumHeight(88)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label
        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                color: #2c3e50;
                font-size: 15px;
                font-weight: 600;
                background-color: transparent;
            }
        """)

        # Input
        input_field = QLineEdit()
        input_field.setPlaceholderText(placeholder)
        input_field.setFixedHeight(54)

        if is_password:
            input_field.setEchoMode(QLineEdit.Password)

        input_field.setStyleSheet("""
            QLineEdit {
                padding: 10px 16px;
                border: 2px solid #d0d0d0;
                border-radius: 10px;
                font-size: 15px;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QLineEdit:focus {
                border: 2px solid #27ae60;
                background-color: white;
                outline: none;
            }
            QLineEdit:hover {
                border: 2px solid #95a5a6;
            }
        """)

        layout.addWidget(label)
        layout.addWidget(input_field)

        container.setLayout(layout)
        return container

    def handle_login(self):
        """Giriş işlemi"""
        email = self.email_input.text().strip()
        password = self.password_input.text()

        # Validasyon
        if not email:
            show_error_message(self, 'Hata', 'E-posta adresi boş olamaz!')
            self.email_input.setFocus()
            return

        if not password:
            show_error_message(self, 'Hata', 'Şifre boş olamaz!')
            self.password_input.setFocus()
            return

        if not is_valid_email(email):
            show_error_message(self, 'Hata', 'Geçerli bir e-posta adresi girin!')
            self.email_input.setFocus()
            return

        # Butonu devre dışı bırak
        self.login_btn.setEnabled(False)
        self.login_btn.setText('⏳ GİRİŞ YAPILIYOR...')
        QApplication.processEvents()

        try:
            user = Database.authenticate_user(email, password)

            if user:
                self.current_user = user
                self.open_main_window(user)
            else:
                show_error_message(
                    self,
                    'Giriş Başarısız!',
                    'E-posta veya şifre yanlış.\n'
                    'Lütfen bilgilerinizi kontrol edin.'
                )
                self.password_input.clear()
                self.password_input.setFocus()

        except Exception as e:
            show_error_message(self, 'Bağlantı Hatası!', f'Bağlantı Hatası!\n\n{str(e)}')

        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText('GİRİŞ YAP')

    def open_main_window(self, user):
        """Ana ekranı aç"""
        try:
            from student_system.views.main_dashboard import MainDashboard

            self.main_dashboard = MainDashboard(user)
            self.main_dashboard.showMaximized()
            self.close()

        except Exception as e:
            show_error_message(self, 'Hata', f'Dashboard açılırken hata:\n\n{str(e)}')
            print(f"Hata detayı: {e}")
            import traceback
            traceback.print_exc()

    # Şifre Sıfırlama Fonksiyonları

    def _generate_password(self):
        """8 haneli rastgele şifre oluşturur."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    def _send_password_email(self, email, password):
        """Yeni şifreyi e-posta olarak gönderir."""
        try:
            smtp_server = "smtp.gmail.com"
            port = 587
            sender_email = "bobs88806@gmail.com"
            app_password = "gbujucqoglugafal"

            msg = MIMEMultipart()
            msg["Subject"] = "Yeni Şifre Talebi - Sınav Takvim Sistemi"
            msg["From"] = sender_email
            msg["To"] = email

            body = f"""
Merhaba,

Sınav takvimi yönetim sistemi için yeni bir şifre talep ettiniz.

Yeni giriş bilgileriniz:
Email: {email}
Yeni Şifre: {password}

Lütfen giriş yaptıktan sonra bu geçici şifreyi değiştiriniz.
"""
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            print(f"Mail gönderme hatası: {e}")
            return False

    def handle_forgot_password(self):
        """'Şifremi Unuttum' butonuna tıklandığında çalışır."""

        email = self.email_input.text().strip()

        # 1. E-posta geçerli mi?
        if not is_valid_email(email):
            show_error_message(self, "Hata", "Lütfen şifresini sıfırlamak istediğiniz\n"
                                             "geçerli bir e-posta adresi girin.")
            self.email_input.setFocus()
            return

        # 2. Butonları devre dışı bırak
        self.login_btn.setEnabled(False)
        self.forgot_password_btn.setEnabled(False)
        self.forgot_password_btn.setText("Gönderiliyor...")
        QApplication.processEvents()

        try:
            # 3. Kullanıcı veritabanında var mı?
            user_exists = Database.execute_query(
                "SELECT kullanici_id FROM kullanicilar WHERE email = %s AND aktif = true", (email,)
            )

            if not user_exists:
                show_error_message(self, "Hata", "Bu e-posta adresi sistemde kayıtlı değil.")
                return

            # 4. Yeni şifre oluştur ve hash'le
            new_password = self._generate_password()
            hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # 5. Veritabanını güncelle
            Database.execute_non_query(
                "UPDATE kullanicilar SET sifre_hash = %s WHERE email = %s",
                (hashed_password, email)
            )

            # 6. E-posta gönder
            if self._send_password_email(email, new_password):
                show_info_message(self, "Başarılı",
                                  f"Yeni şifreniz {email} adresine gönderildi.\n"
                                  "Lütfen e-postanızı kontrol edin.")
            else:
                show_error_message(self, "Mail Gönderim Hatası",
                                   "Şifre sıfırlandı ancak e-posta gönderilemedi.\n"
                                   "Lütfen sistem yöneticisi ile iletişime geçin.")

        except Exception as e:
            show_error_message(self, "Veritabanı Hatası", f"Bir hata oluştu: {e}")

        finally:
            # 7. Butonları tekrar aktif et
            self.login_btn.setEnabled(True)
            self.forgot_password_btn.setEnabled(True)
            self.forgot_password_btn.setText("Şifremi Unuttum🔑")


# Standalone test
if __name__ == '__main__':
    app = QApplication(sys.argv)

    font = QFont('Segoe UI', 10)
    app.setFont(font)

    window = LoginWindow()

    # Birden fazla yöntem garanti için: önce show(), sonra full screen state ata
    window.show()
    window.setWindowState(window.windowState() | Qt.WindowFullScreen)

    # Alternatif (direkt): window.showFullScreen()

    sys.exit(app.exec_())
