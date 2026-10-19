"""
Kullanıcı Modelleri (User Models)
=================================
Bu modül, kütüphane otomasyon sistemindeki kullanıcı varlıklarını (Entities) tanımlar.
N-Tier (Katmanlı) Mimarinin "Domain / Model" katmanında yer alır.

OOP Prensipleri:
----------------
1. Abstraction (Soyutlama): `User` sınıfı `ABC` kullanılarak soyut (abstract) olarak tanımlanmıştır.
   Doğrudan bu sınıftan nesne üretilemez, bir şablon görevi görür.
2. Inheritance (Kalıtım): `Member` ve `Librarian` sınıfları `User` sınıfından türer;
   ortak özellikleri (`id`, `name`, `email`, `role`) tekrar yazmadan devralır.
3. Encapsulation (Kapsülleme): Nitelikler korumalı (protected - `_`) olarak tutulur ve
   Python `@property` dekoratörleri ile kontrollü erişim ve doğrulama sağlanır.
4. Polymorphism (Çok Biçimlilik): `get_user_summary()` soyut metodu her alt sınıfta
   kendine özgü şekilde ezilerek (override) farklı davranış sergiler.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class User(ABC):
    """
    Kullanıcı Temel/Soyut Sınıfı (Abstract Base Class)
    --------------------------------------------------
    Tasarım İlkesi: Soyutlama (Abstraction) & Kapsülleme (Encapsulation)
    
    Kütüphanedeki tüm kullanıcı tipleri (Üye, Kütüphaneci vb.) için ortak
    özellik ve metotları tanımlayan taban sınıftır. `ABC` (Abstract Base Class)
    modülü kullanılarak doğrudan nesne örneği (instance) oluşturulması engellenmiştir.
    
    Özellikler (Attributes):
        id (int): Kullanıcının benzersiz kimlik numarası.
        name (str): Kullanıcının tam adı.
        email (str): Kullanıcının e-posta adresi.
        role (str): Kullanıcının sistemdeki rolü ('MEMBER', 'LIBRARIAN' vb.).
    """

    def __init__(self, id: int, name: str, email: str, role: str) -> None:
        """
        User sınıfının yapıcı (constructor) metodu.

        OOP Karşılığı: Encapsulation (Kapsülleme)
        Nitelikler doğrudan dışarıya açık bırakılmayıp `_` (protected) ön ekiyle
        kapsüllenmiştir.
        """
        self._id: int = id
        self._name: str = name
        self._email: str = email
        self._role: str = role

    # -------------------------------------------------------------------------
    # Kapsülleme (Encapsulation) - Getter ve Setter Özellikleri
    # -------------------------------------------------------------------------
    @property
    def id(self) -> int:
        """Kullanıcı ID'sini döndüren getter metodu."""
        return self._id

    @id.setter
    def id(self, value: int) -> None:
        """Kullanıcı ID'sini güncelleyen setter metodu (Doğrulama içerir)."""
        if value <= 0:
            raise ValueError("Kullanıcı ID'si pozitif bir tam sayı olmalıdır.")
        self._id = value

    @property
    def name(self) -> str:
        """Kullanıcı adını döndüren getter metodu."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Kullanıcı adını güncelleyen setter metodu."""
        if not value or not value.strip():
            raise ValueError("Kullanıcı adı boş bırakılamaz.")
        self._name = value.strip()

    @property
    def email(self) -> str:
        """Kullanıcı e-posta adresini döndüren getter metodu."""
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        """Kullanıcı e-posta adresini güncelleyen setter metodu."""
        if "@" not in value or "." not in value:
            raise ValueError("Geçerli bir e-posta adresi girilmelidir.")
        self._email = value.strip()

    @property
    def role(self) -> str:
        """Kullanıcı rolünü döndüren getter metodu."""
        return self._role

    # -------------------------------------------------------------------------
    # Soyutlama (Abstraction) ve Çok Biçimlilik (Polymorphism)
    # -------------------------------------------------------------------------
    @abstractmethod
    def get_user_summary(self) -> str:
        """
        OOP Karşılığı: Abstraction (Soyut Metot) & Polymorphism
        
        Bu metot alt sınıflar tarafından mutlaka ezilmeli (override edilmeli) ve
        ilgili kullanıcının özet bilgilerini döndürmelidir.
        """
        pass

    def __repr__(self) -> str:
        """Nesnenin temsil dizesini döndürür."""
        return f"<{self.__class__.__name__}(id={self._id}, name='{self._name}', email='{self._email}')>"


