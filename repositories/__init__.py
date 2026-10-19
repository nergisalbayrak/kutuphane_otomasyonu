"""
Repositories Paketi (Data Access Layer - DAL)
==============================================
Bu paket, N-Tier mimarideki Veri Erişim Katmanını dışa aktarır.

Katmanın Görevi:
- Veritabanı motorunu (SQLite) ve SQL sorgularını üst katmanlardan (Service/Business) gizlemek.
- Repository Tasarım Deseni ile her varlık (Book, User/Member/Librarian, BorrowRecord) için
  CRUD işlemlerini nesneye yönelik (Object-Oriented) arayüzlerle sunmak.
"""

from .database import DatabaseManager
from .book_repository import BookRepository
from .user_repository import UserRepository
from .borrow_repository import BorrowRepository

__all__ = [
    "DatabaseManager",
    "BookRepository",
    "UserRepository",
    "BorrowRepository",
]
