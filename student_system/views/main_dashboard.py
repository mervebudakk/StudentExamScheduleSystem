import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QFrame, QGridLayout, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from student_system.core.database import Database
import traceback


class PermissionManager:
    def __init__(self, user_id):
        self.user_id = user_id
        self.permissions = self.load_permissions()

    def load_permissions(self):
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
        return permission_code in self.permissions

    def can_manage_all_departments(self):
        return self.has_permission('TUM_BOLUM_ERISIM')


class MainDashboard(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.permission_manager = PermissionManager(user['id'])
        self.content_layout = None
        self.active_menu_button = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Sınav Takvimi Sistemi - {self.user['ad_soyad']}")
        self.setMinimumSize(1400, 900)

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

        menu_title = QLabel('MENÜ')
        menu_title.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.9);
                padding: 30px 20px 15px 20px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
            }
        """)
        layout.addWidget(menu_title)

        for item in self.get_menu_items():
            btn = self.create_menu_button(item['text'], item['icon'], item['callback'])
            layout.addWidget(btn)

        layout.addStretch()

        logout_btn = self.create_menu_button('Çıkış', '🚪', self.logout)
        logout_btn.setStyleSheet(logout_btn.styleSheet() + """
            QPushButton:hover {
                background-color: rgba(231, 76, 60, 0.9) !important;
            }
        """)
        layout.addWidget(logout_btn)

        sidebar.setLayout(layout)
        return sidebar

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
                padding: 25px 15px;
                margin: 20px 15px;
                border-radius: 15px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(8)

        avatar = QLabel('👤')
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("font-size: 50px;")

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
                padding: 15px 20px;
                border: none;
                color: rgba(255, 255, 255, 0.95);
                font-size: 14px;
                background-color: transparent;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-left: 3px solid white;
            }
        """)
        return btn

    def handle_menu_click(self, button, callback):
        if self.active_menu_button:
            self.active_menu_button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 15px 20px;
                    border: none;
                    color: rgba(255, 255, 255, 0.95);
                    font-size: 14px;
                    background-color: transparent;
                    border-left: 3px solid transparent;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                    border-left: 3px solid white;
                }
            """)

        button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 15px 20px;
                border: none;
                color: white;
                font-size: 14px;
                background-color: rgba(255, 255, 255, 0.15);
                border-left: 3px solid white;
                font-weight: 600;
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

    def show_dashboard(self):
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
        from student_system.views.classroom_management import ClassroomManagement
        self.clear_content_area()
        self.cm_widget = ClassroomManagement(self.user, self.permission_manager, parent=self)
        self.content_layout.addWidget(self.cm_widget)

    def open_course_upload(self):
        if not self.permission_manager.has_permission('DERS_YUKLE'):
            self.show_permission_error()
            return
        from student_system.views.lesson_list import LessonListUploader
        self.clear_content_area()
        uploader = LessonListUploader(self.user, self)
        self.content_layout.addWidget(uploader)

    def open_student_upload(self):
        if not self.permission_manager.has_permission('OGRENCI_YUKLE'):
            self.show_permission_error()
            return
        from student_system.views.student_list import StudentListUploader
        self.clear_content_area()
        uploader = StudentListUploader(self.user, self)
        self.content_layout.addWidget(uploader)

    def open_exam_scheduler(self):
        if not self.permission_manager.has_permission('SINAV_OLUSTUR'):
            self.show_permission_error()
            return
        from student_system.views.exam_scheduler import ExamScheduler
        self.clear_content_area()
        uploader = ExamScheduler(self.user, self)
        self.content_layout.addWidget(uploader)

    def open_seating_plan(self):
        if not self.permission_manager.has_permission('OTURMA_PLAN'):
            self.show_permission_error()
            return
        try:
            from student_system.views.seat_plan import SeatPlanView
            self.clear_content_area()
            self.seatplan_widget = SeatPlanView(self.user, self.permission_manager, parent=self)
            self.content_layout.addWidget(self.seatplan_widget)
        except Exception as e:
            QMessageBox.critical(self, "Oturma Planı",
                               f"Ekran yüklenirken hata:\n\n{e}\n\n{traceback.format_exc()}")


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
                border-radius: 6px;
                padding: 10px 25px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        msg.exec_()
