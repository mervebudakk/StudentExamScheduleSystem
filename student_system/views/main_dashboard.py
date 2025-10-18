"""
Dinamik Sınav Takvimi Sistemi - Ana Dashboard
Login window ile uyumlu yeşil tema
"""
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from student_system.core.database import Database


class PermissionManager:
    """Yetki kontrol yöneticisi"""

    def __init__(self, user_id):
        self.user_id = user_id
        self.permissions = self.load_permissions()

    def load_permissions(self):
        """Kullanıcının yetkilerini yükle"""
        perms = Database.execute_query("""
            SELECT y.yetki_kodu 
            FROM kullanicilar k
            JOIN roller r ON k.rol_id = r.rol_id
            JOIN rolyetkileri ry ON r.rol_id = ry.rol_id
            JOIN yetkiler y ON ry.yetki_id = y.yetki_id
            WHERE k.kullanici_id = %s
        """, (self.user_id,)) or []

        return {p['yetki_kodu'] for p in perms}

    def has_permission(self, permission_code):
        """Yetki kontrolü"""
        return permission_code in self.permissions

    def can_manage_all_departments(self):
        """Tüm bölümlere erişim var mı?"""
        return self.has_permission('TUM_BOLUM_ERISIM')


class MainDashboard(QMainWindow):

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.permission_manager = PermissionManager(user['id'])
        self.init_ui()

    def init_ui(self):
        """Arayüzü oluştur"""
        self.setWindowTitle(f"Sınav Takvimi Sistemi - {self.user['ad_soyad']}")
        self.setMinimumSize(1300, 850)

        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Ana layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sol panel
        sidebar = self.create_sidebar()

        # Sağ panel
        content_area = self.create_content_area()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area, stretch=1)

        central_widget.setLayout(main_layout)

    def create_content_area(self):
        """İçerik alanı"""
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background-color: #f8f9fa;")

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)

        # Varsayılan olarak dashboard içeriğini göster
        self.show_dashboard_content()

        self.content_frame.setLayout(self.content_layout)
        return self.content_frame

    def clear_content_area(self):
        """İçerik alanını temizle"""
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

    def show_dashboard_content(self):
        """Dashboard varsayılan içeriği yükle"""
        self.clear_content_area()
        top_bar = self.create_top_bar()
        stats = self.create_statistics_section()
        self.content_layout.addWidget(top_bar)
        self.content_layout.addWidget(stats)
        self.content_layout.addStretch()

    def create_sidebar(self):
        """Sol menü - Login ile aynı yeşil (#27ae60)"""
        sidebar = QFrame()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: rgba(39, 174, 96, 0.95);
                border-right: none;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Kullanıcı bilgisi
        user_info = self.create_user_info_section()
        layout.addWidget(user_info)

        # Menü başlığı
        menu_title = QLabel('MENÜ')
        menu_title.setStyleSheet("""
            QLabel {
                color: white;
                padding: 25px 20px 15px 20px;
                font-size: 13px;
                font-weight: bold;
            }
        """)
        layout.addWidget(menu_title)

        # Menü öğeleri
        for item in self.get_menu_items():
            btn = self.create_menu_button(item['text'], item['icon'], item['callback'])
            layout.addWidget(btn)

        layout.addStretch()

        # Çıkış
        logout_btn = self.create_menu_button('Çıkış', '🚪', self.logout)
        logout_btn.setStyleSheet(logout_btn.styleSheet() + """
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 0.8) !important;
            }
        """)
        layout.addWidget(logout_btn)

        sidebar.setLayout(layout)
        return sidebar

    def get_menu_items(self):
        """Yetkilere göre menü"""
        pm = self.permission_manager
        items = [{'text': 'Ana Sayfa', 'icon': '🏠', 'callback': self.show_dashboard}]

        if pm.has_permission('KULLANICI_EKLE'):
            items.append({'text': 'Kullanıcı Yönetimi', 'icon': '👥', 'callback': self.open_user_management})
        if pm.has_permission('DERSLIK_YONET'):
            items.append({'text': 'Derslik Yönetimi', 'icon': '🏫', 'callback': self.open_classroom_management})
        if pm.has_permission('DERS_YUKLE'):
            items.append({'text': 'Ders Listesi Yükle', 'icon': '📚', 'callback': self.open_course_upload})
        if pm.has_permission('OGRENCI_YUKLE'):
            items.append({'text': 'Öğrenci Listesi Yükle', 'icon': '👨‍🎓', 'callback': self.open_student_upload})
        if pm.has_permission('SINAV_OLUSTUR'):
            items.append({'text': 'Sınav Programı', 'icon': '📅', 'callback': self.open_exam_scheduler})
        if pm.has_permission('OTURMA_PLAN'):
            items.append({'text': 'Oturma Planı', 'icon': '💺', 'callback': self.open_seating_plan})

        items.append({'text': 'Raporlar', 'icon': '📊', 'callback': self.open_reports})
        return items

    def create_user_info_section(self):
        """Kullanıcı bilgi kartı"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.98);
                padding: 30px 20px;
                margin: 20px;
                border-radius: 20px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(10)

        avatar = QLabel('👤')
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("font-size: 64px;")

        name = QLabel(self.user['ad_soyad'])
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("color:#27ae60; font-size:18px; font-weight:bold;")

        role = QLabel(self.user['rol'])
        role.setAlignment(Qt.AlignCenter)
        role.setStyleSheet("color:#2c3e50; font-size:14px;")

        layout.addWidget(avatar)
        layout.addWidget(name)
        layout.addWidget(role)

        if self.user['bolum_adi']:
            dept = QLabel(self.user['bolum_adi'])
            dept.setAlignment(Qt.AlignCenter)
            dept.setStyleSheet("color:#7f8c8d; font-size:12px;")
            layout.addWidget(dept)

        frame.setLayout(layout)
        return frame

    def create_menu_button(self, text, icon, callback):
        btn = QPushButton(f"{icon}  {text}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 16px 22px;
                border: none;
                color: white;
                font-size: 15px;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(34,153,84,0.7);
            }
            QPushButton:pressed {
                background-color: rgba(30,132,73,0.9);
            }
        """)
        return btn

    def create_top_bar(self):
        bar = QFrame()
        bar.setStyleSheet("""
            QFrame {
                background-color: white;
                border-bottom: 3px solid #27ae60;
                margin: 20px;
                border-radius: 15px 15px 0 0;
            }
        """)
        layout = QHBoxLayout()
        layout.setContentsMargins(35, 25, 35, 25)

        welcome = QLabel(f'Hoş Geldiniz, {self.user["ad_soyad"]}')
        welcome.setStyleSheet("color:#27ae60; font-size:26px; font-weight:bold;")

        role_badge = QLabel(f'🎓 {self.user["rol"]}')
        role_badge.setStyleSheet("""
            color:white; background-color:#27ae60;
            padding:10px 20px; border-radius:12px; font-weight:bold;
        """)

        layout.addWidget(welcome)
        layout.addStretch()
        layout.addWidget(role_badge)
        bar.setLayout(layout)
        return bar

    def create_statistics_section(self):
        frame = QFrame()
        layout = QGridLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

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
            card = self.create_stat_card(title, value, color, icon)
            layout.addWidget(card, i // 2, i % 2)

        frame.setLayout(layout)
        return frame

    def create_stat_card(self, title, value, color, icon):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 20px;
                border-left: 5px solid {color};
            }}
        """)
        card.setFixedHeight(140)
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 20, 25, 20)

        top = QHBoxLayout()
        top.addWidget(QLabel(icon))
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color:#2c3e50; font-size:15px; font-weight:600;")
        top.addWidget(title_lbl)
        top.addStretch()

        val = QLabel(str(value))
        val.setStyleSheet(f"color:{color}; font-size:40px; font-weight:bold;")

        layout.addLayout(top)
        layout.addWidget(val)
        card.setLayout(layout)
        return card

    # ============ İSTATİSTİKLER ============

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

    # ============ MENÜLER ============

    def show_dashboard(self):
        self.show_dashboard_content()

    def open_user_management(self):
        if not self.permission_manager.has_permission('KULLANICI_EKLE'):
            self.show_permission_error(); return
        QMessageBox.information(self, 'Kullanıcı Yönetimi', 'Kullanıcı yönetim ekranı hazırlanıyor...')

    def open_classroom_management(self):
        if not self.permission_manager.has_permission('DERSLIK_YONET'):
            self.show_permission_error(); return

        from student_system.views.classroom_management import ClassroomManagement
        self.classroom_win = ClassroomManagement(self.user, self.permission_manager, self)
        self.classroom_win.show()
        self.classroom_win.raise_()
        self.classroom_win.activateWindow()

    def open_course_upload(self):
        if not self.permission_manager.has_permission('DERS_YUKLE'):
            self.show_permission_error(); return

        from student_system.views.excel_uploader import ExcelUploader
        self.clear_content_area()
        uploader = ExcelUploader(self)
        self.content_layout.addWidget(uploader)

    def open_student_upload(self):
        if not self.permission_manager.has_permission('OGRENCI_YUKLE'):
            self.show_permission_error(); return
        QMessageBox.information(self, 'Öğrenci Yükleme', 'Excel yükleme ekranı hazırlanıyor...')

    def open_exam_scheduler(self):
        if not self.permission_manager.has_permission('SINAV_OLUSTUR'):
            self.show_permission_error(); return
        QMessageBox.information(self, 'Sınav Programı', 'Sınav programı ekranı hazırlanıyor...')

    def open_seating_plan(self):
        if not self.permission_manager.has_permission('OTURMA_PLAN'):
            self.show_permission_error(); return
        QMessageBox.information(self, 'Oturma Planı', 'Oturma planı ekranı hazırlanıyor...')

    def open_reports(self):
        QMessageBox.information(self, 'Raporlar', 'Rapor ekranı hazırlanıyor...')

    def logout(self):
        reply = QMessageBox.question(self, 'Çıkış', 'Çıkış yapmak istediğinize emin misiniz?',
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.close()
            from student_system.views.login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()

    def show_permission_error(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle('⚠️ Yetki Hatası')
        msg.setText('Bu işlem için yetkiniz bulunmamaktadır.')
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setStyleSheet("""
            QMessageBox QLabel { color:#2c3e50; font-size:13px; min-width:300px; }
            QPushButton { background-color:#f39c12; color:white; border:none; border-radius:5px; padding:8px 20px; }
            QPushButton:hover { background-color:#e67e22; }
        """)
        msg.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setFont(QFont('Segoe UI', 10))

    test_user = {
        'id': 1,
        'ad_soyad': 'Sistem Admin',
        'bolum_id': None,
        'bolum_adi': None,
        'rol': 'Admin'
    }

    window = MainDashboard(test_user)
    window.show()
    sys.exit(app.exec_())