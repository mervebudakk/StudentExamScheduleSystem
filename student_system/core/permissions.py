from .database import Database  # database.py ile aynı dizinde olduğu için
from typing import Set


class PermissionManager:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.permissions: Set[str] = self.load_permissions()

    def load_permissions(self) -> Set[str]:
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
        if 'ADMIN_FULL_ACCESS' in self.permissions:
            return True

        return permission_code in self.permissions

    def can_manage_all_departments(self) -> bool:
        return self.has_permission('ADMIN_FULL_ACCESS')