from .database import Database  # database.py ile aynı dizinde olduğu için
from typing import Set


class PermissionManager:
    """
    Kullanıcı rollerini ve yetkilerini yöneten sınıf.
    Veritabanından kullanıcının yetkilerini yükler ve kontrol eder.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.permissions: Set[str] = self.load_permissions()

    def load_permissions(self) -> Set[str]:
        """Kullanıcının veritabanından yetki kodlarını yükler."""
        try:
            perms_list = Database.execute_query("""
                SELECT y.yetki_kodu 
                FROM kullanicilar k
                JOIN roller r ON k.rol_id = r.rol_id
                JOIN rolyetkileri ry ON r.rol_id = ry.rol_id
                JOIN yetkiler y ON ry.yetki_id = y.yetki_id
                WHERE k.kullanici_id = %s
            """, (self.user_id,))

            return {p['yetki_kodu'] for p in perms_list} if perms_list else set()

        except Exception as e:
            print(f"Yetkiler yüklenirken hata: {e}")
            return set()

    def has_permission(self, permission_code: str) -> bool:
        """Kullanıcının belirli bir yetkiye (veya 'Admin' ise tüm yetkilere)
           sahip olup olmadığını kontrol eder."""

        # 'Admin' rolü her zaman tüm yetkilere sahiptir
        if 'ADMIN_FULL_ACCESS' in self.permissions:
            return True

        return permission_code in self.permissions

    def can_manage_all_departments(self) -> bool:
        """Kullanıcının 'Admin' gibi tüm bölümleri yönetip yönetemeyeceğini kontrol eder."""
        # 'TUM_BOLUM_ERISIM' gibi özel bir yetki kodu kullanmak iyi bir pratiktir
        # Bu kodu 'ADMIN_FULL_ACCESS' olarak güncelledim,
        # veritabanınızdaki 'roller' tablosuna göre düzenleyebilirsiniz.
        return self.has_permission('ADMIN_FULL_ACCESS')