import psycopg2
from student_system.core.config import db_settings


def test_connection():
    print("=" * 60)
    print("VERİTABANI BAĞLANTI TESTİ")
    print("=" * 60)
    print(f"Host: {db_settings.host}")
    print(f"Port: {db_settings.port}")
    print(f"Database: {db_settings.name}")
    print(f"User: {db_settings.user}")
    print("=" * 60)

    try:
        print("\n⏳ Bağlanılıyor...")
        conn = psycopg2.connect(**db_settings.psycopg2_params)

        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()

        print("✅ BAĞLANTI BAŞARILI!")
        print(f"\nPostgreSQL Version:")
        print(version[0])

        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)

        tables = cur.fetchall()

        if tables:
            print(f"\n📊 Mevcut Tablolar ({len(tables)} adet):")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("\n⚠️  Henüz tablo oluşturulmamış.")

        cur.close()
        conn.close()

        return True

    except psycopg2.OperationalError as e:
        print("❌ BAĞLANTI HATASI!")
        print(f"\nHata: {e}")
        print("\n🔍 Kontrol Edilecekler:")
        print("  1. Tailscale bağlantınız aktif mi?")
        print("  2. PostgreSQL servisi çalışıyor mu?")
        print("  3. .env dosyasındaki bilgiler doğru mu?")
        print("  4. Firewall PostgreSQL'e izin veriyor mu?")
        return False

    except Exception as e:
        print(f"❌ BEKLENMEYEN HATA: {e}")
        return False


if __name__ == "__main__":
    test_connection()