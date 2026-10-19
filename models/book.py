"""
Kitap Modeli (Book Model)
=========================
Bu modül, kütüphane otomasyon sistemindeki kitap varlığını (Book Entity) ve
kitap durumunu (BookStatus Enum) tanımlar.
N-Tier (Katmanlı) Mimarinin "Domain / Model" katmanında yer alır.

OOP Prensipleri:
----------------
1. Encapsulation (Kapsülleme): Kitabın temel nitelikleri (`_id`, `_title`, `_author`,
   `_isbn`, `_status`) dış dünyadan korunur ve `@property` ile kontrollü erişim sağlanır.
   Kitap durumu doğrudan rastgele değiştirilmek yerine iş kurallarına dayalı metotlarla
   (`mark_as_borrowed`, `mark_as_available`) güncellenir.
2. State Pattern / Enum Kullanımı: Kitabın durumları (`AVAILABLE`, `BORROWED`)
   `Enum` ile sınırlandırılarak tip güvenliği (Type Safety) garanti altına alınmıştır.
"""

from enum import Enum
from typing import Optional


class BookStatus(str, Enum):
    """
    Kitap Durum Sabitleri (Book Status Enum)
    ----------------------------------------
    Kitabın kütüphanedeki anlık ödünç durumunu ifade eder.
    Hatalı durum girişlerini engellemek için Enum olarak tanımlanmıştır.
    """
    AVAILABLE = "AVAILABLE"  # Kitap kütüphanede, ödünç alınabilir durumda
    BORROWED = "BORROWED"    # Kitap bir üye tarafından ödünç alınmış durumda


class Book:
    """
    Kitap Varlık Sınıfı (Book Entity)
    ---------------------------------
    Tasarım İlkesi: Kapsülleme (Encapsulation) & Bilgi Gizleme (Information Hiding)
    
    Kütüphanede bulunan bir kitabı temsil eder. Kitabın kimlik, başlık, yazar,
    ISBN ve ödünç durumu bilgilerini yönetir.
    
    Özellikler (Attributes):
        id (int): Kitabın sistemdeki benzersiz kimlik numarası.
        title (str): Kitabın adı/başlığı.
        author (str): Kitabın yazarı.
        isbn (str): Uluslararası Standart Kitap Numarası (ISBN).
        category (str): Kitabın ait olduğu kategori (örn: Edebiyat, Bilim Kurgu, Tarih).
        status (BookStatus): Kitabın mevcut durumu (Varsayılan: AVAILABLE).
    """

    def __init__(
        self,
        id: int,
        title: str,
        author: str,
        isbn: str,
        category: str = "Genel",
        status: BookStatus = BookStatus.AVAILABLE
    ) -> None:
        """
        Book sınıfı yapıcı (constructor) metodu.

        OOP Karşılığı: Encapsulation (Kapsülleme)
        Nitelikler `_` (protected) ile kapsüllenerek doğrudan dış müdahaleler
        engellenmiştir.
        """
        self._id: int = id
        self._title: str = title
        self._author: str = author
        self._isbn: str = isbn
        self._category: str = category.strip() if category else "Genel"
        # Gelen status str formatında ise Enum'a dönüştürülür
        self._status: BookStatus = BookStatus(status) if isinstance(status, str) else status

    # -------------------------------------------------------------------------
    # Kapsülleme (Encapsulation) - Getter ve Setter Özellikleri
    # -------------------------------------------------------------------------
    @property
    def id(self) -> int:
        """Kitap ID'sini döndürür."""
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        """Kitap ID'sini günceller."""
        if value <= 0:
            raise ValueError("Kitap ID'si pozitif bir tam sayı olmalıdır.")
        self._id = value

    @property
    def title(self) -> str:
        """Kitap başlığını döndürür."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Kitap başlığını günceller (Boş olamaz kontrolü içerir)."""
        if not value or not value.strip():
            raise ValueError("Kitap adı boş bırakılamaz.")
        self._title = value.strip()

    @property
    def author(self) -> str:
        """Kitap yazarını döndürür."""
        return self._author

    @author.setter
    def author(self, value: str) -> None:
        """Kitap yazarını günceller (Boş olamaz kontrolü içerir)."""
        if not value or not value.strip():
            raise ValueError("Yazar bilgisi boş bırakılamaz.")
        self._author = value.strip()

    @property
    def isbn(self) -> str:
        """Kitap ISBN numarasını döndürür."""
        return self._isbn

    @isbn.setter
    def isbn(self, value: str) -> None:
        """Kitap ISBN numarasını günceller."""
        if not value or not value.strip():
            raise ValueError("ISBN numarası boş bırakılamaz.")
        self._isbn = value.strip()

    @property
    def category(self) -> str:
        """Kitabın ait olduğu kategoriyi döndürür."""
        return self._category

    @category.setter
    def category(self, value: str) -> None:
        """Kitap kategorisini günceller."""
        self._category = value.strip() if value and value.strip() else "Genel"

    @property
    def status(self) -> BookStatus:
        """Kitabın anlık durumunu döndürür."""
        return self._status

    @status.setter
    def status(self, value: BookStatus) -> None:
        """Kitabın anlık durumunu günceller."""
        if not isinstance(value, BookStatus):
            try:
                value = BookStatus(value)
            except ValueError:
                raise ValueError(f"Geçersiz kitap durumu: {value}. "
                                 f"Beklenen: {[s.value for s in BookStatus]}")
        self._status = value

    # -------------------------------------------------------------------------
    # Durum ve İş Mantığı Metotları (Business / State Methods)
    # -------------------------------------------------------------------------
    def is_available(self) -> bool:
        """
        Kitabın ödünç alınabilir durumda olup olmadığını doğrular.
        
        Returns:
            bool: Durum AVAILABLE ise True, değilse False.
        """
        return self._status == BookStatus.AVAILABLE

    def mark_as_borrowed(self) -> None:
        """
        Kitabın durumunu ödünç verilmiş (BORROWED) olarak işaretler.
        
        Raises:
            ValueError: Kitap zaten ödünç verilmişse işlem reddedilir.
        """
        if not self.is_available():
            raise ValueError(f"'{self._title}' isimli kitap zaten ödünç verilmiş durumda.")
        self._status = BookStatus.BORROWED

    def mark_as_available(self) -> None:
        """
        Kitap iade edildiğinde durumunu tekrar raflarda (AVAILABLE) olarak işaretler.
        """
        self._status = BookStatus.AVAILABLE

    # -------------------------------------------------------------------------
    # String Temsilleri (Representation)
    # -------------------------------------------------------------------------
    def __str__(self) -> str:
        """Kullanıcı dostu metin temsili."""
        return f"Kitap #{self._id}: '{self._title}' - {self._author} [{self._category}] [ISBN: {self._isbn}] ({self._status.value})"

    def __repr__(self) -> str:
        """Geliştirici dostu nesne temsili."""
        return (
            f"<Book(id={self._id}, title='{self._title}', author='{self._author}', "
            f"category='{self._category}', isbn='{self._isbn}', status='{self._status.value}')>"
        )
