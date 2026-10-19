"""
Ödünç Alma Kaydı Modeli (Borrow Record Model)
==============================================
Bu modül, kütüphane otomasyon sistemindeki ödünç alma işlemlerini temsil eden
ilişkisel varlığı (Association / Transaction Entity) tanımlar.
N-Tier (Katmanlı) Mimarinin "Domain / Model" katmanında yer alır.

OOP Prensipleri:
----------------
1. Association (İlişkilendirme): `BorrowRecord`, `Member` ve `Book` sınıfları arasındaki
   ilişkiyi (Member borrows Book) `member_id` ve `book_id` referansları üzerinden kurar.
2. Encapsulation (Kapsülleme): İşlem kayıtlarının durumları ve tarihleri doğrudan
   değiştirilmek yerine `close_record()` gibi anlamlı metotlarla yönetilir.
3. Type Safety: Tarih alanları `datetime` modülü ile, durumlar ise `BorrowStatus`
   Enum yapısı ile tip korumalı hale getirilmiştir.
"""

from datetime import datetime
from enum import Enum
from typing import Optional


class BorrowStatus(str, Enum):
    """
    Ödünç Kaydı Durum Sabitleri (Borrow Status Enum)
    ------------------------------------------------
    Ödünç alma işleminin mevcut aşamasını tanımlar.
    """
    ACTIVE = "ACTIVE"        # Kitap hala üyede, iade edilmedi
    RETURNED = "RETURNED"    # Kitap başarıyla kütüphaneye teslim edildi


