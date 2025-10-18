# excel_uploader.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog

class ExcelUploader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()

        title = QLabel("📚 Ders Listesi Excel Yükleyici")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #27ae60;")
        layout.addWidget(title)

        upload_btn = QPushButton("Excel Dosyası Seç")
        upload_btn.clicked.connect(self.upload_excel)
        layout.addWidget(upload_btn)

        self.setLayout(layout)

    def upload_excel(self):
        file, _ = QFileDialog.getOpenFileName(self, "Excel Dosyası Seç", "", "Excel Dosyaları (*.xlsx *.xls)")
        if file:
            print("Seçilen dosya:", file)
            # Burada parser işlemlerini yap ve veritabanına kaydet
