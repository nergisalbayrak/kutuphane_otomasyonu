"""
Kitap İş Mantığı Katmanı (Book Service)
=======================================
Bu modül, N-Tier (Katmanlı) Mimarinin "Business Logic Layer (BLL)" yani
İş Mantığı Katmanında yer alır.

Mimari Soru: "İş Kuralları Neden Veri Katmanından (Repository) Ayrı Yazılır?"
----------------------------------------------------------------------------
1. Tek Sorumluluk Prensibi (Single Responsibility Principle - SRP):
   - Repository katmanının tek görevi veriyi veritabanına yazmak ve okumaktır (SQL işlemleri).
   - Service katmanının görevi ise "kuralları koymaktır" (Örn: ISBN benzersiz mi?
     Ödünçte olan bir kitap silinebilir mi?).
2. Bakım Kolaylığı ve Değişime Açıklık:
   - Yarın veritabanı SQLite yerine PostgreSQL veya MongoDB yapılsa bile, iş kuralları
     (Service katmanı) tek bir satır dahi değişmeden aynı kalır.
3. Yeniden Kullanılabilirlik (Reusability):
   - Aynı `BookService` mantığı ister Konsol (CLI), ister Masaüstü (Tkinter/Qt),
     ister Web API (FastAPI/Flask) üzerinden doğrudan kullanılabilir.
"""

from typing import List, Optional

from models.book import Book, BookStatus
from repositories.book_repository import BookRepository


