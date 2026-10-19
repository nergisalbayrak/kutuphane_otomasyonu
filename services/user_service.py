"""
Kullanıcı ve Yetkilendirme İş Mantığı Katmanı (User Service)
============================================================
Bu modül, kullanıcı (Üye ve Kütüphaneci) kayıtlarını, profil yönetimini ve
rol tabanlı yetkilendirme (Authorization) kontrollerini yönetir.

Mimari Soru: "Yetkilendirme ve Üye Kuralları Neden Service Katmanında Bulunur?"
------------------------------------------------------------------------------
1. Güvenlik ve İş Kuralı İzolasyonu:
   - UI (Arayüz) katmanındaki doğrulamalar istemci taraflıdır ve atlatılabilir.
   - Veritabanı (DAL) katmanı ise sadece satır kaydeder, "aktif ödünç kitabı olan üye
     silinemez" gibi karmaşık iş kurallarını bilmez.
   - Bu nedenle gerçek güvenlik ve iş denetimleri Service katmanında yapılır.
2. Rol Tabanlı Yetkilendirme (RBAC - Role-Based Access Control):
   - Bir işlemin (kitap ekleme/silme vb.) yalnızca 'LIBRARIAN' rolündeki personel
     tarafından yapılabileceğini kontrol eden merkezi mantık buradadır.
"""

from typing import List, Optional

from models.user import User, Member, Librarian
from repositories.user_repository import UserRepository
from repositories.borrow_repository import BorrowRepository


