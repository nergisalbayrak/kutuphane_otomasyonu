"""
Ödünç Alma ve İade İş Mantığı Katmanı (Borrow Service)
======================================================
Bu modül, kütüphane otomasyon sisteminin en kritik iş süreçlerini (Core Business Logic)
yönetir: Kitap ödünç verme, limit denetimleri, iade alma ve gecikme cezası hesaplama.

Mimari Soru: "Bu Hesaplamalar Neden SQL veya UI Katmanında Değil de Service Katmanında Yapılır?"
------------------------------------------------------------------------------------------------
1. İş Kurallarının Merkezi Yönetimi:
   - Örneğin kütüphane yönetimi yarın "Ödünç süresini 14 günden 21 güne çıkarıyoruz"
     veya "Günlük ceza 5 TL yerine 10 TL oldu" derse; SQL tabloları veya UI formları
     değişmez, yalnızca bu servis sınıfındaki kurallar güncellenir.
2. İşlem Bütünlüğü ve Orkestrasyon (Transaction Orchestration):
   - Ödünç verme işlemi tek bir işlem değildir:
     a) Üye limiti kontrol edilir.
     b) Kitabın durumu sorgulanır.
     c) Ödünç kaydı açılır.
     d) Kitabın durumu 'BORROWED' yapılır.
   - Tüm bu adımların koordinasyonu Service katmanının temel görevidir.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from models.book import BookStatus
from models.borrow_record import BorrowRecord, BorrowStatus
from models.user import Member
from repositories.book_repository import BookRepository
from repositories.borrow_repository import BorrowRepository
from repositories.user_repository import UserRepository


@dataclass
class ReturnReceipt:
    """
    İade İşlem Dekontu (Data Transfer Object - DTO)
    -----------------------------------------------
    Tasarım İlkesi: DTO (Data Transfer Object)
    
    İade işlemi tamamlandığında üst katmanlara (UI / Sunum Katmanı)
    hesaplanan ceza, gecikme günü ve işlem özetini paketleyerek ileten
    veri taşıyıcı sınıftır.
    """
    record: BorrowRecord
    days_borrowed: int
    overdue_days: int
    penalty_fee: float
    message: str


class BorrowService:
    """
    Ödünç ve İade İş Süreçleri Yöneticisi (Borrow Service)
    -----------------------------------------------------
    Tasarım Deseni: Service Layer Pattern & Dependency Injection
    
    `BorrowRepository`, `BookRepository` ve `UserRepository` sınıflarını koordine ederek
    kütüphane kurallarını uygular.
    """

    # Kütüphane İş Kuralları Sabitleri (Business Constants)
    STANDARD_LOAN_DAYS: int = 14     # Standart ödünç verme süresi (gün)
    DAILY_PENALTY_RATE: float = 5.0   # Gecikilen her gün başına ceza tutarı (TL)

    def __init__(
        self,
        borrow_repository: BorrowRepository,
        book_repository: BookRepository,
        user_repository: UserRepository
    ) -> None:
        """
        BorrowService yapıcı metodu.

        OOP Karşılığı: Dependency Injection
        Üç farklı veri deposunu bir araya getirerek iş mantığını yönetir.
        """
        self._borrow_repo: BorrowRepository = borrow_repository
        self._book_repo: BookRepository = book_repository
        self._user_repo: UserRepository = user_repository

    # -------------------------------------------------------------------------
    # İş Kuralı: Kitap Ödünç Verme (borrow_book)
    # -------------------------------------------------------------------------
    def borrow_book(self, member_id: int, book_id: int) -> BorrowRecord:
        """
        Bir üyeye kitap ödünç verir.

        İş Kuralları (Business Rules):
        1. Üye sistemde kayıtlı olmalı ve rolü 'MEMBER' olmalıdır.
        2. Üyenin aktif kitap limiti (varsayılan 3) kontrol edilir.
           Aktif ödünç sayısı limiti aşmışsa İŞLEM REDDEDİLİR.
        3. Kitap sistemde kayıtlı olmalıdır.
        4. Kitabın durumu 'AVAILABLE' (Rafta) olmalıdır. Eğer zaten ödünçteyse
           İŞLEM REDDEDİLİR.
        5. Tüm kurallar geçerliyse:
           - Kitap 'BORROWED' durumuna çekilir.
           - Yeni bir `BorrowRecord` (durumu 'ACTIVE') oluşturulur.
           - Üyenin aktif ödünç listesi güncellenir.

        Args:
            member_id (int): Kitabı alacak üyenin ID'si.
            book_id (int): Ödünç verilecek kitabın ID'si.

        Returns:
            BorrowRecord: Oluşturulan ödünç hareket kaydı.

        Raises:
            ValueError: İş kurallarından herhangi biri ihlal edilirse.
        """
        # 1. Kural: Üye varlık ve rol kontrolü
        user = self._user_repo.get_by_id(member_id)
        if user is None:
            raise ValueError(f"İş Kuralı İhlali: ID #{member_id} numaralı kullanıcı bulunamadı.")
        if not isinstance(user, Member):
            raise ValueError(f"İş Kuralı İhlali: ID #{member_id} bir üye (Member) değildir. Sadece üyeler kitap ödünç alabilir.")

        # 2. Kural: Maksimum kitap limiti kontrolü (max 3)
        active_records = self._borrow_repo.get_active_by_member(member_id)
        if len(active_records) >= user.max_book_limit:
            raise ValueError(
                f"İş Kuralı İhlali: Üye '{user.name}' maksimum ödünç alma limitine "
                f"({user.max_book_limit} kitap) ulaşmıştır. Yeni kitap alamaz!"
            )

        # 3. Kural: Kitap varlık kontrolü
        book = self._book_repo.get_by_id(book_id)
        if book is None:
            raise ValueError(f"İş Kuralı İhlali: ID #{book_id} numaralı kitap kütüphanede bulunamadı.")

        # 4. Kural: Kitap rafta mı kontrolü
        if not book.is_available():
            raise ValueError(
                f"İş Kuralı İhlali: '{book.title}' başlıklı kitap şu anda kütüphanede mevcut değil (Ödünçte)!"
            )

        # 5. Adım: Başarılı senaryo - Durumların güncellenmesi
        book.mark_as_borrowed()
        self._book_repo.update(book)

        new_record = BorrowRecord(
            id=0,
            member_id=member_id,
            book_id=book_id,
            borrow_date=datetime.now(),
            return_date=None,
            status=BorrowStatus.ACTIVE
        )
        saved_record = self._borrow_repo.add(new_record)
        return saved_record

    # -------------------------------------------------------------------------
    # İş Kuralı: Kitap İade Alma ve Ceza Hesaplama (return_book)
    # -------------------------------------------------------------------------
    def return_book(
        self,
        borrow_id: int,
        return_date: Optional[datetime] = None
    ) -> ReturnReceipt:
        """
        Ödünç verilen kitabı iade alır ve gecikme cezasını hesaplar.

        İş Kuralları (Business Rules):
        1. Belirtilen ID'ye ait bir ödünç kaydı bulunmalıdır.
        2. Kayıt zaten 'RETURNED' ise mükerrer iade reddedilir.
        3. Gecikme Cezası Hesabı:
           - İade tarihi ile ödünç tarihi arasındaki gün farkı hesaplanır.
           - Standart ödünç süresi 14 gündür (`STANDARD_LOAN_DAYS`).
           - Eğer ödünç süresi 14 günü aşmışsa:
             `gecikme_gunu = toplam_gun - 14`
             `ceza_tutari = gecikme_gunu * DAILY_PENALTY_RATE (5.0 TL)`
           - Aşmamışsa ceza 0 TL'dir.
        4. Kitap tekrar 'AVAILABLE' durumuna getirilir.
        5. Kaydın durumu 'RETURNED' olarak kapatılır.

        Args:
            borrow_id (int): Kapatılacak ödünç işlem ID'si.
            return_date (Optional[datetime]): İade zamanı (Test veya simülasyon için opsiyonel).

        Returns:
            ReturnReceipt: Ceza ve iade ayrıntılarını içeren dekont nesnesi.

        Raises:
            ValueError: Kayıt bulunamazsa veya zaten iade edilmişse.
        """
        # 1. Kural: Kayıt kontrolü
        record = self._borrow_repo.get_by_id(borrow_id)
        if record is None:
            raise ValueError(f"İş Kuralı İhlali: ID #{borrow_id} numaralı ödünç kaydı bulunamadı.")

        # 2. Kural: Mükerrer iade kontrolü
        if not record.is_active():
            raise ValueError(f"İş Kuralı İhlali: ID #{borrow_id} numaralı kayıt zaten daha önce iade edilmiş!")

        actual_return_date = return_date if return_date is not None else datetime.now()

        # 3. Kural: Gecikme ve Ceza Hesabı
        time_difference = actual_return_date - record.borrow_date
        total_days = max(1, time_difference.days)  # En az 1 gün sayılır
        overdue_days = max(0, total_days - self.STANDARD_LOAN_DAYS)
        penalty_fee = round(overdue_days * self.DAILY_PENALTY_RATE, 2)

        # 4. Adım: Kaydı kapat
        record.close_record(actual_return_date)
        self._borrow_repo.update(record)

        # 5. Adım: Kitabı tekrar rafa (AVAILABLE) al
        book = self._book_repo.get_by_id(record.book_id)
        if book:
            book.mark_as_available()
            self._book_repo.update(book)

        # Kullanıcı dostu bilgilendirme mesajı
        if overdue_days > 0:
            msg = (
                f"Kitap {overdue_days} gün gecikmeyle iade edildi! "
                f"Hesaplanan Gecikme Cezası: {penalty_fee:.2f} TL."
            )
        else:
            msg = "Kitap süresi içerisinde zamanında iade edildi. Ceza bulunmamaktadır."

        return ReturnReceipt(
            record=record,
            days_borrowed=total_days,
            overdue_days=overdue_days,
            penalty_fee=penalty_fee,
            message=msg
        )

    # -------------------------------------------------------------------------
    # Sorgulama ve Bilgi Metotları
    # -------------------------------------------------------------------------
    def get_active_borrows_for_member(self, member_id: int) -> List[BorrowRecord]:
        """
        Belirli bir üyenin elindeki tüm aktif ödünç kitap kayıtlarını getirir.
        """
        return self._borrow_repo.get_active_by_member(member_id)

    def get_all_borrow_history(self) -> List[BorrowRecord]:
        """
        Tüm geçmiş ve aktif ödünç hareketlerini listeler.
        """
        return self._borrow_repo.get_all()