class BookService:
    """
    Kitap İş Mantığı Yöneticisi (Book Service)
    -----------------------------------------
    Tasarım İlkesi: Service Layer Pattern & Dependency Injection
    
    Kitap ekleme, arama, güncelleme ve silme süreçlerindeki iş kurallarını (business rules)
    denetler ve onaylanan işlemleri `BookRepository` aracılığıyla veritabanına iletir.
    """

    def __init__(self, book_repository: BookRepository) -> None:
        """
        BookService yapıcı metodu.

        OOP Karşılığı: Dependency Injection (Bağımlılık Enjeksiyonu)
        Servis sınıfı veritabanına doğrudan bağlanmaz; veri erişim işini
        `BookRepository` arayüzüne delege eder (Gevşek Bağlılık - Loose Coupling).

        Args:
            book_repository (BookRepository): Kitap veri erişim deposu.
        """
        self._book_repository: BookRepository = book_repository

    # -------------------------------------------------------------------------
    # İş Kuralı: Yeni Kitap Ekleme ve ISBN Doğrulaması
    # -------------------------------------------------------------------------
    def add_book(self, title: str, author: str, isbn: str, category: str = "Genel") -> Book:
        """
        Sisteme yeni bir kitap ekler.

        İş Kuralları (Business Rules):
        1. Başlık, yazar ve ISBN alanları boş bırakılamaz.
        2. ISBN sistemde tamamen BENZERSİZ (Unique) olmalıdır. Aynı ISBN numarasıyla
           ikinci bir kitap kaydedilemez.
        3. Yeni eklenen kitabın başlangıç durumu mutlaka 'AVAILABLE' (Rafta) olmalıdır.

        Args:
            title (str): Kitabın adı.
            author (str): Kitabın yazarı.
            isbn (str): Uluslararası standart kitap numarası.
            category (str): Kitabın ait olduğu kategori (Varsayılan: 'Genel').

        Returns:
            Book: Başarıyla kaydedilen ve veritabanı ID'si atanmış kitap nesnesi.

        Raises:
            ValueError: Zorunlu alanlar boşsa veya ISBN zaten kayıtlıysa.
        """
        # Kural 1: Girdi doğrulama
        clean_title = title.strip() if title else ""
        clean_author = author.strip() if author else ""
        clean_isbn = isbn.strip() if isbn else ""
        clean_category = category.strip() if category else "Genel"

        if not clean_title:
            raise ValueError("İş Kuralı İhlali: Kitap başlığı boş olamaz.")
        if not clean_author:
            raise ValueError("İş Kuralı İhlali: Yazar bilgisi boş olamaz.")
        if not clean_isbn:
            raise ValueError("İş Kuralı İhlali: ISBN numarası boş olamaz.")

        # Kural 2: ISBN Benzersizlik Kontrolü
        existing_book = self._book_repository.get_by_isbn(clean_isbn)
        if existing_book is not None:
            raise ValueError(
                f"İş Kuralı İhlali: '{clean_isbn}' ISBN numarasına sahip kitap "
                f"sistemde zaten mevcut ('{existing_book.title}')."
            )

        # Kural 3: Yeni kitap 'AVAILABLE' durumuyla oluşturulur
        new_book = Book(
            id=0,  # Veritabanı otomatik atayacak
            title=clean_title,
            author=clean_author,
            isbn=clean_isbn,
            category=clean_category,
            status=BookStatus.AVAILABLE
        )

        return self._book_repository.add(new_book)

    # -------------------------------------------------------------------------
    # İş Kuralı: Kitap Silme ve Durum Kontrolü
    # -------------------------------------------------------------------------
    def delete_book(self, book_id: int) -> bool:
        """
        Belirtilen ID'deki kitabı sistemden siler.

        İş Kuralları (Business Rules):
        1. Kitap sistemde mevcut olmalıdır.
        2. 'BORROWED' (Ödünçte) olan bir kitap ASLA silinemez! Önce iade edilmelidir.

        Args:
            book_id (int): Silinmek istenen kitabın kimlik numarası.

        Returns:
            bool: Silme işlemi başarılıysa True.

        Raises:
            ValueError: Kitap bulunamazsa veya ödünçte ise.
        """
        book = self.get_book_by_id(book_id)

        # Kural 2: Ödünçteki kitap silinemez kuralı
        if book.status == BookStatus.BORROWED:
            raise ValueError(
                f"İş Kuralı İhlali: ID #{book_id} ('{book.title}') şu anda bir üyede ödünçtedir. "
                "İade işlemi gerçekleşmeden kitap sistemden silinemez!"
            )

        return self._book_repository.delete(book_id)

    # -------------------------------------------------------------------------
    # Kitap Güncelleme ve Arama
    # -------------------------------------------------------------------------
    def update_book(
        self,
        book_id: int,
        title: str,
        author: str,
        isbn: str,
        category: str = "Genel"
    ) -> Book:
        """
        Var olan bir kitabın bilgilerini günceller.

        İş Kuralları (Business Rules):
        1. Güncellenen ISBN başka bir kitaba ait olmamalıdır.
        """
        book = self.get_book_by_id(book_id)

        clean_isbn = isbn.strip()
        if clean_isbn != book.isbn:
            conflict = self._book_repository.get_by_isbn(clean_isbn)
            if conflict and conflict.id != book_id:
                raise ValueError(f"İş Kuralı İhlali: '{clean_isbn}' ISBN numarası başka bir kitaba ait.")

        book.title = title
        book.author = author
        book.isbn = clean_isbn
        book.category = category.strip() if category else "Genel"

        self._book_repository.update(book)
        return book

    def get_book_by_id(self, book_id: int) -> Book:
        """
        ID ile kitap sorgular, bulunamazsa hata fırlatır.
        """
        book = self._book_repository.get_by_id(book_id)
        if book is None:
            raise ValueError(f"İş Kuralı İhlali: ID #{book_id} numaralı kitap bulunamadı.")
        return book

    def search_books(self, search_term: str) -> List[Book]:
        """
        Başlık veya yazar adına göre arama yapar.
        """
        if not search_term or not search_term.strip():
            return self._book_repository.get_all()
        return self._book_repository.search(search_term.strip())

    def get_all_books(self) -> List[Book]:
        """
        Sistemdeki tüm kitapları listeler.
        """
        return self._book_repository.get_all()
