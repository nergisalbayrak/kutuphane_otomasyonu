"""
Kullanıcı Veri Erişim Katmanı (User Repository)
===============================================
Bu modül, kütüphane sistemindeki `User`, `Member` ve `Librarian` varlıklarının
veritabanı işlemlerini gerçekleştiren sınıftır.

Mimarideki Rolü:
----------------
1. Single Table Inheritance Eşlemesi:
   - OOP'deki kalıtım hiyerarşisi (`User -> Member, Librarian`) ilişkisel veritabanında
     tek bir `users` tablosuna aktarılmıştır.
   - Bu sınıf, veritabanından okunan satırdaki `role` değerine göre polimorfik olarak
     doğru alt sınıfı (`Member` veya `Librarian`) üretir (Polymorphic Mapping).
2. Aktif Ödünçlerin İlişkilendirilmesi:
   - Bir üye veritabanından çekildiğinde, `borrow_records` tablosundaki aktif ödünç
     kayıtları da sorgulanarak üyenin `active_borrows` listesine yüklenir.
3. Soyutlama (Abstraction):
   - Üst katmanlar (Service Katmanı), kullanıcı verisinin hangi tabloda nasıl tutulduğuna
     veya SQL sorgularına dair detayları bilmeksizin saf Python nesneleriyle çalışır.
"""

from typing import List, Optional, Union
import sqlite3

from models.user import User, Member, Librarian
from repositories.database import DatabaseManager