class UserService:
    """
    Kullanıcı ve Yetki Yöneticisi (User Service)
    -------------------------------------------
    Tasarım İlkesi: Service Layer Pattern & RBAC (Role-Based Access Control)
    
    Üye ve kütüphane personeli kayıtlarını, e-posta benzersizliğini ve
    silme öncesi aktif ödünç denetimlerini yürütür.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        borrow_repository: BorrowRepository
    ) -> None:
        """
        UserService yapıcı metodu.

        OOP Karşılığı: Dependency Injection
        Kullanıcı ve ödünç depolarını bağımlılık olarak alır.
        """
        self._user_repo: UserRepository = user_repository
        self._borrow_repo: BorrowRepository = borrow_repository

    # -------------------------------------------------------------------------
    # İş Kuralı: Yeni Üye Kaydı (register_member)
    # -------------------------------------------------------------------------
    def register_member(
        self,
        name: str,
        email: str,
        max_book_limit: int = Member.DEFAULT_MAX_BOOK_LIMIT
    ) -> Member:
        """
        Sisteme yeni bir kütüphane üyesi kaydeder.

        İş Kuralları (Business Rules):
        1. Ad ve e-posta alanları boş bırakılamaz.
        2. E-posta adresi geçerli formatta (@ ve .) olmalıdır.
        3. E-posta adresi sistemde tamamen BENZERSİZ olmalıdır.
        4. Maksimum kitap alma limiti en az 1 olmalıdır.

        Args:
            name (str): Üyenin tam adı.
            email (str): Üyenin e-posta adresi.
            max_book_limit (int): Alabileceği maksimum kitap sayısı (Varsayılan: 3).

        Returns:
            Member: Veritabanına kaydedilen yeni üye nesnesi.

        Raises:
            ValueError: Kurallar ihlal edilirse.
        """
        clean_name = name.strip() if name else ""
        clean_email = email.strip() if email else ""

        if not clean_name:
            raise ValueError("İş Kuralı İhlali: Üye adı boş bırakılamaz.")
        if not clean_email or "@" not in clean_email or "." not in clean_email:
            raise ValueError("İş Kuralı İhlali: Geçerli bir e-posta adresi girilmelidir.")
        if max_book_limit < 1:
            raise ValueError("İş Kuralı İhlali: Kitap ödünç limiti en az 1 olmalıdır.")

        # E-posta benzersizlik kontrolü
        existing_user = self._user_repo.get_by_email(clean_email)
        if existing_user is not None:
            raise ValueError(
                f"İş Kuralı İhlali: '{clean_email}' e-posta adresi sistemde zaten kayıtlı "
                f"({existing_user.name} - Rol: {existing_user.role})."
            )

        new_member = Member(
            id=0,
            name=clean_name,
            email=clean_email,
            max_book_limit=max_book_limit
        )
        return self._user_repo.add(new_member)  # type: ignore

    # -------------------------------------------------------------------------
    # İş Kuralı: Yeni Kütüphaneci Personel Kaydı
    # -------------------------------------------------------------------------
    def register_librarian(self, name: str, email: str, employee_id: str) -> Librarian:
        """
        Sisteme yeni bir kütüphane personeli/görevlisi kaydeder.

        İş Kuralları (Business Rules):
        1. E-posta benzersiz olmalıdır.
        2. Personel sicil numarası (employee_id) boş olamaz.
        """
        clean_name = name.strip() if name else ""
        clean_email = email.strip() if email else ""
        clean_emp_id = employee_id.strip() if employee_id else ""

        if not clean_name or not clean_email or not clean_emp_id:
            raise ValueError("İş Kuralı İhlali: İsim, e-posta ve sicil numarası zorunludur.")

        existing_user = self._user_repo.get_by_email(clean_email)
        if existing_user is not None:
            raise ValueError(f"İş Kuralı İhlali: '{clean_email}' e-posta adresi sistemde zaten kayıtlı.")

        new_librarian = Librarian(
            id=0,
            name=clean_name,
            email=clean_email,
            employee_id=clean_emp_id
        )
        return self._user_repo.add(new_librarian)  # type: ignore

    # -------------------------------------------------------------------------
    # İş Kuralı: Yetkilendirme ve Rol Kontrolü (Authorization)
    # -------------------------------------------------------------------------
    def authorize_librarian(self, user_id: int) -> Librarian:
        """
        Belirtilen kullanıcının kütüphaneci yetkisine sahip olup olmadığını denetler.

        Katmanlı Mimari Rolü:
        Yönetici/Görevli işlemlerinden önce çağrılarak işlem güvenliğini sağlar.

        Args:
            user_id (int): İşlem yapmak isteyen kullanıcının ID'si.

        Returns:
            Librarian: Yetkili personel nesnesi.

        Raises:
            PermissionError: Kullanıcı kütüphaneci değilse veya bulunamazsa.
        """
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise PermissionError(f"Yetki Hatası: ID #{user_id} numaralı kullanıcı bulunamadı.")
        if not isinstance(user, Librarian):
            raise PermissionError(
                f"Yetki Hatası: Bu işlemi sadece Kütüphane Görevlileri (Librarian) yapabilir. "
                f"Mevcut rol: '{user.role}'."
            )
        return user

    # -------------------------------------------------------------------------
    # İş Kuralı: Üye Silme ve Aktif Ödünç Kontrolü
    # -------------------------------------------------------------------------
    def delete_user(self, user_id: int) -> bool:
        """
        Kullanıcıyı sistemden siler.

        İş Kuralları (Business Rules):
        1. Silinmek istenen kullanıcı bir 'Member' ise ve üzerinde henüz iade
           etmediği aktif ödünç kitaplar varsa SİLME İŞLEMİ ENGELLENİR!
        """
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"İş Kuralı İhlali: ID #{user_id} numaralı kullanıcı bulunamadı.")

        if isinstance(user, Member):
            active_borrows = self._borrow_repo.get_active_by_member(user_id)
            if active_borrows:
                raise ValueError(
                    f"İş Kuralı İhlali: '{user.name}' isimli üyenin üzerinde henüz teslim edilmemiş "
                    f"{len(active_borrows)} adet kitap bulunmaktadır. Önce kitaplar iade edilmelidir!"
                )

        return self._user_repo.delete(user_id)

    # -------------------------------------------------------------------------
    # Sorgulama Metotları
    # -------------------------------------------------------------------------
    def get_user_by_id(self, user_id: int) -> User:
        """ID ile kullanıcı getirir."""
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"ID #{user_id} numaralı kullanıcı bulunamadı.")
        return user

    def get_user_by_email(self, email: str) -> Optional[User]:
        """E-posta ile kullanıcı arar."""
        return self._user_repo.get_by_email(email.strip())

    def list_all_users(self) -> List[User]:
        """Sistemdeki tüm kullanıcıları (Üyeler ve Kütüphaneciler) listeler."""
        return self._user_repo.get_all()

    def list_members(self) -> List[Member]:
        """Tüm kayıtlı üyeleri listeler."""
        return self._user_repo.get_all_members()

    def list_librarians(self) -> List[Librarian]:
        """Tüm kütüphane personellerini listeler."""
        return self._user_repo.get_all_librarians()
