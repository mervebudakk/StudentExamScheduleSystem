import sys
from loguru import logger

# Proje ana dizinini Python path'ine ekliyoruz.
# Bu sayede "student_system" modülünü bulabiliyor.
sys.path.append('.')

from student_system.core.database import init_pool, fetch_one


def main():
    """
    Veritabanı bağlantısını test etmek için ana fonksiyon.
    """
    logger.info("Veritabanı bağlantısı test ediliyor...")

    try:
        # 1. Bağlantı havuzunu başlatmayı dene.
        # Bu fonksiyon, .env dosyasını okuyup bağlantı kurmaya çalışacak.
        init_pool()

        # 2. Bağlantının çalıştığını doğrulamak için basit bir sorgu gönder.
        logger.info("PostgreSQL sunucu versiyonu sorgulanıyor...")
        version_info = fetch_one("SELECT version();")

        if version_info:
            logger.success("Sorgu başarılı! Sunucu versiyonu:")
            # Gelen sonucun ilk elemanını (versiyon metnini) yazdır.
            logger.info(version_info[0])
            print("\n✅ VERİTABANI BAĞLANTISI BAŞARILI! ✅")
        else:
            logger.error("Bağlantı kuruldu ancak sorgu bir sonuç döndürmedi.")

    except Exception as e:
        logger.error("❌ VERİTABANI BAĞLANTISI BAŞARISIZ OLDU! ❌")
        logger.error(f"Alınan Hata: {e}")
        print("\nLütfen .env dosyasındaki DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS bilgilerini,")
        print("Tailscale bağlantınızın aktif olduğunu ve PostgreSQL sunucusunun çalıştığını kontrol edin.")


if __name__ == "__main__":
    main()