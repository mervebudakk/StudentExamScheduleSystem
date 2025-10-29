import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from .config import db_settings
import bcrypt
from typing import List, Dict, Optional


class Database:
    """Veritabanı işlemleri için yönetici sınıf"""

    @staticmethod
    def get_connection():
        """Veritabanı bağlantısı al"""
        return psycopg2.connect(**db_settings.psycopg2_params)

    @staticmethod
    def execute_query(query: str, params: tuple = None, fetch: bool = True):
        """
        SQL sorgusu çalıştır

        Args:
            query: SQL sorgusu
            params: Parametreler
            fetch: True ise sonuçları döndür, False ise etkilenen satır sayısını döndür

        Returns:
            fetch=True: List[Dict] (sonuçlar)
            fetch=False: int (etkilenen satır sayısı)
        """
        conn = Database.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cur.execute(query, params)

            if fetch:
                result = cur.fetchall()
                return [dict(row) for row in result]
            else:
                conn.commit()
                return cur.rowcount

        except Exception as e:
            if not fetch:
                conn.rollback()
            raise e
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def execute_non_query(query: str, params: tuple = None) -> int:
        """
        Sonuç döndürmeyen DML sorguları (INSERT/UPDATE/DELETE) için yardımcı.
        Dönüş: etkilenen satır sayısı
        """
        return Database.execute_query(query, params, fetch=False)

    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[Dict]:
        """
        Kullanıcı girişi yap

        Args:
            email: E-posta adresi
            password: Şifre

        Returns:
            Başarılı ise kullanıcı bilgileri, değilse None
        """
        result = Database.execute_query("""
            SELECT k.kullanici_id, k.sifre_hash, k.ad_soyad, 
                   k.bolum_id, r.rol_adi, b.bolum_adi
            FROM kullanicilar k
            JOIN roller r ON k.rol_id = r.rol_id
            LEFT JOIN bolumler b ON k.bolum_id = b.bolum_id
            WHERE k.email = %s AND k.aktif = true
        """, (email,))

        if not result:
            return None

        user = result[0]

        # Şifre kontrolü
        if bcrypt.checkpw(password.encode('utf-8'),
                          user['sifre_hash'].encode('utf-8')):
            # Son giriş zamanını güncelle
            Database.execute_query("""
                UPDATE kullanicilar 
                SET son_giris = CURRENT_TIMESTAMP 
                WHERE kullanici_id = %s
            """, (user['kullanici_id'],), fetch=False)

            return {
                'id': user['kullanici_id'],
                'ad_soyad': user['ad_soyad'],
                'bolum_id': user['bolum_id'],
                'bolum_adi': user['bolum_adi'],
                'rol': user['rol_adi']
            }

        return None

    @staticmethod
    def get_user_permissions(user_id: int) -> List[str]:
        """Kullanıcının yetkilerini getir"""
        result = Database.execute_query("""
            SELECT y.yetki_kodu 
            FROM kullanicilar k
            JOIN roller r ON k.rol_id = r.rol_id
            JOIN rolyetkileri ry ON r.rol_id = ry.rol_id
            JOIN yetkiler y ON ry.yetki_id = y.yetki_id
            WHERE k.kullanici_id = %s
        """, (user_id,))

        return [p['yetki_kodu'] for p in result]

    @staticmethod
    def get_all_departments() -> List[Dict]:
        """Tüm bölümleri getir"""
        return Database.execute_query("""
            SELECT bolum_id, bolum_adi, aktif 
            FROM bolumler 
            WHERE aktif = true
            ORDER BY bolum_adi
        """)

    @staticmethod
    def execute_many(query, data_list):
        """
        Birden fazla kayıt için toplu sorgu çalıştırır.
        """
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.executemany(query, data_list)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @staticmethod
    def get_classrooms_by_department(bolum_id: int) -> List[Dict]:
        """Bölüme ait derslikleri getir"""
        return Database.execute_query("""
            SELECT * FROM derslikler 
            WHERE bolum_id = %s AND aktif = true
            ORDER BY derslik_kodu
        """, (bolum_id,))

    @staticmethod
    def create_all_tables():
        """Tüm tabloları oluştur"""
        conn = Database.get_connection()
        cur = conn.cursor()

        try:
            with open('database/schema.sql', 'r', encoding='utf-8') as f:
                schema_sql = f.read()

            cur.execute(schema_sql)
            conn.commit()

            print("✅ Tüm tablolar oluşturuldu!")
            return True

        except Exception as e:
            print(f"❌ Hata: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def create_admin_user(email="admin@kocaeli.edu.tr", password="admin123"):
        """Admin kullanıcısı oluştur"""
        conn = Database.get_connection()
        cur = conn.cursor()

        try:
            password_hash = bcrypt.hashpw(
                password.encode('utf-8'),
                bcrypt.gensalt(12)
            ).decode('utf-8')

            cur.execute("""
                INSERT INTO kullanicilar (email, sifre_hash, ad_soyad, rol_id, aktif)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
                RETURNING kullanici_id
            """, (email, password_hash, 'Sistem Admin', 1, True))

            result = cur.fetchone()
            conn.commit()

            if result:
                print(f"✅ Admin oluşturuldu! (ID: {result[0]})")
                print(f"   Email: {email}")
                print(f"   Şifre: {password}")
            else:
                print("⚠️  Admin zaten mevcut.")

            return True

        except Exception as e:
            print(f"❌ Hata: {e}")
            conn.rollback()
            return False
        finally:
            cur.close()
            conn.close()

    ### YENİ EKLENTİ: İş Akışı Kontrol Fonksiyonları ###

    @staticmethod
    def check_classrooms_exist(bolum_id: int) -> bool:
        """Bölüm için en az bir derslik var mı?"""
        if bolum_id is None:
            return False
        r = Database.execute_query(
            "SELECT COUNT(*) as c FROM derslikler WHERE bolum_id=%s AND aktif=true", (bolum_id,)
        )
        return r[0]['c'] > 0 if r else False

    @staticmethod
    def check_courses_exist(bolum_id: int) -> bool:
        """Bölüm için en az bir ders var mı?"""
        if bolum_id is None:
            return False
        r = Database.execute_query(
            "SELECT COUNT(*) as c FROM dersler WHERE bolum_id=%s AND aktif=true", (bolum_id,)
        )
        return r[0]['c'] > 0 if r else False

    @staticmethod
    def check_students_exist(bolum_id: int) -> bool:
        """Bölüm için en az bir öğrenci var mı?"""
        if bolum_id is None:
            return False
        r = Database.execute_query(
            "SELECT COUNT(*) as c FROM ogrenciler WHERE bolum_id=%s AND aktif=true", (bolum_id,)
        )
        return r[0]['c'] > 0 if r else False

    @staticmethod
    def check_schedule_exists(bolum_id: int) -> bool:
        """Bölüm için en az bir sınav programı var mı?"""
        if bolum_id is None:
            return False
        r = Database.execute_query(
            "SELECT COUNT(*) as c FROM sinavlar WHERE bolum_id=%s", (bolum_id,)
        )
        return r[0]['c'] > 0 if r else False

    ### YENİ EKLENTİ SONU ###


# Eski isimlendirme için backward compatibility
DatabaseManager = Database

if __name__ == "__main__":
    """Test"""
    print("Veritabanı bağlantısı test ediliyor...")
    conn = Database.get_connection()
    print("✅ Bağlantı başarılı!")
    conn.close()

    print("\nBölümler:")
    for dept in Database.get_all_departments():
        print(f"  - {dept['bolum_adi']}")