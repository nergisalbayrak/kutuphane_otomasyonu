"""
Ödünç İşlemleri Veri Erişim Katmanı (Borrow Repository)
======================================================
Bu modül, `BorrowRecord` varlığı için veritabanı işlemlerini gerçekleştiren sınıftır.

Mimarideki Rolü:
----------------
1. İlişkilendirme (Association) Yönetimi:
   - Çoktan-çoğa (Many-to-Many) `Member <-> Book` ilişkisinin hareket kayıtlarını
     `borrow_records` tablosunda kalıcı hale getirir.
2. Tarih ve Tip Dönüşümleri (Data Marshaling):
   - SQLite bünyesinde yerel bir `DATETIME` tipi barındırmaz. Bu sınıf, Python `datetime`
     nesnelerini ISO 8601 dizgisine (string) ve okurken de tekrar `datetime` nesnelerine
     dönüştürme sorumluluğunu üstlenir.
3. Katmanlar Arası İşlem İzolasyonu:
   - Ödünç alma ve iade etme durum güncellemelerini (`ACTIVE -> RETURNED`) SQL
     seviyesinde güvenli ve tutarlı biçimde icra eder.
"""

from datetime import datetime
from typing import List, Optional
import sqlite3

from models.borrow_record import BorrowRecord, BorrowStatus
from repositories.database import DatabaseManager


class BorrowRepository:
    """
    Ödünç Kayıtları Deposu (Borrow Repository)
    -----------------------------------------
    Tasarım Deseni: Repository Pattern
    
    `borrow_records` tablosunda yeni ödünç kaydı açma, aktif kayıtları sorgulama
    ve iade kaydını güncelleme işlemlerini yürütür.
    """

    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        BorrowRepository yapıcı metodu.

        OOP Karşılığı: Dependency Injection
        
        Args:
            db_manager (DatabaseManager): Veritabanı bağlantı yöneticisi.
        """
        self._db_manager: DatabaseManager = db_manager

    # -------------------------------------------------------------------------
    # Dönüştürücü Metot (Data Mapper)
    # -------------------------------------------------------------------------
    def _row_to_entity(self, row: sqlite3.Row) -> BorrowRecord:
        """
        SQL Satırını BorrowRecord Nesnesine Dönüştürme
        ----------------------------------------------
        Metin formatında saklanan tarihleri Python `datetime` nesnesine çevirir.
        """
        borrow_date = datetime.strptime(row["borrow_date"], self.DATE_FORMAT)
        return_date = (
            datetime.strptime(row["return_date"], self.DATE_FORMAT)
            if row["return_date"]
            else None
        )

        return BorrowRecord(
            id=row["id"],
            member_id=row["member_id"],
            book_id=row["book_id"],
            borrow_date=borrow_date,
            return_date=return_date,
            status=BorrowStatus(row["status"])
        )

    # -------------------------------------------------------------------------
    # CRUD - Create (Ödünç Kaydı Oluşturma)
    # -------------------------------------------------------------------------
    def add(self, record: BorrowRecord) -> BorrowRecord:
        """
        Veritabanına yeni bir ödünç alma kaydı ekler.

        Args:
            record (BorrowRecord): Kaydedilecek ödünç nesnesi.

        Returns:
            BorrowRecord: Üretilen ID değeri atanmış güncel ödünç kaydı.
        """
        query = """
            INSERT INTO borrow_records (member_id, book_id, borrow_date, return_date, status)
            VALUES (?, ?, ?, ?, ?);
        """
        borrow_date_str = record.borrow_date.strftime(self.DATE_FORMAT)
        return_date_str = (
            record.return_date.strftime(self.DATE_FORMAT) if record.return_date else None
        )

        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (record.member_id, record.book_id, borrow_date_str, return_date_str, record.status.value)
            )
            record.id = cursor.lastrowid
            return record

    # -------------------------------------------------------------------------
    # CRUD - Read (Sorgulama)
    # -------------------------------------------------------------------------
    def get_by_id(self, record_id: int) -> Optional[BorrowRecord]:
        """
        ID numarasına göre ödünç kaydını getirir.

        Args:
            record_id (int): Aranacak kayıt ID'si.

        Returns:
            Optional[BorrowRecord]: Eşleşen kayıt veya `None`.
        """
        query = "SELECT * FROM borrow_records WHERE id = ?;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (record_id,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    def get_all(self) -> List[BorrowRecord]:
        """
        Sistemdeki tüm ödünç kayıtlarını (geçmiş ve aktif) listeler.

        Returns:
            List[BorrowRecord]: Tüm ödünç hareketleri listesi.
        """
        query = "SELECT * FROM borrow_records ORDER BY id DESC;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]

    def get_active_by_member(self, member_id: int) -> List[BorrowRecord]:
        """
        Belirli bir üyenin henüz iade etmediği (ACTIVE) ödünç kayıtlarını listeler.

        Katmanlı Mimari Rolü:
        İş Mantığı Katmanı (Service), üyenin kitap limitini aşıp aşmadığını
        denetlerken bu sorgu sonucundan faydalanır.

        Args:
            member_id (int): Üyenin ID numarası.

        Returns:
            List[BorrowRecord]: Üyeye ait aktif ödünç kayıtları.
        """
        query = """
            SELECT * FROM borrow_records
            WHERE member_id = ? AND status = 'ACTIVE'
            ORDER BY borrow_date ASC;
        """
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (member_id,))
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]

    def get_active_by_book(self, book_id: int) -> Optional[BorrowRecord]:
        """
        Belirli bir kitabın şu anki aktif ödünç kaydını bulur.

        Args:
            book_id (int): Kitabın ID numarası.

        Returns:
            Optional[BorrowRecord]: Kitap ödünçteyse aktif kayıt, raftaysa `None`.
        """
        query = """
            SELECT * FROM borrow_records
            WHERE book_id = ? AND status = 'ACTIVE'
            LIMIT 1;
        """
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (book_id,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    # -------------------------------------------------------------------------
    # CRUD - Update (Güncelleme / İade Tamamlama)
    # -------------------------------------------------------------------------
    def update(self, record: BorrowRecord) -> bool:
        """
        Ödünç kaydını günceller (Özellikle iade tarihi ve durum değişiminde kullanılır).

        Args:
            record (BorrowRecord): Güncellenecek kayıt nesnesi.

        Returns:
            bool: Güncelleme başarılıysa True.
        """
        query = """
            UPDATE borrow_records
            SET return_date = ?, status = ?
            WHERE id = ?;
        """
        return_date_str = (
            record.return_date.strftime(self.DATE_FORMAT) if record.return_date else None
        )

        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (return_date_str, record.status.value, record.id))
            return cursor.rowcount > 0
