import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor
from student_system.core.database import Database
from PyQt5.QtWidgets import QSizePolicy


class LoginWindow(QMainWindow):
    """Modern ve temiz giriş ekranı"""

    def __init__(self):
        super().__init__()
        self.current_user = None
        self.main_dashboard = None
        self.init_ui()

    def init_ui(self):
        """Arayüzü oluştur"""
        # Pencere ayarları
        self.setWindowTitle('Sınav Takvimi Sistemi - Giriş')
        self.setFixedSize(550, 700)

        # Arka plan resmi ile gradient overlay
        import os
        banner_path = os.path.join(os.path.dirname(__file__), '..', '..', 'bannerkoumobil.png')
        banner_path = os.path.abspath(banner_path).replace('\\', '/')

        self.setStyleSheet(f"""
            QMainWindow {{
                background-image: url({banner_path});
                background-position: center;
                background-repeat: no-repeat;
            }}
            QMainWindow::before {{
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(39, 174, 96, 0.75);
            }}
        """)

        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Ana layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(50, 50, 50, 50)
        main_layout.setSpacing(30)

        # Yeşil overlay frame (saydam arka plan için)
        overlay = QFrame()
        overlay.setStyleSheet("""
            QFrame {
                background-color: rgba(39, 174, 96, 0.65);
                border-radius: 15px;
            }
        """)

        overlay_layout = QVBoxLayout()
        overlay_layout.setContentsMargins(0, 0, 0, 0)

        # Logo/İkon alanı
        logo_section = self.create_logo_section()

        # Form kartı
        form_card = self.create_form_card()


        # Overlay layout'a ekle
        overlay_layout.addStretch(1)
        overlay_layout.addWidget(logo_section)
        overlay_layout.addWidget(form_card)
        overlay_layout.addStretch(1)

        overlay.setLayout(overlay_layout)

        # Ana layout'a overlay ekle
        main_layout.addWidget(overlay)

        central_widget.setLayout(main_layout)

    def create_logo_section(self):
        """Logo/Başlık bölümü"""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
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
                border-radius: 20px;
                padding: 0px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(45, 40, 45, 40)
        layout.setSpacing(22)

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

        # Email alanı
        email_container = self.create_input_field(
            '📧  E-posta Adresi',
            'admin@kocaeli.edu.tr',
            is_password=False
        )
        self.email_input = email_container.findChild(QLineEdit)

        # Şifre alanı
        password_container = self.create_input_field(
            '🔒  Şifre',
            'Şifrenizi girin',
            is_password=True
        )
        self.password_input = password_container.findChild(QLineEdit)
        self.password_input.returnPressed.connect(self.handle_login)

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
        layout.addSpacing(10)
        layout.addWidget(password_container)
        layout.addSpacing(10)
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
            self.show_error('E-posta adresi boş olamaz!')
            self.email_input.setFocus()
            return

        if not password:
            self.show_error('Şifre boş olamaz!')
            self.password_input.setFocus()
            return

        if '@' not in email:
            self.show_error('Geçerli bir e-posta adresi girin!')
            self.email_input.setFocus()
            return

        # Butonu devre dışı bırak
        self.login_btn.setEnabled(False)
        self.login_btn.setText('⏳ GİRİŞ YAPILIYOR...')
        QApplication.processEvents()  # UI güncelle

        try:
            user = Database.authenticate_user(email, password)

            if user:
                self.current_user = user
                self.open_main_window(user)
            else:
                self.show_error(
                    'Giriş Başarısız!\n\n'
                    'E-posta veya şifre yanlış.\n'
                    'Lütfen bilgilerinizi kontrol edin.'
                )
                self.password_input.clear()
                self.password_input.setFocus()

        except Exception as e:
            self.show_error(f'Bağlantı Hatası!\n\n{str(e)}')

        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText('GİRİŞ YAP')

    def open_main_window(self, user):
        """Ana ekranı aç"""
        try:
            from student_system.views.main_dashboard import MainDashboard

            self.main_dashboard = MainDashboard(user)
            self.main_dashboard.show()
            self.close()

        except Exception as e:
            self.show_error(f'Dashboard açılırken hata:\n\n{str(e)}')
            print(f"Hata detayı: {e}")
            import traceback
            traceback.print_exc()

    def show_error(self, message):
        """Hata mesajı - Modern tasarım"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle('❌ Hata')
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)

        # Modern stil
        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #2c3e50;
                font-size: 13px;
                min-width: 300px;
            }
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        msg.exec_()

    def show_success(self, message):
        """Başarı mesajı"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle('✅ Başarılı')
        msg.setText(message)
        msg.setStandardButtons(QMessageBox.Ok)

        msg.setStyleSheet("""
            QMessageBox {
                background-color: white;
            }
            QMessageBox QLabel {
                color: #2c3e50;
                font-size: 13px;
                min-width: 300px;
            }
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)

        msg.exec_()


# Standalone test
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Modern font
    font = QFont('Segoe UI', 10)
    app.setFont(font)

    window = LoginWindow()
    window.show()

    sys.exit(app.exec_())