class BorrowRecord:
    """
    Ödünç Alma Kayıt Sınıfı (Borrow Record Entity)
    ----------------------------------------------
    Tasarım İlkesi: Kapsülleme (Encapsulation) & İlişkilendirme (Association)
    
    Bir üyenin belirli bir kitabı hangi tarihte aldığını, ne zaman iade ettiğini
    ve kaydın güncel durumunu takip eden modeldir.
    
    Özellikler (Attributes):
        id (int): Ödünç işleminin benzersiz işlem numarası.
        member_id (int): Kitabı ödünç alan üyenin ID'si (Foreign Key referansı).
        book_id (int): Ödünç alınan kitabın ID'si (Foreign Key referansı).
        borrow_date (datetime): Kitabın teslim alındığı tarih ve saat.
        return_date (Optional[datetime]): Kitabın iade edildiği tarih ve saat (İade edilmediyse None).
        status (BorrowStatus): Kaydın durumu (ACTIVE veya RETURNED).
    """

    def __init__(
        self,
        id: int,
        member_id: int,
        book_id: int,
        borrow_date: Optional[datetime] = None,
        return_date: Optional[datetime] = None,
        status: BorrowStatus = BorrowStatus.ACTIVE
    ) -> None:
        """
        BorrowRecord sınıfı yapıcı metodu.

        OOP Karşılığı: Encapsulation (Kapsülleme)
        Tüm alanlar `_` (protected) ile gizlenmiştir.
        """
        self._id: int = id
        self._member_id: int = member_id
        self._book_id: int = book_id
        # Tarih belirtilmediyse anlık zaman varsayılan alınır
        self._borrow_date: datetime = borrow_date if borrow_date is not None else datetime.now()
        self._return_date: Optional[datetime] = return_date
        # Durum string gelirse Enum'a dönüştürülür
        self._status: BorrowStatus = BorrowStatus(status) if isinstance(status, str) else status

    # -------------------------------------------------------------------------
    # Kapsülleme (Encapsulation) - Getter ve Setter Özellikleri
    # -------------------------------------------------------------------------
    @property
    def id(self) -> int:
        """Ödünç işlem ID'sini döndürür."""
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        """Ödünç işlem ID'sini günceller."""
        if value <= 0:
            raise ValueError("Kayıt ID'si pozitif bir tam sayı olmalıdır.")
        self._id = value

    @property
    def member_id(self) -> int:
        """Kitabı alan üyenin ID'sini döndürür."""
        return self._member_id

    @member_id.setter
    def member_id(self, value: int) -> None:
        """Üye ID'sini günceller."""
        if value <= 0:
            raise ValueError("Geçerli bir üye ID'si girilmelidir.")
        self._member_id = value

    @property
    def book_id(self) -> int:
        """Ödünç alınan kitabın ID'sini döndürür."""
        return self._book_id

    @book_id.setter
    def book_id(self, value: int) -> None:
        """Kitap ID'sini günceller."""
        if value <= 0:
            raise ValueError("Geçerli bir kitap ID'si girilmelidir.")
        self._book_id = value

    @property
    def borrow_date(self) -> datetime:
        """Ödünç alma tarihini döndürür."""
        return self._borrow_date

    @borrow_date.setter
    def borrow_date(self, value: datetime) -> None:
        """Ödünç alma tarihini günceller."""
        if not isinstance(value, datetime):
            raise TypeError("Ödünç tarihi bir datetime nesnesi olmalıdır.")
        self._borrow_date = value

    @property
    def return_date(self) -> Optional[datetime]:
        """İade tarihini döndürür (Henüz iade edilmediyse None)."""
        return self._return_date

    @property
    def status(self) -> BorrowStatus:
        """Kaydın anlık durumunu döndürür."""
        return self._status

    @status.setter
    def status(self, value: BorrowStatus) -> None:
        """Kaydın durumunu günceller."""
        if not isinstance(value, BorrowStatus):
            try:
                value = BorrowStatus(value)
            except ValueError:
                raise ValueError(f"Geçersiz kayıt durumu: {value}. "
                                 f"Beklenen: {[s.value for s in BorrowStatus]}")
        self._status = value

    # -------------------------------------------------------------------------
    # İş Kuralları Metotları (Business Methods)
    # -------------------------------------------------------------------------
    def is_active(self) -> bool:
        """
        Ödünç kaydının hala aktif (iade edilmemiş) olup olmadığını kontrol eder.
        
        Returns:
            bool: Durum ACTIVE ise True, değilse False.
        """
        return self._status == BorrowStatus.ACTIVE

    def close_record(self, return_date: Optional[datetime] = None) -> None:
        """
        Ödünç kaydını kapatır ve iade işlemini tamamlar.
        
        OOP Karşılığı: Encapsulation (İç durumun kontrollü değişimi)
        İade tarihi atanır ve durum 'RETURNED' olarak güncellenir.
        
        Args:
            return_date (Optional[datetime]): İade tarihi. Verilmezse anlık zaman atanır.
            
        Raises:
            ValueError: Kayıt zaten kapatılmışsa (iade edilmişse) hata fırlatılır.
        """
        if not self.is_active():
            raise ValueError(f"ID #{self._id} numaralı ödünç kaydı zaten iade edilerek kapatılmış.")
        
        resolved_return_date = return_date if return_date is not None else datetime.now()
        
        # İade tarihi ödünç tarihinden önce olamaz doğrulaması
        if resolved_return_date < self._borrow_date:
            raise ValueError("İade tarihi, ödünç alma tarihinden daha eski olamaz.")

        self._return_date = resolved_return_date
        self._status = BorrowStatus.RETURNED

    # -------------------------------------------------------------------------
    # String Temsilleri (Representation)
    # -------------------------------------------------------------------------
    def __str__(self) -> str:
        """Kullanıcı dostu metin temsili."""
        borrow_str = self._borrow_date.strftime("%Y-%m-%d %H:%M")
        return_str = self._return_date.strftime("%Y-%m-%d %H:%M") if self._return_date else "Devam Ediyor"
        return (
            f"Ödünç Kaydı #{self._id} [Üye ID: {self._member_id} -> Kitap ID: {self._book_id}] | "
            f"Alış: {borrow_str} | İade: {return_str} | Durum: {self._status.value}"
        )

    def __repr__(self) -> str:
        """Geliştirici dostu nesne temsili."""
        return (
            f"<BorrowRecord(id={self._id}, member_id={self._member_id}, "
            f"book_id={self._book_id}, status='{self._status.value}')>"
        )