class Member(User):
    """
    Üye Sınıfı (Member Entity)
    --------------------------
    Tasarım İlkesi: Kalıtım (Inheritance), Kapsülleme (Encapsulation), Çok Biçimlilik (Polymorphism)
    
    `User` taban sınıfından türer. Kitap ödünç alabilen standart kütüphane üyelerini temsil eder.
    
    Ek Özellikler:
        max_book_limit (int): Bir üyenin aynı anda alabileceği maksimum kitap sayısı (Varsayılan: 3).
        active_borrows (List[int]): Üyenin üzerindeki aktif ödünç alma kayıtlarının (BorrowRecord) ID listesi.
    """

    DEFAULT_MAX_BOOK_LIMIT: int = 3

    def __init__(
        self,
        id: int,
        name: str,
        email: str,
        max_book_limit: int = DEFAULT_MAX_BOOK_LIMIT,
        active_borrows: Optional[List[int]] = None
    ) -> None:
        """
        Member sınıfı yapıcı metodu.

        OOP Karşılığı:
        `super().__init__(...)` çağrısıyla üst sınıfın (`User`) yapıcısı çağrılarak
        kalıtım (Inheritance) işletilir.
        """
        super().__init__(id=id, name=name, email=email, role="MEMBER")
        self._max_book_limit: int = max_book_limit
        # Aktif ödünç alınan kayıtların ID'lerini liste olarak tutar
        self._active_borrows: List[int] = active_borrows if active_borrows is not None else []

    # -------------------------------------------------------------------------
    # Kapsülleme (Encapsulation) - Getter & Setter
    # -------------------------------------------------------------------------
    @property
    def max_book_limit(self) -> int:
        """Maksimum ödünç kitap limitini döndürür."""
        return self._max_book_limit

    @max_book_limit.setter
    def max_book_limit(self, value: int) -> None:
        """Maksimum ödünç kitap limitini günceller."""
        if value < 1:
            raise ValueError("Maksimum kitap limiti en az 1 olmalıdır.")
        self._max_book_limit = value

    @property
    def active_borrows(self) -> List[int]:
        """
        Aktif ödünç ID listesinin kopyasını döndürür.
        Kapsülleme (Encapsulation) gereği listenin doğrudan manipüle edilmesini
        engellemek için liste kopyası döndürülür.
        """
        return list(self._active_borrows)

    # -------------------------------------------------------------------------
    # İş Kuralları ve Durum Yönetimi (Business Helper Methods)
    # -------------------------------------------------------------------------
    def can_borrow(self) -> bool:
        """
        Üyenin yeni bir kitap ödünç alıp alamayacağını kontrol eder.
        
        Returns:
            bool: Aktif ödünç sayısı limiti aşmamışsa True, aksi halde False.
        """
        return len(self._active_borrows) < self._max_book_limit

    def add_active_borrow(self, borrow_id: int) -> None:
        """
        Üyenin aktif ödünç listesine yeni bir kayıt ID'si ekler.
        
        Args:
            borrow_id (int): Eklenen ödünç kaydının ID'si.
            
        Raises:
            ValueError: Limit aşıldıysa veya kayıt zaten mevcutsa hata fırlatılır.
        """
        if not self.can_borrow():
            raise ValueError(f"Maksimum ödünç alma limitine ({self._max_book_limit}) ulaşıldı.")
        if borrow_id in self._active_borrows:
            raise ValueError("Bu ödünç kaydı zaten üyenin aktif listesinde bulunuyor.")
        self._active_borrows.append(borrow_id)

    def remove_active_borrow(self, borrow_id: int) -> None:
        """
        Kitap iade edildiğinde ilgili ödünç ID'sini aktif listeden çıkarır.
        
        Args:
            borrow_id (int): Çıkarılacak ödünç kaydının ID'si.
        """
        if borrow_id in self._active_borrows:
            self._active_borrows.remove(borrow_id)

    # -------------------------------------------------------------------------
    # Çok Biçimlilik (Polymorphism)
    # -------------------------------------------------------------------------
    def get_user_summary(self) -> str:
        """
        OOP Karşılığı: Polymorphism (Çok Biçimlilik - Metot Ezme / Override)
        
        `User` sınıfındaki soyut metodu `Member` sınıfına özgü ayrıntılarla
        uygular.
        """
        return (
            f"[Üye] ID: {self._id} | Ad: {self._name} | E-posta: {self._email} | "
            f"Aktif Ödünç: {len(self._active_borrows)}/{self._max_book_limit}"
        )


class Librarian(User):
    """
    Kütüphaneci / Görevli Sınıfı (Librarian Entity)
    -----------------------------------------------
    Tasarım İlkesi: Kalıtım (Inheritance), Kapsülleme (Encapsulation), Çok Biçimlilik (Polymorphism)
    
    `User` taban sınıfından türer. Sistemde kitap ekleme, silme, ödünç onaylama gibi
    yönetimsel yetkilere sahip kütüphane personelini temsil eder.
    
    Ek Özellikler:
        employee_id (str): Kütüphane personelinin sicil/çalışan numarası.
    """

    def __init__(self, id: int, name: str, email: str, employee_id: str) -> None:
        """
        Librarian sınıfı yapıcı metodu.

        OOP Karşılığı:
        `super().__init__(...)` ile `User` sınıfının alanları devralınır.
        """
        super().__init__(id=id, name=name, email=email, role="LIBRARIAN")
        self._employee_id: str = employee_id

    # -------------------------------------------------------------------------
    # Kapsülleme (Encapsulation) - Getter & Setter
    # -------------------------------------------------------------------------
    @property
    def employee_id(self) -> str:
        """Personel çalışan numarasını döndürür."""
        return self._employee_id

    @employee_id.setter
    def employee_id(self, value: str) -> None:
        """Personel çalışan numarasını günceller."""
        if not value or not value.strip():
            raise ValueError("Personel sicil numarası boş bırakılamaz.")
        self._employee_id = value.strip()

    # -------------------------------------------------------------------------
    # Çok Biçimlilik (Polymorphism)
    # -------------------------------------------------------------------------
    def get_user_summary(self) -> str:
        """
        OOP Karşılığı: Polymorphism (Çok Biçimlilik - Metot Ezme / Override)
        
        `User` sınıfındaki soyut metodu `Librarian` sınıfına özgü ayrıntılarla uygular.
        """
        return (
            f"[Kütüphaneci] ID: {self._id} | Sicil No: {self._employee_id} | "
            f"Ad: {self._name} | E-posta: {self._email}"
        )
