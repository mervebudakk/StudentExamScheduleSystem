import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

try:
    from student_system.views.login_window import LoginWindow
except ImportError as e:
    print(f"❌ Import hatası: {e}")
    print("\n🔍 Kontrol edilecekler:")
    print("1. student_system/views/__init__.py var mı?")
    print("2. student_system/views/login_window.py var mı?")
    print("3. LoginWindow sınıfı doğru mu?")
    sys.exit(1)


def main():
    app = QApplication(sys.argv)

    font = QFont('Segoe UI', 10)
    app.setFont(font)

    try:
        login_window = LoginWindow()
        login_window.show()
    except Exception as e:
        print(f"❌ LoginWindow oluşturulamadı: {e}")
        import traceback
        traceback.print_exc()
        return

    sys.exit(app.exec_())


if __name__ == '__main__':
    print("Uygulama başlatılıyor")
    main()