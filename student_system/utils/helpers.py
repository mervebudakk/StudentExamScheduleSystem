import re
import bcrypt
from PyQt5.QtWidgets import QMessageBox
from typing import Optional

def show_error_message(parent, title: str, text: str):
    QMessageBox.critical(parent, title, text)

def show_info_message(parent, title: str, text: str):
    QMessageBox.information(parent, title, text)

def show_warning_message(parent, title: str, text: str):
    QMessageBox.warning(parent, title, text)


def show_confirmation_dialog(parent, title, text):
    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(text)
    msg.setIcon(QMessageBox.Question)

    yes_button = msg.addButton("Evet", QMessageBox.YesRole)
    no_button = msg.addButton("Hayır", QMessageBox.NoRole)

    msg.setDefaultButton(no_button)

    ret = msg.exec_()

    return ret == QMessageBox.AcceptRole


def is_valid_email(email: str) -> bool:
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(12)
    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_pw.decode('utf-8')

def check_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'),
                              hashed_password.encode('utf-8'))
    except Exception:
        return False