import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QFrame, QGridLayout, QScrollArea, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from student_system.core.database import Database
import traceback
from student_system.core.permissions import PermissionManager
from student_system.utils.helpers import show_error_message, show_warning_message, show_confirmation_dialog
from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit
from student_system.utils.helpers import show_error_message, show_info_message
import bcrypt
import os
from PyQt5.QtGui import QIcon

class ProfileSettingsDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        self.user_id = user_id

        self.setWindowTitle("Profil ve Şifre Güncelleme")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #f5f7fa; }
            QLabel { font-size: 14px; }
            QLineEdit { 
                padding: 10px; border: 1px solid #ddd; border-radius: 5px; 
                font-size: 14px; 
            }
            QPushButton {
                background-color: #27ae60; color: white; padding: 12px;
                border-radius: 5px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel("Şifre Değiştir")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        form_layout = QFormLayout()

        self.current_pass_input = QLineEdit()
        self.current_pass_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Mevcut Şifre:", self.current_pass_input)

        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Yeni Şifre:", self.new_pass_input)

        self.confirm_pass_input = QLineEdit()
        self.confirm_pass_input.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Yeni Şifre (Tekrar):", self.confirm_pass_input)

        layout.addLayout(form_layout)

        self.save_button = QPushButton("Kaydet")
        self.save_button.clicked.connect(self.save_password)
        layout.addWidget(self.save_button)

    def save_password(self):
        current_pass = self.current_pass_input.text()
        new_pass = self.new_pass_input.text()
        confirm_pass = self.confirm_pass_input.text()

        # 1. Doğrulamalar
        if not current_pass or not new_pass or not confirm_pass:
            show_error_message(self, "Hata", "Tüm alanlar doldurulmalıdır.")
            return

        if new_pass != confirm_pass:
            show_error_message(self, "Hata", "Yeni şifreler uyuşmuyor.")
            return

        if len(new_pass) < 6:
            show_error_message(self, "Hata", "Yeni şifre en az 6 karakter olmalıdır.")
            return

        try:
            # 2. Mevcut şifreyi kontrol et
            db_result = Database.execute_query(
                "SELECT sifre_hash FROM kullanicilar WHERE kullanici_id = %s",
                (self.user_id,)
            )

            if not db_result:
                show_error_message(self, "Hata", "Kullanıcı bulunamadı.")
                return

            current_hash = db_result[0]['sifre_hash']

            if not bcrypt.checkpw(current_pass.encode('utf-8'), current_hash.encode('utf-8')):
                show_error_message(self, "Hata", "Mevcut şifreniz yanlış.")
                return

            # 3. Yeni şifreyi hash'le ve güncelle
            new_hash = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            Database.execute_non_query(
                "UPDATE kullanicilar SET sifre_hash = %s WHERE kullanici_id = %s",
                (new_hash, self.user_id)
            )

            show_info_message(self, "Başarılı", "Şifreniz başarıyla güncellendi.")
            self.accept()  # Diyaloğu kapat

        except Exception as e:
            show_error_message(self, "Veritabanı Hatası", f"Bir hata oluştu: {e}")

class MainDashboard(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.permission_manager = PermissionManager(user['id'])
        self.content_layout = None
        self.active_menu_button = None
        self.menu_buttons = {}

        self.admin_selected_department = {
            'bolum_id': None,
            'bolum_adi': None
        }

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Sınav Takvimi Sistemi - {self.user['ad_soyad']}")
        self.setMinimumSize(1400, 900)

        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'kalem.png')
        icon_path = os.path.abspath(icon_path)

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = self.create_sidebar()
        content_area = self.create_content_area()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area, stretch=1)

        central_widget.setLayout(main_layout)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }
        """)

        ### YENİ EKLENTİ: Arayüzü ilk açılışta yetkilendir ###
        self.update_ui_authorization()
        ### YENİ EKLENTİ SONU ###

    def create_content_area(self):
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background-color: #f5f7fa;")

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        self.show_dashboard_content()

        self.content_frame.setLayout(self.content_layout)
        return self.content_frame

    def clear_content_area(self):
        if not self.content_layout:
            return
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def show_dashboard_content(self):
        self.clear_content_area()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: #f5f7fa; }")

        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(25)

        top_bar = self.create_modern_top_bar()
        stats = self.create_modern_statistics()
        container_layout.addWidget(top_bar)
        container_layout.addWidget(stats)
        dashboarduni = self.create_dashboarduni()
        container_layout.addWidget(dashboarduni)
        container_layout.addStretch()

        container.setLayout(container_layout)
        scroll.setWidget(container)

        self.content_layout.addWidget(scroll)

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #27ae60;
                border: none;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        user_info = self.create_user_info_section()
        layout.addWidget(user_info)

        if self.user['rol'] == 'Admin':
            admin_dept_frame = self.create_admin_dept_selector()
            layout.addWidget(admin_dept_frame)

        menu_title = QLabel('MENÜ')
        menu_title.setStyleSheet("""
                QLabel {
                    color: rgba(255, 255, 255, 0.9);
                    padding: 25px 25px 10px 25px;
                    font-size: 13px;
                    font-weight: 700;
                    letter-spacing: 1px;
                }
            """)
        layout.addWidget(menu_title)

        for item in self.get_menu_items():
            btn = self.create_menu_button(item['text'], item['icon'], item['callback'])
            self.menu_buttons[item['text']] = btn
            layout.addWidget(btn)

        ### YENİ EKLENTİ: PROFİL BUTONU ###
        self.profile_btn = self.create_menu_button('Profili Güncelle', '⚙️', self.open_profile_settings)
        layout.addWidget(self.profile_btn)
        ### YENİ EKLENTİ SONU ###

        logout_btn = self.create_menu_button('Çıkış', '🚪', self.logout)
        logout_btn.setStyleSheet(logout_btn.styleSheet() + """
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 0.9) !important;
            }
        """)
        layout.addWidget(logout_btn)
        layout.addStretch()
        sidebar.setLayout(layout)
        return sidebar

    def create_admin_dept_selector(self):
        """Admin için bölüm seçici QComboBox'u oluşturan frame'i döndürür."""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                padding: 10px 20px 20px 20px; /* Üst, Sağ, Alt, Sol */
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(8)

        label = QLabel('YÖNETİLEN BÖLÜM')
        label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 1px;
            }
        """)

        self.admin_dept_combo = QComboBox()
        self.admin_dept_combo.setStyleSheet("""
            QComboBox {
                background-color: white;
                color: #2c3e50;
                padding: 8px 10px;
                border-radius: 5px;
                font-size: 13px;
            }
        """)

        # ComboBox'u doldur
        self.populate_admin_combo()

        # Sinyali bağla
        self.admin_dept_combo.currentIndexChanged.connect(self.on_admin_dept_change)

        layout.addWidget(label)
        layout.addWidget(self.admin_dept_combo)
        frame.setLayout(layout)
        return frame

    def populate_admin_combo(self):
        """Admin QComboBox'unu veritabanındaki bölümlerle doldurur."""
        try:
            # 'Bölüm Seç' seçeneğini başta ekle
            self.admin_dept_combo.addItem("Bölüm Seçilmedi", None)

            r = Database.execute_query("SELECT bolum_id, bolum_adi FROM bolumler WHERE aktif = true ORDER BY bolum_adi")
            if r:
                for bolum in r:
                    self.admin_dept_combo.addItem(bolum['bolum_adi'], bolum['bolum_id'])

            # Başlangıçta ilk seçimi yap (Bölüm Seçilmedi)
            self.on_admin_dept_change(0)  # 0. indeksi tetikle

        except Exception as e:
            show_error_message(self, "Hata", f"Admin bölüm listesi yüklenemedi: {e}")

    def on_admin_dept_change(self, index):
        """Admin bölüm seçimini değiştirdiğinde state'i günceller."""
        self.admin_selected_department['bolum_id'] = self.admin_dept_combo.itemData(index)
        self.admin_selected_department['bolum_adi'] = self.admin_dept_combo.itemText(index)

        # Eğer "Bölüm Seçilmedi" (ID=None) seçilirse, adı da None yap
        if self.admin_selected_department['bolum_id'] is None:
            self.admin_selected_department['bolum_adi'] = None

        # ÖNEMLİ: Bölüm değiştiğinde ana sayfa istatistiklerini ve
        # iş akışı butonlarını (update_ui_authorization) güncelle
        self.update_ui_authorization()
        if self.active_menu_button and self.active_menu_button.text().strip() == '🏠 Ana Sayfa':
            self.show_dashboard_content()

    def get_scoped_user(self):
        """
        Mevcut 'self.user'ın bir kopyasını alır.
        Eğer kullanıcı Admin ise, kopyanın 'bolum_id' ve 'bolum_adi' alanlarını
        ComboBox'ta seçili olanla değiştirir.
        """

        # Orijinal user'ın bir kopyasını al (bu çok önemli)
        scoped_user = self.user.copy()

        if self.user['rol'] == 'Admin':
            # Kopyalanan user'ın bolum_id ve bolum_adi'sini ez.
            scoped_user['bolum_id'] = self.admin_selected_department['bolum_id']
            scoped_user['bolum_adi'] = self.admin_selected_department['bolum_adi']

        return scoped_user

    def get_menu_items(self):
        pm = self.permission_manager
        items = [{'text': 'Ana Sayfa', 'icon': '🏠', 'callback': self.show_dashboard}]

        if pm.has_permission('KULLANICI_EKLE'):
            items.append({'text': 'Kullanıcı Yönetimi', 'icon': '👥', 'callback': self.open_user_management})
        if pm.has_permission('DERSLIK_YONET'):
            items.append({'text': 'Derslik Yönetimi', 'icon': '🏫', 'callback': self.open_classroom_management})
        if pm.has_permission('DERS_YUKLE'):
            items.append({'text': 'Ders Listesi İşlemleri', 'icon': '📚', 'callback': self.open_course_upload})
        if pm.has_permission('OGRENCI_YUKLE'):
            items.append({'text': 'Öğrenci Listesi İşlemleri', 'icon': '👨‍🎓', 'callback': self.open_student_upload})
        if pm.has_permission('SINAV_OLUSTUR'):
            items.append({'text': 'Sınav Programı', 'icon': '📅', 'callback': self.open_exam_scheduler})
        if pm.has_permission('OTURMA_PLAN'):
            items.append({'text': 'Oturma Planı', 'icon': '💺', 'callback': self.open_seating_plan})
        return items

    def create_user_info_section(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.15);
                padding: 15px 15px;
                margin: 15px 15px;
                border-radius: 15px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        avatar = QLabel('👤')
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("font-size: 40px;")

        name = QLabel(self.user['ad_soyad'])
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("""
            color: white;
            font-size: 15px;
            font-weight: 600;
        """)
        name.setWordWrap(True)

        role = QLabel(self.user['rol'])
        role.setAlignment(Qt.AlignCenter)
        role.setStyleSheet("""
            color: rgba(255, 255, 255, 0.8);
            font-size: 12px;
        """)

        layout.addWidget(avatar)
        layout.addWidget(name)
        layout.addWidget(role)

        if self.user['bolum_adi']:
            dept = QLabel(self.user['bolum_adi'])
            dept.setAlignment(Qt.AlignCenter)
            dept.setStyleSheet("""
                color: rgba(255, 255, 255, 0.7);
                font-size: 11px;
            """)
            layout.addWidget(dept)

        frame.setLayout(layout)
        return frame

    def create_menu_button(self, text, icon, callback):
        btn = QPushButton(f"{icon}  {text}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.handle_menu_click(btn, callback))
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 16px 25px;
                border: none;
                color: rgba(255, 255, 255, 0.95);
                font-size: 15px;
                background-color: transparent;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-left: 3px solid white;
            }
            QPushButton:disabled {
                color: rgba(255, 255, 255, 0.4);
            }
            QPushButton:disabled:hover {
                background-color: transparent;
                border-left: 3px solid transparent;
            }
        """)
        return btn

    def handle_menu_click(self, button, callback):
        if self.active_menu_button:
            self.active_menu_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 16px 25px;
                    border: none;
                    color: rgba(255, 255, 255, 0.95);
                    font-size: 15px;
                    background-color: transparent;
                    border-left: 3px solid transparent;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-left: 3px solid white;
                }
                QPushButton:disabled {
                    color: rgba(255, 255, 255, 0.4);
                }
                QPushButton:disabled:hover {
                    background-color: transparent;
                    border-left: 3px solid transparent;
                }
            """)

        button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 16px 25px;
                border: none;
                color: white;
                font-size: 15px;
                background-color: rgba(255, 255, 255, 0.15);
                border-left: 3px solid white;
                font-weight: 600;
            }
            QPushButton:disabled {
                color: rgba(255, 255, 255, 0.4);
                background-color: rgba(255, 255, 255, 0.15);
                border-left: 3px solid white;
            }
        """)

        self.active_menu_button = button
        callback()

    def create_modern_top_bar(self):
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 15px;
                padding: 25px 30px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        title_row = QHBoxLayout()

        welcome = QLabel(f'{self.user["ad_soyad"]}')
        welcome.setStyleSheet("""
            color: #2c3e50;
            font-size: 28px;
            font-weight: 700;
        """)
        welcome.setWordWrap(True)

        role_badge = QLabel(f'{self.user["rol"]}')
        role_badge.setStyleSheet("""
            color: white;
            background-color: #27ae60;
            padding: 8px 18px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        """)

        title_row.addWidget(welcome, stretch=1)
        title_row.addWidget(role_badge)

        subtitle = QLabel('Sınav Takvimi Yönetim Sistemi')
        subtitle.setStyleSheet("""
            color: #7f8c8d;
            font-size: 14px;
        """)
        subtitle.setWordWrap(True)

        layout.addLayout(title_row)
        layout.addWidget(subtitle)

        bar.setLayout(layout)
        return bar

    def create_modern_statistics(self):
        container = QWidget()
        layout = QGridLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)

        pm = self.permission_manager
        if pm.can_manage_all_departments():
            stats = [
                ('Toplam Bölüm', self.get_department_count(), '#27ae60', '🏛️'),
                ('Toplam Derslik', self.get_classroom_count(), '#3498db', '🏫'),
                ('Toplam Ders', self.get_course_count(), '#e74c3c', '📚'),
                ('Toplam Öğrenci', self.get_student_count(), '#f39c12', '👨‍🎓'),
            ]
        else:
            stats = [
                ('Dersliklerim', self.get_classroom_count(self.user['bolum_id']), '#27ae60', '🏫'),
                ('Derslerim', self.get_course_count(self.user['bolum_id']), '#3498db', '📚'),
                ('Öğrencilerim', self.get_student_count(self.user['bolum_id']), '#e74c3c', '👨‍🎓'),
                ('Sınavlarım', self.get_exam_count(self.user['bolum_id']), '#f39c12', '📅'),
            ]

        for i, (title, value, color, icon) in enumerate(stats):
            card = self.create_modern_stat_card(title, value, color, icon)
            layout.addWidget(card, i // 2, i % 2)

        container.setLayout(layout)
        return container

    def create_dashboarduni(self):
        """Üniversite görselini transparan olarak gösterir"""
        import os

        frame = QFrame()
        frame.setStyleSheet("background-color: transparent; border: none;")

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 20, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # Görseli yükle
        image_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'dashboarduni.png')
        image_path = os.path.abspath(image_path)

        if os.path.exists(image_path):
            from PyQt5.QtGui import QPixmap

            image_label = QLabel()
            pixmap = QPixmap(image_path)

            # Görseli boyutlandır (genişlik max 800px, yükseklik orantılı)
            scaled_pixmap = pixmap.scaledToWidth(800, Qt.SmoothTransformation)

            image_label.setPixmap(scaled_pixmap)
            image_label.setAlignment(Qt.AlignCenter)

            # Transparan efekt için opacity ayarla
            image_label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)

            # Opacity efekti için QGraphicsOpacityEffect kullan
            from PyQt5.QtWidgets import QGraphicsOpacityEffect
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(0.3)  # 0.0 (görünmez) ile 1.0 (tam görünür) arası
            image_label.setGraphicsEffect(opacity_effect)

            layout.addWidget(image_label)
        else:
            # Görsel bulunamazsa boş bir alan bırak
            placeholder = QLabel()
            placeholder.setFixedHeight(200)
            layout.addWidget(placeholder)

        frame.setLayout(layout)
        return frame

    def create_modern_stat_card(self, title, value, color, icon):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 15px;
                border: none;
            }}
            QFrame:hover {{
                background-color: #fafbfc;
            }}
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(15)

        top_row = QHBoxLayout()

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            font-size: 32px;
            background-color: {color};
            padding: 10px;
            border-radius: 12px;
        """)
        icon_label.setFixedSize(55, 55)
        icon_label.setAlignment(Qt.AlignCenter)

        top_row.addWidget(icon_label)
        top_row.addStretch()

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            color: #7f8c8d;
            font-size: 13px;
            font-weight: 500;
        """)

        value_label = QLabel(str(value))
        value_label.setStyleSheet(f"""
            color: {color};
            font-size: 36px;
            font-weight: 700;
        """)

        layout.addLayout(top_row)
        layout.addWidget(title_label)
        layout.addWidget(value_label)

        card.setLayout(layout)
        return card

    def get_department_count(self):
        r = Database.execute_query("SELECT COUNT(*) as count FROM bolumler WHERE aktif = true")
        return r[0]['count'] if r else 0

    def get_classroom_count(self, bolum_id=None):
        if bolum_id:
            r = Database.execute_query(
                "SELECT COUNT(*) as count FROM derslikler WHERE bolum_id=%s AND aktif=true", (bolum_id,)
            )
        else:
            r = Database.execute_query("SELECT COUNT(*) as count FROM derslikler WHERE aktif=true")
        return r[0]['count'] if r else 0

    def get_course_count(self, bolum_id=None):
        if bolum_id:
            r = Database.execute_query(
                "SELECT COUNT(*) as count FROM dersler WHERE bolum_id=%s AND aktif=true", (bolum_id,)
            )
        else:
            r = Database.execute_query("SELECT COUNT(*) as count FROM dersler WHERE aktif=true")
        return r[0]['count'] if r else 0

    def get_student_count(self, bolum_id=None):
        if bolum_id:
            r = Database.execute_query(
                "SELECT COUNT(*) as count FROM ogrenciler WHERE bolum_id=%s AND aktif=true", (bolum_id,)
            )
        else:
            r = Database.execute_query("SELECT COUNT(*) as count FROM ogrenciler WHERE aktif=true")
        return r[0]['count'] if r else 0

    def get_exam_count(self, bolum_id=None):
        if bolum_id:
            r = Database.execute_query("SELECT COUNT(*) as count FROM sinavlar WHERE bolum_id=%s", (bolum_id,))
        else:
            r = Database.execute_query("SELECT COUNT(*) as count FROM sinavlar")
        return r[0]['count'] if r else 0

    ### YENİ EKLENTİ: İş Akışı Buton Kontrolü ###
    def update_ui_authorization(self):
        """
        Proje dokümanındaki iş akışına göre butonları etkinleştirir/devre dışı bırakır.
        Admin rolü bu kısıtlamalardan muaftır.
        """
        try:
            # Admin rolü (rol_adi == 'Admin') veya bölümü olmayan
            # (bolum_id is None) kullanıcılar kısıtlanmaz.
            if self.user['rol'] == 'Admin' or self.user['bolum_id'] is None:
                return

            bolum_id = self.user['bolum_id']

            # 1. Derslik Kontrolü
            # (Dokümana göre derslik yoksa sadece derslik yönetimi aktif olmalı)
            derslik_var = Database.check_classrooms_exist(bolum_id)

            if self.menu_buttons.get('Derslik Yönetimi'):
                self.menu_buttons['Derslik Yönetimi'].setEnabled(True)

            if self.menu_buttons.get('Ders Listesi İşlemleri'):
                self.menu_buttons['Ders Listesi İşlemleri'].setEnabled(derslik_var)

            if self.menu_buttons.get('Öğrenci Listesi İşlemleri'):
                self.menu_buttons['Öğrenci Listesi İşlemleri'].setEnabled(derslik_var)

            if self.menu_buttons.get('Sınav Programı'):
                self.menu_buttons['Sınav Programı'].setEnabled(derslik_var)

            if self.menu_buttons.get('Oturma Planı'):
                self.menu_buttons['Oturma Planı'].setEnabled(derslik_var)

            if not derslik_var:
                return  # Derslik yoksa daha fazla kontrol yapma

            # 2. Excel Yükleme Kontrolü
            # (Sınav programı için hem ders hem öğrenci listesi yüklenmiş olmalı)
            ders_var = Database.check_courses_exist(bolum_id)
            ogrenci_var = Database.check_students_exist(bolum_id)
            exceller_yuklenmis = ders_var and ogrenci_var

            if self.menu_buttons.get('Sınav Programı'):
                self.menu_buttons['Sınav Programı'].setEnabled(exceller_yuklenmis)

            if self.menu_buttons.get('Oturma Planı'):
                self.menu_buttons['Oturma Planı'].setEnabled(exceller_yuklenmis)

            if not exceller_yuklenmis:
                return  # Excel'ler yüklenmemişse daha fazla kontrol yapma

            # 3. Sınav Programı Kontrolü
            # (Oturma planı için sınav programı oluşturulmuş olmalı)
            program_var = Database.check_schedule_exists(bolum_id)

            if self.menu_buttons.get('Oturma Planı'):
                self.menu_buttons['Oturma Planı'].setEnabled(program_var)

        except Exception as e:
            print(f"HATA (update_ui_authorization): {e}")
            # Bir hata olursa güvenli modda çoğu şeyi devre dışı bırak
            if self.menu_buttons.get('Ders Listesi İşlemleri'):
                self.menu_buttons['Ders Listesi İşlemleri'].setEnabled(False)
            if self.menu_buttons.get('Sınav Programı'):
                self.menu_buttons['Sınav Programı'].setEnabled(False)
            if self.menu_buttons.get('Oturma Planı'):
                self.menu_buttons['Oturma Planı'].setEnabled(False)

    ### YENİ EKLENTİ SONU ###

    def show_dashboard(self):
        ### YENİ EKLENTİ: Ana sayfaya her tıklandığında buton durumunu güncelle ###
        self.update_ui_authorization()
        ### YENİ EKLENTİ SONU ###
        self.show_dashboard_content()

    def open_user_management(self):
        if not self.permission_manager.has_permission('KULLANICI_EKLE'):
            self.show_permission_error()
            return
        from student_system.views.user_management import UserManagement
        self.clear_content_area()
        self.cm_widget = UserManagement(self.user)
        self.content_layout.addWidget(self.cm_widget)

    def open_classroom_management(self):
        if not self.permission_manager.has_permission('DERSLIK_YONET'):
            self.show_permission_error()
            return

        scoped_user = self.get_scoped_user()

        if scoped_user['rol'] == 'Admin' and scoped_user['bolum_id'] is None:
            show_warning_message(self, "Bölüm Seçilmedi",
                                 "Lütfen dersliklerini yönetmek için bir bölüm seçin.")
            return

        from student_system.views.classroom_management import ClassroomManagement
        self.clear_content_area()
        self.cm_widget = ClassroomManagement(scoped_user, self.permission_manager, parent=self)
        self.content_layout.addWidget(self.cm_widget)

    def open_course_upload(self):
        if not self.permission_manager.has_permission('DERS_YUKLE'):
            self.show_permission_error()
            return

        scoped_user = self.get_scoped_user()

        if scoped_user['rol'] == 'Admin' and scoped_user['bolum_id'] is None:
            show_warning_message(self, "Bölüm Seçilmedi",
                                 "Lütfen dersliklerini yönetmek için bir bölüm seçin.")
            return

        from student_system.views.lesson_list import LessonListUploader
        self.clear_content_area()
        uploader = LessonListUploader(scoped_user, self)
        self.content_layout.addWidget(uploader)

    def open_student_upload(self):
        if not self.permission_manager.has_permission('OGRENCI_YUKLE'):
            self.show_permission_error()
            return

        scoped_user = self.get_scoped_user()

        if scoped_user['rol'] == 'Admin' and scoped_user['bolum_id'] is None:
            show_warning_message(self, "Bölüm Seçilmedi",
                                 "Lütfen dersliklerini yönetmek için bir bölüm seçin.")
            return

        from student_system.views.student_list import StudentListUploader
        self.clear_content_area()
        uploader = StudentListUploader(scoped_user, self)
        self.content_layout.addWidget(uploader)

    def open_exam_scheduler(self):
        if not self.permission_manager.has_permission('SINAV_OLUSTUR'):
            self.show_permission_error()
            return

        scoped_user = self.get_scoped_user()

        if scoped_user['rol'] == 'Admin' and scoped_user['bolum_id'] is None:
            show_warning_message(self, "Bölüm Seçilmedi",
                                 "Lütfen dersliklerini yönetmek için bir bölüm seçin.")
            return

        from student_system.views.exam_scheduler import ExamScheduler
        self.clear_content_area()
        uploader = ExamScheduler(scoped_user, self)
        self.content_layout.addWidget(uploader)

    def open_seating_plan(self):
        if not self.permission_manager.has_permission('OTURMA_PLAN'):
            self.show_permission_error()
            return

        scoped_user = self.get_scoped_user()

        if scoped_user['rol'] == 'Admin' and scoped_user['bolum_id'] is None:
            show_warning_message(self, "Bölüm Seçilmedi",
                                 "Lütfen dersliklerini yönetmek için bir bölüm seçin.")
            return

        try:
            from student_system.views.seat_plan import SeatPlanView
            self.clear_content_area()
            self.seatplan_widget = SeatPlanView(scoped_user, self.permission_manager, parent=self)
            self.content_layout.addWidget(self.seatplan_widget)
        except Exception as e:
            QMessageBox.critical(self, "Oturma Planı",
                                 f"Ekran yüklenirken hata:\n\n{e}\n\n{traceback.format_exc()}")

    ### YENİ EKLENTİ: PROFİL PENCERESİNİ AÇMA ###
    def open_profile_settings(self):
        # user['id']'yi diyaloga gönderiyoruz
            dialog = ProfileSettingsDialog(self.user['id'], self)
            dialog.exec_()
        ### YENİ EKLENTİ SONU ###

    def logout(self):
        if show_confirmation_dialog(self, 'Çıkış', 'Çıkış yapmak istediğinize emin misiniz?'):
            self.close()
            from student_system.views.login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()

    def show_permission_error(self):
        show_warning_message(self, 'Yetki Hatası', 'Bu işlem için yetkiniz bulunmamaktadır.')