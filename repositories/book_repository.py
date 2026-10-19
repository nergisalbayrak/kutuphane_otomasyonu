"""
Kitap Veri Erişim Katmanı (Book Repository)
===========================================
Bu modül, `Book` modeli için veritabanı CRUD (Create, Read, Update, Delete)
işlemlerini yürüten sınıftır.

Mimarideki Rolü:
----------------
1. Repository Pattern (Depo Tasarım Deseni):
   - İş Mantığı Katmanı (Service Layer) doğrudan SQL sorguları yazmaz.
   - Bu sınıf, veritabanı sorgularını soyutlayarak üst katmanlara yalnızca
     `Book` nesneleri ile çalışma imkanı tanır (Separation of Concerns).
2. Data Mapper / ORM Rolü:
   - Veritabanından dönen ham SQL satırlarını (`sqlite3.Row`) nesne yönelimli
     `Book` nesnelerine dönüştürür (`_row_to_entity`).
3. SQL Enjeksiyonuna Karşı Güvenlik:
   - Tüm sorgular parametrik (`?` yer tutucuları ile) çalıştırılarak
     güvenli veri erişimi sağlanır.
"""

from typing import List, Optional
import sqlite3

from models.book import Book, BookStatus
from repositories.database import DatabaseManager


class BookRepository:
    """
    Kitap Deposu (Book Repository)
    ------------------------------
    Tasarım Deseni: Repository Pattern
    
    `books` tablosundaki verileri sorgulamak, eklemek, güncellemek ve silmekten
    sorumlu sınıftır.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        BookRepository yapıcı metodu.

        OOP Karşılığı: Dependency Injection (Bağımlılık Enjeksiyonu)
        Veritabanı yöneticisi dışarıdan parametre olarak alınarak
        sınıflar arası sıkı bağ (tight coupling) önlenir.
        
        Args:
            db_manager (DatabaseManager): Veritabanı bağlantı yöneticisi.
        """
        self._db_manager: DatabaseManager = db_manager

    # -------------------------------------------------------------------------
    # Yardımcı Dönüştürücü Metot (Data Mapper)
    # -------------------------------------------------------------------------
    def _row_to_entity(self, row: sqlite3.Row) -> Book:
        """
        SQL Satırını Book Nesnesine Dönüştürme
        ---------------------------------------
        OOP / Mimari Karşılığı: Object-Relational Mapping (ORM)
        
        İlişkisel veritabanı satırını nesne yönelimli `Book` varlığına (Entity) çevirir.
        """
        category_val = row["category"] if "category" in row.keys() else "Genel"
        return Book(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            isbn=row["isbn"],
            category=category_val or "Genel",
            status=BookStatus(row["status"])
        )

    # -------------------------------------------------------------------------
    # CRUD - Create (Oluşturma / Ekleme)
    # -------------------------------------------------------------------------
    def add(self, book: Book) -> Book:
        """
        Veritabanına yeni bir kitap kaydı ekler.

        Katmanlı Mimari Rolü:
        Parametre olarak üst katmandan gelen `Book` nesnesini alır,
        SQL `INSERT INTO` komutunu çalıştırır ve veritabanı tarafından
        üretilen otomatik `id` değerini nesneye atayarak geri döndürür.

        Args:
            book (Book): Eklenecek kitap nesnesi.

        Returns:
            Book: Veritabanı ID'si atanmış güncel kitap nesnesi.
        """
        query = """
            INSERT INTO books (title, author, isbn, category, status)
            VALUES (?, ?, ?, ?, ?);
        """
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (book.title, book.author, book.isbn, book.category, book.status.value)
            )
            # Otomatik üretilen birincil anahtar (Primary Key) atanır
            book.id = cursor.lastrowid
            return book

    # -------------------------------------------------------------------------
    # CRUD - Read (Okuma / Sorgulama)
    # -------------------------------------------------------------------------
    def get_by_id(self, book_id: int) -> Optional[Book]:
        """
        ID numarasına göre tek bir kitap kaydı getirir.

        Args:
            book_id (int): Aranacak kitabın ID'si.

        Returns:
            Optional[Book]: Bulunursa `Book` nesnesi, bulunamazsa `None`.
        """
        query = "SELECT * FROM books WHERE id = ?;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (book_id,))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    def get_by_isbn(self, isbn: str) -> Optional[Book]:
        """
        ISBN numarasına göre kitap arar (Benzersizlik kontrolü için kullanılır).

        Args:
            isbn (str): Aranacak ISBN değeri.

        Returns:
            Optional[Book]: Eşleşen `Book` nesnesi veya `None`.
        """
        query = "SELECT * FROM books WHERE isbn = ?;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (isbn.strip(),))
            row = cursor.fetchone()
            return self._row_to_entity(row) if row else None

    def get_all(self) -> List[Book]:
        """
        Sistemde kayıtlı olan tüm kitapları listeler.

        Returns:
            List[Book]: Kitap nesneleri listesi.
        """
        query = "SELECT * FROM books ORDER BY id ASC;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]

    def search(self, search_term: str) -> List[Book]:
        """
        Başlık, yazar veya kategoriye göre esnek arama yapar (SQL LIKE sorgusu).

        Katmanlı Mimari Rolü:
        Kullanıcı arayüzünden gelen arama terimini SQL seviyesinde filtreleyerek
        sunum katmanına yalnızca eşleşen `Book` nesnelerini iletir.

        Args:
            search_term (str): Arama kelimesi (Kitap başlığı, yazar veya kategori).

        Returns:
            List[Book]: Eşleşen kitapların listesi.
        """
        query = """
            SELECT * FROM books
            WHERE title LIKE ? OR author LIKE ? OR category LIKE ?
            ORDER BY title ASC;
        """
        param = f"%{search_term.strip()}%"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (param, param, param))
            rows = cursor.fetchall()
            return [self._row_to_entity(row) for row in rows]

    # -------------------------------------------------------------------------
    # CRUD - Update (Güncelleme)
    # -------------------------------------------------------------------------
    def update(self, book: Book) -> bool:
        """
        Var olan bir kitabın bilgilerini ve durumunu günceller.

        Args:
            book (Book): Güncel bilgileri içeren kitap nesnesi.

        Returns:
            bool: Güncelleme başarılıysa (en az bir satır etkilendiyse) True.
        """
        query = """
            UPDATE books
            SET title = ?, author = ?, isbn = ?, category = ?, status = ?
            WHERE id = ?;
        """
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                query,
                (book.title, book.author, book.isbn, book.category, book.status.value, book.id)
            )
            return cursor.rowcount > 0

    # -------------------------------------------------------------------------
    # CRUD - Delete (Silme)
    # -------------------------------------------------------------------------
    def delete(self, book_id: int) -> bool:
        """
        Belirtilen ID'ye sahip kitabı veritabanından siler.

        Args:
            book_id (int): Silinecek kitabın ID'si.

        Returns:
            bool: Silme işlemi başarılıysa True, satır bulunamadıysa False.
        """
        query = "DELETE FROM books WHERE id = ?;"
        with self._db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (book_id,))
            return cursor.rowcount > 0
