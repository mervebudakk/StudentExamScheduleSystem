import os
from dotenv import load_dotenv

# .env dosyasının tam yolunu bul
# Bu, script'i projenin neresinden çalıştırırsanız çalıştırın .env dosyasını doğru bulmasını sağlar.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')

# .env dosyasını yükleyerek içindeki değişkenleri ortam değişkeni olarak ayarla
load_dotenv(dotenv_path=dotenv_path)

# Ortam değişkenlerinden veritabanı bilgilerini oku ve Python değişkenlerine ata
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS') # .env dosyasındaki anahtarın DB_PASS olduğundan emin olun