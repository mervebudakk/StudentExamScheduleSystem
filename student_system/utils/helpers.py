import re
import bcrypt
from PyQt5.QtWidgets import QMessageBox
from typing import Optional

# --- Arayüz (PyQt) Helper'ları ---
# [cite_start]Bu fonksiyonlar, PDF'te belirtilen hata ve uyarı mantığını [cite: 156, 239-245, 262-266]
# standart hale getirmek için kullanılır.

def show_error_message(parent, title: str, text: str):
    """Genel bir HATA mesaj kutusu gösterir."""
    QMessageBox.critical(parent, title, text)

def show_info_message(parent, title: str, text: str):
    """Genel bir BİLGİ mesaj kutusu gösterir."""
    QMessageBox.information(parent, title, text)

def show_warning_message(parent, title: str, text: str):
    """Genel bir UYARI mesaj kutusu gösterir."""
    QMessageBox.warning(parent, title, text)

def show_confirmation_dialog(parent, title: str, text: str) -> bool:
    """
    Bir EVET/HAYIR onay kutusu gösterir.
    Kullanıcı 'Evet'e basarsa True döner.
    """
    reply = QMessageBox.question(parent, title, text,
                                 QMessageBox.Yes | QMessageBox.No,
                                 QMessageBox.No) # Varsayılan seçim 'No'
    return reply == QMessageBox.Yes


# --- Validasyon Helper'ları ---

def is_valid_email(email: str) -> bool:
    """
    Basit bir regex ile email formatını doğrular.
    [cite_start]PDF'e göre kullanıcılar e-posta ile giriş yapacaktır[cite: 108].
    """
    if not email:
        return False
    # Standart bir email regex'i
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


# --- Güvenlik Helper'ları ---

def hash_password(password: str) -> str:
    """
    Verilen bir şifreyi (str) bcrypt ile hash'ler ve
    veritabanında saklanabilir bir string (str) olarak döndürür.
    """
    salt = bcrypt.gensalt(12)
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_pw.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    """
    Kullanıcının girdiği şifre (str) ile veritabanındaki hash'i (str) karşılaştırır.
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'),
                              hashed_password.encode('utf-8'))
    except Exception:
        return False