"""
Dinamik Sınav Takvimi Sistemi - Ana Dashboard
RBAC (Role-Based Access Control) ile yetki yönetimi
Tek dashboard, dinamik menü ve yetki kontrolleri
"""
import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QFrame, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
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
        """, (self.user_id,))

        return {p['yetki_kodu'] for p in perms}

    def has_permission(self, permission_code):
        """Yetki kontrolü"""
        return permission_code in self.permissions

    def can_manage_all_departments(self):
        """Tüm bölümlere erişim var mı?"""
        return self.has_permission('TUM_BOLUM_ERISIM')


class MainDashboard(QMainWindow):
    """Ana yönetim ekranı - RBAC ile"""

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.permission_manager = PermissionManager(user['id'])
        self.init_ui()

    def init_ui(self):
        """Arayüzü oluştur"""
        self.setWindowTitle(f"Sınav Takvimi Sistemi - {self.user['ad_soyad']}")
        self.setMinimumSize(1200, 800)

        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Ana layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sol panel (Menü)
        sidebar = self.create_sidebar()

        # Sağ panel (İçerik)
        content_area = self.create_content_area()

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content_area, stretch=1)

        central_widget.setLayout(main_layout)

    def create_sidebar(self):
        """Sol menü paneli - Yetkiye göre dinamik"""
        sidebar = QFrame()
        sidebar.setFixedWidth(280)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-right: 1px solid #34495e;
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
                color: #95a5a6;
                padding: 20px 20px 10px 20px;
                font-size: 12px;
                font-weight: bold;
                letter-spacing: 1px;
            }
        """)
        layout.addWidget(menu_title)

        # Menü öğeleri (Yetki bazlı)
        menu_items = self.get_menu_items()

        for item in menu_items:
            btn = self.create_menu_button(
                item['text'],
                item['icon'],
                item['callback']
            )
            layout.addWidget(btn)

        layout.addStretch()

        # Çıkış butonu
        logout_btn = self.create_menu_button('Çıkış', '🚪', self.logout)
        logout_btn.setStyleSheet(logout_btn.styleSheet() + """
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        layout.addWidget(logout_btn)

        sidebar.setLayout(layout)
        return sidebar

    def get_menu_items(self):
        """Kullanıcının yetkilerine göre menü öğelerini oluştur"""
        pm = self.permission_manager
        items = []

        # Ana Sayfa (herkes görebilir)
        items.append({
            'text': 'Ana Sayfa',
            'icon': '🏠',
            'callback': self.show_dashboard
        })

        # Kullanıcı Yönetimi (Sadece admin)
        if pm.has_permission('KULLANICI_EKLE'):
            items.append({
                'text': 'Kullanıcı Yönetimi',
                'icon': '👥',
                'callback': self.open_user_management
            })

        # Derslik Yönetimi
        if pm.has_permission('DERSLIK_YONET'):
            items.append({
                'text': 'Derslik Yönetimi',
                'icon': '🏫',
                'callback': self.open_classroom_management
            })

        # Ders Yükleme
        if pm.has_permission('DERS_YUKLE'):
            items.append({
                'text': 'Ders Listesi Yükle',
                'icon': '📚',
                'callback': self.open_course_upload
            })

        # Öğrenci Yükleme
        if pm.has_permission('OGRENCI_YUKLE'):
            items.append({
                'text': 'Öğrenci Listesi Yükle',
                'icon': '👨‍🎓',
                'callback': self.open_student_upload
            })

        # Sınav Programı
        if pm.has_permission('SINAV_OLUSTUR'):
            items.append({
                'text': 'Sınav Programı',
                'icon': '📅',
                'callback': self.open_exam_scheduler
            })

        # Oturma Planı
        if pm.has_permission('OTURMA_PLAN'):
            items.append({
                'text': 'Oturma Planı',
                'icon': '💺',
                'callback': self.open_seating_plan
            })

        # Raporlar (herkes görebilir)
        items.append({
            'text': 'Raporlar',
            'icon': '📊',
            'callback': self.open_reports
        })

        return items

    def create_user_info_section(self):
        """Kullanıcı bilgi bölümü"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #34495e;
                padding: 20px;
                border-bottom: 1px solid #2c3e50;
            }
        """)

        layout = QVBoxLayout()

        # Avatar (emoji)
        avatar = QLabel('👤')
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("font-size: 48px;")

        # İsim
        name = QLabel(self.user['ad_soyad'])
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
                margin-top: 10px;
            }
        """)

        # Rol
        role = QLabel(self.user['rol'])
        role.setAlignment(Qt.AlignCenter)
        role.setStyleSheet("""
            QLabel {
                color: #95a5a6;
                font-size: 12px;
                margin-top: 5px;
            }
        """)

        # Bölüm (varsa)
        if self.user['bolum_adi']:
            dept = QLabel(self.user['bolum_adi'])
            dept.setAlignment(Qt.AlignCenter)
            dept.setStyleSheet("""
                QLabel {
                    color: #3498db;
                    font-size: 11px;
                    margin-top: 3px;
                }
            """)
            layout.addWidget(dept)

        layout.addWidget(avatar)
        layout.addWidget(name)
        layout.addWidget(role)

        frame.setLayout(layout)
        return frame

    def create_menu_button(self, text, icon, callback):
        """Menü butonu oluştur"""
        btn = QPushButton(f"{icon}  {text}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(callback)
        btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 15px 20px;
                border: none;
                background-color: transparent;
                color: #ecf0f1;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #34495e;
                color: white;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
        """)
        return btn

    def create_content_area(self):
        """İçerik alanı"""
        content = QFrame()
        content.setStyleSheet("""
            QFrame {
                background-color: #ecf0f1;
            }
        """)

        layout = QVBoxLayout()

        # Başlık
        header = QLabel('Hoş Geldiniz')
        header.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                padding: 30px;
            }
        """)

        # İstatistikler (Dashboard)
        stats = self.create_statistics_section()

        layout.addWidget(header)
        layout.addWidget(stats)
        layout.addStretch()

        content.setLayout(layout)
        return content

    def create_statistics_section(self):
        """İstatistik kartları"""
        frame = QFrame()
        frame.setStyleSheet("background-color: transparent;")

        layout = QGridLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 0, 30, 30)

        # Admin ise tüm bölümlerin istatistiklerini göster
        if self.permission_manager.can_manage_all_departments():
            stats = [
                ('Toplam Bölüm', self.get_department_count(), '#3498db'),
                ('Toplam Derslik', self.get_classroom_count(), '#2ecc71'),
                ('Toplam Ders', self.get_course_count(), '#e74c3c'),
                ('Toplam Öğrenci', self.get_student_count(), '#f39c12'),
            ]
        else:
            # Koordinatör ise sadece kendi bölümünün istatistiklerini göster
            stats = [
                ('Derslikler', self.get_classroom_count(self.user['bolum_id']), '#3498db'),
                ('Dersler', self.get_course_count(self.user['bolum_id']), '#2ecc71'),
                ('Öğrenciler', self.get_student_count(self.user['bolum_id']), '#e74c3c'),
                ('Sınavlar', self.get_exam_count(self.user['bolum_id']), '#f39c12'),
            ]

        for i, (title, value, color) in enumerate(stats):
            card = self.create_stat_card(title, value, color)
            layout.addWidget(card, i // 2, i % 2)

        frame.setLayout(layout)
        return frame

    def create_stat_card(self, title, value, color):
        """İstatistik kartı"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border-left: 5px solid {color};
            }}
        """)
        card.setFixedHeight(120)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-size: 13px;
            }
        """)

        value_label = QLabel(str(value))
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 36px;
                font-weight: bold;
            }}
        """)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addStretch()

        card.setLayout(layout)
        return card

    # =================== İSTATİSTİK FONKSİYONLARI ===================

    def get_department_count(self):
        """Toplam bölüm sayısı"""
        result = Database.execute_query("SELECT COUNT(*) as count FROM bolumler WHERE aktif = true")
        return result[0]['count'] if result else 0

    def get_classroom_count(self, bolum_id=None):
        """Derslik sayısı"""
        if bolum_id:
            result = Database.execute_query(
                "SELECT COUNT(*) as count FROM derslikler WHERE bolum_id = %s AND aktif = true",
                (bolum_id,)
            )
        else:
            result = Database.execute_query("SELECT COUNT(*) as count FROM derslikler WHERE aktif = true")
        return result[0]['count'] if result else 0

    def get_course_count(self, bolum_id=None):
        """Ders sayısı"""
        if bolum_id:
            result = Database.execute_query(
                "SELECT COUNT(*) as count FROM dersler WHERE bolum_id = %s AND aktif = true",
                (bolum_id,)
            )
        else:
            result = Database.execute_query("SELECT COUNT(*) as count FROM dersler WHERE aktif = true")
        return result[0]['count'] if result else 0

    def get_student_count(self, bolum_id=None):
        """Öğrenci sayısı"""
        if bolum_id:
            result = Database.execute_query(
                "SELECT COUNT(*) as count FROM ogrenciler WHERE bolum_id = %s AND aktif = true",
                (bolum_id,)
            )
        else:
            result = Database.execute_query("SELECT COUNT(*) as count FROM ogrenciler WHERE aktif = true")
        return result[0]['count'] if result else 0

    def get_exam_count(self, bolum_id=None):
        """Sınav sayısı"""
        if bolum_id:
            result = Database.execute_query(
                "SELECT COUNT(*) as count FROM sinavlar WHERE bolum_id = %s",
                (bolum_id,)
            )
        else:
            result = Database.execute_query("SELECT COUNT(*) as count FROM sinavlar")
        return result[0]['count'] if result else 0

    # =================== MENÜ CALLBACK FONKSİYONLARI ===================

    def show_dashboard(self):
        """Ana sayfa"""
        QMessageBox.information(self, 'Ana Sayfa', 'Ana sayfa zaten açık!')

    def open_user_management(self):
        """Kullanıcı yönetimi (Sadece Admin)"""
        if not self.permission_manager.has_permission('KULLANICI_EKLE'):
            QMessageBox.warning(self, 'Yetki Hatası', 'Bu işlem için yetkiniz yok!')
            return

        QMessageBox.information(self, 'Kullanıcı Yönetimi', 'Kullanıcı yönetim ekranı açılacak...')

    def open_classroom_management(self):
        """Derslik yönetimi"""
        if not self.permission_manager.has_permission('DERSLIK_YONET'):
            QMessageBox.warning(self, 'Yetki Hatası', 'Bu işlem için yetkiniz yok!')
            return

        QMessageBox.information(self, 'Derslik Yönetimi', 'Derslik yönetim ekranı açılacak...')

    def open_course_upload(self):
        """Ders listesi yükleme"""
        if not self.permission_manager.has_permission('DERS_YUKLE'):
            QMessageBox.warning(self, 'Yetki Hatası', 'Bu işlem için yetkiniz yok!')
            return

        QMessageBox.information(self, 'Ders Yükleme', 'Ders yükleme ekranı açılacak...')

    def open_student_upload(self):
        """Öğrenci listesi yükleme"""
        if not self.permission_manager.has_permission('OGRENCI_YUKLE'):
            QMessageBox.warning(self, 'Yetki Hatası', 'Bu işlem için yetkiniz yok!')
            return

        QMessageBox.information(self, 'Öğrenci Yükleme', 'Öğrenci yükleme ekranı açılacak...')

    def open_exam_scheduler(self):
        """Sınav programı"""
        if not self.permission_manager.has_permission('SINAV_OLUSTUR'):
            QMessageBox.warning(self, 'Yetki Hatası', 'Bu işlem için yetkiniz yok!')
            return

        QMessageBox.information(self, 'Sınav Programı', 'Sınav programı ekranı açılacak...')

    def open_seating_plan(self):
        """Oturma planı"""
        if not self.permission_manager.has_permission('OTURMA_PLAN'):
            QMessageBox.warning(self, 'Yetki Hatası', 'Bu işlem için yetkiniz yok!')
            return

        QMessageBox.information(self, 'Oturma Planı', 'Oturma planı ekranı açılacak...')

    def open_reports(self):
        """Raporlar"""
        QMessageBox.information(self, 'Raporlar', 'Rapor ekranı açılacak...')

    def logout(self):
        """Çıkış yap"""
        reply = QMessageBox.question(
            self,
            'Çıkış',
            'Çıkış yapmak istediğinize emin misiniz?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.close()
            # Login ekranını tekrar aç
            # TODO: Login window'u tekrar göster


# Test
if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Test kullanıcısı (normalde login'den gelecek)
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