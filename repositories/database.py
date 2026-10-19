"""
Veritabanı Yöneticisi (Database Manager)
========================================
Bu modül, N-Tier (Katmanlı) Mimarinin "Data Access Layer (DAL)" yani
Veri Erişim Katmanının temel yapı taşıdır.

Mimarideki Rolü:
----------------
1. Veri Kaynağının Soyutlanması: Uygulamanın diğer katmanları (İş Mantığı/Service ve Sunum/UI),
   veritabanı motorunun (SQLite, PostgreSQL vb.) düşük seviyeli bağlantı ayrıntılarını bilmez.
2. Deployment Diagram Açısından Önemi: SQLite, sunucu gerektirmeyen (serverless/embedded) bir
   dosya tabanlı veritabanıdır. Dağıtım diyagramında uygulamanın çalıştığı istemci/sunucu
   düğümünde yerel bir dosya bileşeni (.db) olarak modellenir.
3. Veri Bütünlüğü (Data Integrity): İlişkisel tablolar arasında Foreign Key (Yabancı Anahtar)
   kısıtlamalarını aktif hale getirerek yetkisiz veya tutarsız veri girişini engeller.
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Generator, Optional


class DatabaseManager:
    """
    Veritabanı Bağlantı ve Tablo Yönetim Sınıfı
    -------------------------------------------
    Tasarım Deseni: Context Manager & Singleton Benzeri Merkezi Yapı
    
    SQLite veritabanı ile bağlantı kurma, kapatma, hata durumunda geri alma (rollback)
    ve tabloların DDL (Data Definition Language) şemalarını oluşturma işlemlerini yönetir.
    """

    DEFAULT_DB_NAME: str = "kutuphane.db"

    def __init__(self, db_path: Optional[str] = None) -> None:
        """
        DatabaseManager yapıcı metodu.

        Args:
            db_path (Optional[str]): Veritabanı dosyasının yolu. Belirtilmezse
                                     varsayılan olarak kök dizindeki 'kutuphane.db' kullanılır.
        """
        self._db_path: str = db_path if db_path else self.DEFAULT_DB_NAME

    @property
    def db_path(self) -> str:
        """Kullanılan veritabanı dosyasının yolunu döndürür."""
        return self._db_path

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Veritabanı Bağlantı Bağlamı (Context Manager)
        --------------------------------------------
        OOP / Mimari Karşılığı: Resource Management (Kaynak Yönetimi)
        
        Python `with` bloğu ile kullanılır. Bağlantıyı açar, sorguların sözlük
        gibi erişilebilmesi için `row_factory = sqlite3.Row` ayarını yapar,
        Foreign Key desteğini açar, işlem başarılıysa `commit`, hata varsa `rollback`
        yapar ve bağlantıyı daima kapatır.
        
        Yields:
            sqlite3.Connection: Aktif SQLite veritabanı bağlantısı.
        """
        conn: sqlite3.Connection = sqlite3.connect(self._db_path)
        # Sütun isimlerine sözlük gibi erişebilmek için (row['title'] vb.)
        conn.row_factory = sqlite3.Row
        # SQLite varsayılan olarak yabancı anahtarları denetlemez; zorunlu kılmak için açıyoruz:
        conn.execute("PRAGMA foreign_keys = ON;")
        
        try:
            yield conn
            conn.commit()  # Hata çıkmazsa değişiklikleri kalıcı kaydet
        except Exception:
            conn.rollback()  # Hata oluşursa yapılan işlemleri geri al
            raise
        finally:
            conn.close()  # Kaynağı serbest bırakarak sızıntıyı önle

    def initialize_tables(self) -> None:
        """
        Veritabanı Tablo Şemalarını Oluşturma (DDL)
        -------------------------------------------
        Katmanlı mimaride uygulamanın ilk açılışında çalıştırılarak
        gerekli ilişkisel tabloları (`users`, `books`, `borrow_records`)
        yoksa otomatik oluşturur.
        
        Tasarım İlkesi: Single Table Inheritance (Tek Tablo Kalıtımı)
        `User`, `Member` ve `Librarian` nesneleri veritabanında `users` tablosunda
        `role` ayracı (discriminator) kullanılarak modellenmiştir.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # -------------------------------------------------------------
            # 1. KATEGORİLER TABLOSU (categories)
            # Kitapların sınıflandırılması için kullanılan kategori tablosudur.
            # -------------------------------------------------------------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                );
            """)

            # -------------------------------------------------------------
            # 2. KULLANICILAR TABLOSU (users)
            # OOP Kalıtım Eşlemesi: Single Table Inheritance
            # Hem Member hem Librarian alanları bu tabloda tutulur.
            # -------------------------------------------------------------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL,                -- 'MEMBER' veya 'LIBRARIAN'
                    max_book_limit INTEGER DEFAULT 3,  -- Üyelere özel alan
                    employee_id TEXT                   -- Kütüphaneciye özel sicil no
                );
            """)

            # -------------------------------------------------------------
            # 3. KİTAPLAR TABLOSU (books)
            # Book nesnesinin veritabanındaki izdüşümüdür.
            # -------------------------------------------------------------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    isbn TEXT UNIQUE NOT NULL,
                    category TEXT DEFAULT 'Genel',
                    status TEXT NOT NULL DEFAULT 'AVAILABLE' -- 'AVAILABLE' veya 'BORROWED'
                );
            """)

            # Eski veritabanı şeması için sütun kontrolü (Schema Migration)
            cursor.execute("PRAGMA table_info(books);")
            existing_columns = [col["name"] for col in cursor.fetchall()]
            if "category" not in existing_columns:
                cursor.execute("ALTER TABLE books ADD COLUMN category TEXT DEFAULT 'Genel';")

            # -------------------------------------------------------------
            # 4. ÖDÜNÇ KAYITLARI TABLOSU (borrow_records)
            # OOP İlişkilendirme (Association): Member <-> Book çoktan-çoğa
            # ilişkisinin işlem (transaction) tablosudur.
            # -------------------------------------------------------------
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS borrow_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    member_id INTEGER NOT NULL,
                    book_id INTEGER NOT NULL,
                    borrow_date TEXT NOT NULL,          -- ISO Formatında tarih-saat
                    return_date TEXT,                  -- İade edilmediyse NULL
                    status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE' veya 'RETURNED'
                    FOREIGN KEY (member_id) REFERENCES users (id) ON DELETE RESTRICT,
                    FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE RESTRICT
                );
            """)

    def seed_initial_data(self) -> bool:
        """
        Veritabanı Başlangıç Verilerini Yükleme (Seed Data)
        ---------------------------------------------------
        Katmanlı Mimari ve Test Prensibi:
        Proje ilk kez çalıştırıldığında veya veritabanı boşken sunum ve testlerin
        hemen yapılabilmesi için başlangıç verilerini sisteme aktarır.
        
        İdempotent Tasarım (Mükerrerlik Koruması):
        Eğer veritabanında zaten kayıt varsa (kullanıcı veya kitap mevcutsa)
        tekrar ekleme yapmaz, veri bütünlüğünü korur.

        Eklenen Örnek Veriler:
        1. Kategoriler : "Edebiyat", "Bilim Kurgu", "Tarih"
        2. Kitaplar    : 
           - "Nutuk" (Mustafa Kemal Atatürk, ISBN: 9789751600010, Kategori: Tarih)
           - "1984" (George Orwell, ISBN: 9789750718533, Kategori: Bilim Kurgu)
           - "Fahreneit 451" (Ray Bradbury, ISBN: 9789756902202, Kategori: Bilim Kurgu)
        3. Üyeler      :
           - "Ahmet Yılmaz" (Öğrenci Üye, ID: 1, Limit: 3)
           - "Ayşe Kaya" (Kütüphaneci / Admin, ID: 2, Sicil No: LIB-001)

        Returns:
            bool: Veriler yüklendiyse True, veritabanında zaten veri varsa False.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Veritabanında halihazırda veri olup olmadığını denetle
            cursor.execute("SELECT COUNT(*) FROM books;")
            book_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]

            # Eğer kitap veya kullanıcı zaten varsa tekrar ekleme yapma!
            if book_count > 0 or user_count > 0:
                return False

            # -------------------------------------------------------------
            # 1. Örnek Kategoriler Ekleme
            # -------------------------------------------------------------
            categories = [("Edebiyat",), ("Bilim Kurgu",), ("Tarih",)]
            cursor.executemany(
                "INSERT OR IGNORE INTO categories (name) VALUES (?);",
                categories
            )

            # -------------------------------------------------------------
            # 2. Örnek Kitaplar Ekleme
            # -------------------------------------------------------------
            sample_books = [
                ("Nutuk", "Mustafa Kemal Atatürk", "9789751600010", "Tarih", "AVAILABLE"),
                ("1984", "George Orwell", "9789750718533", "Bilim Kurgu", "AVAILABLE"),
                ("Fahreneit 451", "Ray Bradbury", "9789756902202", "Bilim Kurgu", "AVAILABLE")
            ]
            cursor.executemany(
                """
                INSERT OR IGNORE INTO books (title, author, isbn, category, status)
                VALUES (?, ?, ?, ?, ?);
                """,
                sample_books
            )

            # -------------------------------------------------------------
            # 3. Örnek Kullanıcılar (Üye ve Kütüphaneci) Ekleme
            # -------------------------------------------------------------
            # Ahmet Yılmaz (Öğrenci Üye, ID: 1, Limit: 3)
            cursor.execute(
                """
                INSERT OR IGNORE INTO users (id, name, email, role, max_book_limit, employee_id)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (1, "Ahmet Yılmaz", "ahmet.yilmaz@kutuphane.com", "MEMBER", 3, None)
            )

            # Ayşe Kaya (Kütüphaneci / Admin, ID: 2, Sicil No: LIB-001)
            cursor.execute(
                """
                INSERT OR IGNORE INTO users (id, name, email, role, max_book_limit, employee_id)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (2, "Ayşe Kaya", "ayse.kaya@kutuphane.com", "LIBRARIAN", None, "LIB-001")
            )

            print("\n" + "=" * 70)
            print("  [BİLGİ] Veritabanı boş olduğundan örnek veriler (Seed Data) yüklendi:")
            print("  * Örnek Kategoriler : Edebiyat, Bilim Kurgu, Tarih")
            print("  * Örnek Kitaplar    : Nutuk (Tarih), 1984 (Bilim Kurgu), Fahreneit 451 (Bilim Kurgu)")
            print("  * Örnek Üyeler      : Ahmet Yılmaz (Öğrenci Üye - ID: 1), Ayşe Kaya (Kütüphaneci - ID: 2)")
            print("=" * 70 + "\n")
            return True