class UserRepository:
    """
    Kullanıcı Deposu (User Repository)
    ----------------------------------
    Tasarım Deseni: Repository Pattern & Factory Method Prensibi
    
    `users` tablosu üzerinde üye ve kütüphaneci verilerinin yönetimini sağlar.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        UserRepository yapıcı metodu.

        OOP Karşılığı: Dependency Injection
        
        Args:
            db_manager (DatabaseManager): Veritabanı bağlantı yöneticisi.
        """
        self._db_manager: DatabaseManager = db_manager

    # -------------------------------------------------------------------------
    # Nesneye Dönüştürücü (Polymorphic Data Mapper)
    # -------------------------------------------------------------------------
    def _row_to_entity(self, row: sqlite3.Row, conn: Optional[sqlite3.Connection] = None) -> User:
        """
        SQL Satırını Uygun Kullanıcı Alt Sınıfına Dönüştürme
        ---------------------------------------------------
        OOP Karşılığı: Polymorphism (Çok Biçimlilik) & Factory Pattern
        
        `row['role']` bilgisine bakarak:
        - 'MEMBER' ise `Member` nesnesi oluşturur ve aktif ödünç ID'lerini yükler.
        - 'LIBRARIAN' ise `Librarian` nesnesi oluşturur.
        """
        role = row["role"]
        user_id = row["id"]

        if role == "MEMBER":
            active_borrows: List[int] = []
            # Eğer bağlantı sağlanmışsa üyenin aktif ödünç kayıtlarını da çekiyoruz
            if conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id FROM borrow_records WHERE member_id = ? AND status = 'ACTIVE';",
                    (user_id,)
                )
                active_borrows = [r["id"] for r in cur.fetchall()]

            return Member(
                id=user_id,
                name=row["name"],
                email=row["email"],
                max_book_limit=row["max_book_limit"] or Member.DEFAULT_MAX_BOOK_LIMIT,
                active_borrows=active_borrows
            )
        elif role == "LIBRARIAN":
            return Librarian(
                id=user_id,
                name=row["name"],
                email=row["email"],
                employee_id=row["employee_id"] or ""
            )
        else:
            raise ValueError(f"Bilinmeyen kullanıcı rolü: {role}")

    # -------------------------------------------------------------------------
    # CRUD - Create (Oluşturma / Ekleme)
    # -------------------------------------------------------------------------
    def add(self, user: User) -> User:
        """
        Kullanıcıyı (Üye veya Kütüphaneci) veritabanına ekler.

        OOP / Mimari Karşılığı: Polymorphic Handling
        Gelen nesnenin türüne (`Member` veya `Librarian`) göre ilgili alanlar
        (`max_book_limit` veya `employee_id`) SQL sorgusuna parametre olarak verilir.

        Args:
            user (User): Eklenecek Member veya Librarian nesnesi.

        Returns:
            User: Veritabanı ID'si atanmış kullanıcı nesnesi.
        """
        query = """
            INSERT INTO users (name, email, role, max_book_limit, employee_id)
            VALUES (?, ?, ?, ?, ?);
        """
        max_book_limit = user.max_book_limit if isinstance(user, Member) else None
        employee_id = user.employee_id if isinstance(user, Librarian) else None

        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user.name, user.email, user.role, max_book_limit, employee_id))
            user.id = cursor.lastrowid
            return user

    # -------------------------------------------------------------------------
    # CRUD - Read (Okuma / Sorgulama)
    # -------------------------------------------------------------------------
    def get_by_id(self, user_id: int) -> Optional[User]:
        """
        ID numarasına göre kullanıcı kaydını getirir.

        Args:
            user_id (int): Kullanıcı ID'si.

        Returns:
            Optional[User]: Bulunan `Member` veya `Librarian` nesnesi; yoksa `None`.
        """
        query = "SELECT * FROM users WHERE id = ?;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            row = cursor.fetchone()
            return self._row_to_entity(row, conn) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        """
        E-posta adresine göre kullanıcı arar (Benzersizlik ve giriş kontrolleri için).

        Args:
            email (str): Kullanıcı e-posta adresi.

        Returns:
            Optional[User]: Eşleşen kullanıcı veya `None`.
        """
        query = "SELECT * FROM users WHERE email = ?;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (email.strip(),))
            row = cursor.fetchone()
            return self._row_to_entity(row, conn) if row else None

    def get_all(self) -> List[User]:
        """
        Sistemdeki tüm kullanıcıları (üye ve kütüphaneciler) listeler.

        Returns:
            List[User]: Polimorfik kullanıcı listesi.
        """
        query = "SELECT * FROM users ORDER BY id ASC;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._row_to_entity(row, conn) for row in rows]

    def get_all_members(self) -> List[Member]:
        """
        Sistemde kayıtlı yalnızca üyeleri (`role = 'MEMBER'`) filtreleyerek listeler.

        Returns:
            List[Member]: Üye nesneleri listesi.
        """
        query = "SELECT * FROM users WHERE role = 'MEMBER' ORDER BY name ASC;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            # Hepsi Member olacağı garantilidir
            return [self._row_to_entity(row, conn) for row in rows]  # type: ignore

    def get_all_librarians(self) -> List[Librarian]:
        """
        Sistemde kayıtlı yalnızca kütüphane görevlilerini (`role = 'LIBRARIAN'`) listeler.

        Returns:
            List[Librarian]: Kütüphaneci nesneleri listesi.
        """
        query = "SELECT * FROM users WHERE role = 'LIBRARIAN' ORDER BY name ASC;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._row_to_entity(row, conn) for row in rows]  # type: ignore

    # -------------------------------------------------------------------------
    # CRUD - Update (Güncelleme)
    # -------------------------------------------------------------------------
    def update(self, user: User) -> bool:
        """
        Kullanıcı bilgilerini günceller.

        Args:
            user (User): Güncel bilgileri taşıyan Member veya Librarian nesnesi.

        Returns:
            bool: Güncelleme başarılıysa True.
        """
        query = """
            UPDATE users
            SET name = ?, email = ?, max_book_limit = ?, employee_id = ?
            WHERE id = ?;
        """
        max_book_limit = user.max_book_limit if isinstance(user, Member) else None
        employee_id = user.employee_id if isinstance(user, Librarian) else None

        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (user.name, user.email, max_book_limit, employee_id, user.id)
            )
            return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # CRUD - Delete (Silme)
    # -------------------------------------------------------------------------
    def delete(self, user_id: int) -> bool:
        """
        Kullanıcı kaydını siler.

        Not: Yabancı anahtar (FK) kısıtı sayesinde, aktif ödünç kaydı
        bulunan bir kullanıcı silinmek istendiğinde veritabanı hata fırlatır.

        Args:
            user_id (int): Silinecek kullanıcının ID'si.

        Returns:
            bool: Silme işlemi başarılıysa True.
        """
        query = "DELETE FROM users WHERE id = ?;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id,))
            return cursor.rowcount > 0
