"""
Kütüphane Otomasyonu - CustomTkinter Modern Görsel Arayüzü (Presentation Layer)
================================================================================
Bu modül, N-Tier (Katmanlı) Mimarinin en üst katmanı olan "Presentation Layer"dır.

Mimari Özellikler:
------------------
1. %100 CustomTkinter Koyu Tema (Zero Native Popups):
   - Standart işletim sistemi beyaz pop-up diyalogları (tkinter.messagebox) tamamen
     kaldırılmıştır.
   - Tüm bilgi, uyarı, hata, onay (askyesno) ve iade ceza dekontları; modern
     `CTkToplevel` tabanlı koyu temalı kart pencerelerle (Custom Modal Dialogs) yönetilir.
2. Özel Ceza ve İade Faturası / Dekontu (Receipt Modal):
   - İade işleminde hesaplanan ceza tutarı, gecikme süresi ve işlem özeti
     kurumsal SaaS makbuzu görünümünde özel bir diyalog penceresinde sunulur.
3. Mimari Katmanların Tam Korunması (Loose Coupling):
   - `services/` ve `repositories/` katmanları hiçbir değişikliğe uğramadan
     çalışmaya devam eder.
"""

import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
from typing import List, Optional, Callable

import customtkinter as ctk

# 1. Katman: Varlık Modelleri (Domain Entities)
from models.book import Book, BookStatus
from models.user import Member, Librarian, User
from models.borrow_record import BorrowRecord, BorrowStatus

# 2. Katman: Veri Erişim Katmanı (Data Access Layer - DAL)
from repositories.database import DatabaseManager
from repositories.book_repository import BookRepository
from repositories.user_repository import UserRepository
from repositories.borrow_repository import BorrowRepository

# 3. Katman: İş Mantığı Katmanı (Business Logic Layer - BLL)
from services.book_service import BookService
from services.borrow_service import BorrowService, ReturnReceipt
from services.user_service import UserService

# -----------------------------------------------------------------------------
# CustomTkinter Genel Tema Ayarları
# -----------------------------------------------------------------------------
ctk.set_appearance_mode("Dark")       # Koyu Gece Modu (Dark Mode)
ctk.set_default_color_theme("blue")    # Modern Mavi Vurgu Teması


# =============================================================================
# Modern CustomTkinter Pop-up ve Diyalog Pencereleri (Custom Modals)
# =============================================================================
def center_modal(dialog: ctk.CTkToplevel, parent: ctk.CTk, width: int, height: int) -> None:
    """
    Diyalog penceresini ana pencerenin tam ortasına konumlandırır.
    """
    parent.update_idletasks()
    dialog.update_idletasks()
    pw = parent.winfo_width()
    ph = parent.winfo_height()
    px = parent.winfo_rootx()
    py = parent.winfo_rooty()
    x = max(40, px + (pw - width) // 2)
    y = max(40, py + (ph - height) // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")


def show_custom_message(
    parent: ctk.CTk,
    title: str,
    message: str,
    msg_type: str = "info"
) -> None:
    """
    Modern koyu temalı Bilgi, Başarı, Uyarı veya Hata diyalogu açar.
    Klasik işletim sistemi messagebox kutularının yerini alır.
    """
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry("450x260")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    # İkon ve Renk Konfigürasyonu
    type_configs = {
        "info": {"icon": "ℹ️", "color": "#2563eb", "badge": "BİLGİLENDİRME"},
        "success": {"icon": "✔", "color": "#059669", "badge": "BAŞARILI İŞLEM"},
        "warning": {"icon": "⚠️", "color": "#d97706", "badge": "DİKKAT / UYARI"},
        "error": {"icon": "❌", "color": "#dc2626", "badge": "HATA / İHLAL"}
    }
    cfg = type_configs.get(msg_type, type_configs["info"])

    center_modal(dialog, parent, 450, 260)

    # Ana Kart Konteyneri
    card = ctk.CTkFrame(dialog, corner_radius=15, fg_color="#1e293b", border_width=1, border_color="#334155")
    card.pack(fill="both", expand=True, padx=14, pady=14)

    # Üst Başlık ve İkon Rozeti
    top_bar = ctk.CTkFrame(card, fg_color="transparent")
    top_bar.pack(fill="x", padx=16, pady=(14, 8))

    icon_badge = ctk.CTkLabel(
        top_bar,
        text=cfg["icon"],
        font=ctk.CTkFont(size=18),
        width=36,
        height=36,
        corner_radius=18,
        fg_color=cfg["color"],
        text_color="#ffffff"
    )
    icon_badge.pack(side="left", padx=(0, 10))

    header_text_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
    header_text_frame.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(
        header_text_frame,
        text=cfg["badge"],
        font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
        text_color=cfg["color"]
    ).pack(anchor="w")

    ctk.CTkLabel(
        header_text_frame,
        text=title,
        font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        text_color="#ffffff"
    ).pack(anchor="w")

    # Mesaj Metni
    msg_label = ctk.CTkLabel(
        card,
        text=message,
        font=ctk.CTkFont(family="Segoe UI", size=11),
        text_color="#cbd5e1",
        justify="left",
        wraplength=380
    )
    msg_label.pack(fill="both", expand=True, padx=18, pady=(4, 10))

    # Kapat Butonu (Modern Kapsül Buton)
    btn_close = ctk.CTkButton(
        card,
        text="✔  Tamam",
        width=120,
        height=36,
        corner_radius=18,
        fg_color=cfg["color"],
        hover_color="#1d4ed8" if cfg["color"] == "#2563eb" else ("#047857" if cfg["color"] == "#059669" else "#b91c1c"),
        font=ctk.CTkFont(size=11, weight="bold"),
        command=dialog.destroy
    )
    btn_close.pack(side="bottom", pady=(0, 14))

    dialog.wait_window()


def show_custom_confirm(
    parent: ctk.CTk,
    title: str,
    message: str
) -> bool:
    """
    Modern koyu temalı Onay (askyesno) diyalogu açar.
    Kullanıcı 'Evet' basarsa True, 'Vazgeç' basarsa False döndürür.
    """
    dialog = ctk.CTkToplevel(parent)
    dialog.title(title)
    dialog.geometry("450x240")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    center_modal(dialog, parent, 450, 240)

    result = [False]

    def on_yes() -> None:
        result[0] = True
        dialog.destroy()

    def on_no() -> None:
        result[0] = False
        dialog.destroy()

    card = ctk.CTkFrame(dialog, corner_radius=15, fg_color="#1e293b", border_width=1, border_color="#334155")
    card.pack(fill="both", expand=True, padx=14, pady=14)

    # Üst İkon
    top_bar = ctk.CTkFrame(card, fg_color="transparent")
    top_bar.pack(fill="x", padx=16, pady=(14, 6))

    icon_badge = ctk.CTkLabel(
        top_bar,
        text="❓",
        font=ctk.CTkFont(size=18),
        width=36,
        height=36,
        corner_radius=18,
        fg_color="#6366f1",
        text_color="#ffffff"
    )
    icon_badge.pack(side="left", padx=(0, 10))

    header_text_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
    header_text_frame.pack(side="left", fill="both", expand=True)

    ctk.CTkLabel(
        header_text_frame,
        text="İŞLEM ONAYI",
        font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
        text_color="#818cf8"
    ).pack(anchor="w")

    ctk.CTkLabel(
        header_text_frame,
        text=title,
        font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
        text_color="#ffffff"
    ).pack(anchor="w")

    msg_label = ctk.CTkLabel(
        card,
        text=message,
        font=ctk.CTkFont(family="Segoe UI", size=11),
        text_color="#cbd5e1",
        justify="left",
        wraplength=380
    )
    msg_label.pack(fill="both", expand=True, padx=18, pady=(4, 10))

    # Butonlar: Modern Yeşil (Evet) ve Kırmızı (Hayır) Kapsül Butonlar
    btn_bar = ctk.CTkFrame(card, fg_color="transparent")
    btn_bar.pack(side="bottom", fill="x", padx=16, pady=(0, 14))

    # Kırmızı Kapsül Buton (Hayır / Vazgeç)
    btn_no = ctk.CTkButton(
        btn_bar,
        text="✖  Hayır, Vazgeç",
        width=135,
        height=36,
        corner_radius=18,
        fg_color="#dc2626",
        hover_color="#b91c1c",
        font=ctk.CTkFont(size=11, weight="bold"),
        command=on_no
    )
    btn_no.pack(side="left")

    # Yeşil Kapsül Buton (Evet / Onaylıyorum)
    btn_yes = ctk.CTkButton(
        btn_bar,
        text="✔  Evet, Onaylıyorum",
        width=165,
        height=36,
        corner_radius=18,
        fg_color="#059669",
        hover_color="#047857",
        font=ctk.CTkFont(size=11, weight="bold"),
        command=on_yes
    )
    btn_yes.pack(side="right")

    dialog.wait_window()
    return result[0]


def show_return_receipt_modal(parent: ctk.CTk, receipt: ReturnReceipt) -> None:
    """
    Modern Koyu Temalı İade ve Ceza Faturası / Dekontu (Receipt Modal Dialog).
    Klasik pop-up yerine kurumsal SaaS makbuzu formatında sunar.
    """
    dialog = ctk.CTkToplevel(parent)
    dialog.title("İade İşlem Dekontu")
    dialog.geometry("500x520")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.grab_set()

    center_modal(dialog, parent, 500, 520)

    # Ana Kart
    card = ctk.CTkFrame(dialog, corner_radius=15, fg_color="#1e293b", border_width=1, border_color="#334155")
    card.pack(fill="both", expand=True, padx=16, pady=16)

    # Üst Başlık Rozeti (Gecikmeli mi zamanında mı?)
    is_overdue = receipt.overdue_days > 0
    status_bg = "#451a1a" if is_overdue else "#064e3b"
    status_fg = "#f87171" if is_overdue else "#34d399"
    status_icon = "⚠️" if is_overdue else "✔"
    status_title = "GECİKMELİ İADE İŞLEMİ" if is_overdue else "ZAMANINDA İADE İŞLEMİ"

    badge_frame = ctk.CTkFrame(card, corner_radius=10, fg_color=status_bg)
    badge_frame.pack(fill="x", padx=18, pady=(16, 12))

    ctk.CTkLabel(
        badge_frame,
        text=f"{status_icon}  {status_title}",
        font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
        text_color=status_fg
    ).pack(pady=8)

    ctk.CTkLabel(
        card,
        text="🧾  İADE İŞLEM DEKONTU",
        font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        text_color="#ffffff"
    ).pack(pady=(0, 10))

    # Detaylar Tablosu (Grid Kartı)
    details_card = ctk.CTkFrame(card, corner_radius=10, fg_color="#0f172a")
    details_card.pack(fill="x", padx=18, pady=6)

    rows = [
        ("İşlem Kayıt No:", f"#{receipt.record.id}"),
        ("Kitap ID / Eser:", f"ID #{receipt.record.book_id}"),
        ("Toplam Ödünç Süresi:", f"{receipt.days_borrowed} Gün"),
        ("Standart Yasal Süre:", f"{BorrowService.STANDARD_LOAN_DAYS} Gün"),
        ("Gecikme Süresi:", f"{receipt.overdue_days} Gün"),
    ]

    for idx, (label_txt, val_txt) in enumerate(rows):
        row_frame = ctk.CTkFrame(details_card, fg_color="transparent")
        row_frame.pack(fill="x", padx=14, pady=3)
        ctk.CTkLabel(row_frame, text=label_txt, font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(side="left")
        ctk.CTkLabel(row_frame, text=val_txt, font=ctk.CTkFont(size=11, weight="bold"), text_color="#f8fafc").pack(side="right")

    # Ceza Tutarı Vurgu Kartı
    fee_card = ctk.CTkFrame(card, corner_radius=10, fg_color="#0f172a")
    fee_card.pack(fill="x", padx=18, pady=10)

    fee_header = ctk.CTkFrame(fee_card, fg_color="transparent")
    fee_header.pack(fill="x", padx=14, pady=(8, 2))
    ctk.CTkLabel(fee_header, text="HESAPLANAN GECİKME CEZASI:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94a3b8").pack(side="left")

    fee_color = "#ef4444" if is_overdue else "#10b981"
    ctk.CTkLabel(
        fee_card,
        text=f"{receipt.penalty_fee:.2f} TL",
        font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
        text_color=fee_color
    ).pack(anchor="w", padx=14, pady=(0, 8))

    # Mesaj
    ctk.CTkLabel(
        card,
        text=receipt.message,
        font=ctk.CTkFont(size=11, slant="italic"),
        text_color="#cbd5e1",
        wraplength=420
    ).pack(padx=18, pady=(0, 6))

    ctk.CTkLabel(
        card,
        text="Kitap tekrar kütüphane raflarına (AVAILABLE) alındı.",
        font=ctk.CTkFont(size=10),
        text_color="#64748b"
    ).pack(pady=(0, 10))

    # Kapat Butonu (Modern Mavi Kapsül Buton)
    btn_ok = ctk.CTkButton(
        card,
        text="🧾  Dekontu Kapat",
        width=150,
        height=38,
        corner_radius=19,
        fg_color="#2563eb",
        hover_color="#1d4ed8",
        font=ctk.CTkFont(size=12, weight="bold"),
        command=dialog.destroy
    )
    btn_ok.pack(side="bottom", pady=(0, 14))

    dialog.wait_window()


# =============================================================================
# CustomTkinter Ana Arayüz Penceresi
# =============================================================================
class LibraryApp(ctk.CTk):
    """
    CustomTkinter Kütüphane Yönetim Arayüzü
    ---------------------------------------
    Tasarım İlkesi: Modern Card-Based Dark Dashboard (Zero Light Popups)
    """

    def __init__(
        self,
        book_service: BookService,
        user_service: UserService,
        borrow_service: BorrowService
    ) -> None:
        """
        CustomTkinter Ana Pencere Yapıcı Metodu.
        OOP Karşılığı: Dependency Injection (Bağımlılık Enjeksiyonu)
        """
        super().__init__()

        # Servis Bağımlılıkları
        self.book_service: BookService = book_service
        self.user_service: UserService = user_service
        self.borrow_service: BorrowService = borrow_service

        # Pencere Boyut ve Konumlandırma
        self.title("Kütüphane Otomasyon Sistemi | N-Tier Mimari (CustomTkinter)")
        self.geometry("1200x780")
        self.minsize(1060, 700)

        # Tablo (Treeview) Koyu Tema Yapılandırması
        self._configure_treeview_dark_style()

        # Ana Bileşenleri Oluştur
        self._create_header()
        self._create_tabview()
        self._create_status_bar()

        # Verileri İlk Kez Yükle
        self.refresh_all_views()
        self.set_architecture_status("Sistem hazır. SQLite (kutuphane.db) ve CustomTkinter Dark Mode aktif.")

    # =========================================================================
    # Tablo (Treeview) Koyu Tema Ayarları
    # =========================================================================
    def _configure_treeview_dark_style(self) -> None:
        """ttk.Treeview bileşenini koyu tema paletiyle (#0f172a, #1e293b) uyumlu kılar."""
        self.style = ttk.Style(self)
        available_themes = self.style.theme_names()
        if "clam" in available_themes:
            self.style.theme_use("clam")

        TREE_BG = "#1e293b"        # Koyu Slate Kart Rengi
        TREE_HEADING = "#0f172a"   # Derin Lacivert Başlık
        TREE_FG = "#f8fafc"        # Açık Beyaz Metin
        TREE_SELECTED = "#2563eb"  # Mavi Seçim Rengi

        self.style.configure(
            "Treeview",
            font=("Segoe UI", 10),
            rowheight=30,
            background=TREE_BG,
            fieldbackground=TREE_BG,
            foreground=TREE_FG,
            borderwidth=0,
            relief="flat"
        )
        self.style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background=TREE_HEADING,
            foreground="#38bdf8",
            relief="flat",
            padding=[8, 8]
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", "#1e293b")]
        )
        self.style.map(
            "Treeview",
            background=[("selected", TREE_SELECTED)],
            foreground=[("selected", "#ffffff")]
        )

    # =========================================================================
    # 1. Üst Başlık Barı (Custom Header Bar)
    # =========================================================================
    def _create_header(self) -> None:
        """Pencerenin üstündeki modern koyu başlık paneli."""
        header_frame = ctk.CTkFrame(self, corner_radius=0, height=65, fg_color="#0f172a")
        header_frame.pack(fill="x", side="top")
        header_frame.pack_propagate(False)

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=10)

        lbl_title = ctk.CTkLabel(
            title_box,
            text="📚 KÜTÜPHANE YÖNETİM SİSTEMİ",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#ffffff"
        )
        lbl_title.pack(side="left", padx=(0, 12))

        lbl_badge = ctk.CTkLabel(
            title_box,
            text="N-Tier Architecture • CustomTkinter v6",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#38bdf8",
            fg_color="#1e293b",
            corner_radius=8,
            padx=10,
            pady=3
        )
        lbl_badge.pack(side="left")

        lbl_status = ctk.CTkLabel(
            header_frame,
            text="● SQLite: kutuphane.db  |  🟢 Çevrimiçi",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8"
        )
        lbl_status.pack(side="right", padx=24, pady=14)

    # =========================================================================
    # 2. Modern Sekmeli Yapı (CTkTabview)
    # =========================================================================
    def _create_tabview(self) -> None:
        """4 ana sekmeden oluşan CustomTkinter Tabview bileşeni."""
        self.tabview = ctk.CTkTabview(
            self,
            corner_radius=15,
            fg_color="#0f172a",
            segmented_button_fg_color="#1e293b",
            segmented_button_selected_color="#2563eb",
            segmented_button_selected_hover_color="#1d4ed8",
            segmented_button_unselected_hover_color="#334155",
            text_color="#ffffff"
        )
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(10, 12))

        # Sekmeleri Ekle
        self.tab_books = self.tabview.add("📖 Kitap Yönetimi")
        self.tab_members = self.tabview.add("👥 Üye & Personel Yönetimi")
        self.tab_borrows = self.tabview.add("🔄 Ödünç / İade İşlemleri")
        self.tab_reports = self.tabview.add("📊 Raporlar & Analitik")

        # Sekme İçeriklerini İnşa Et
        self._build_books_tab()
        self._build_members_tab()
        self._build_borrows_tab()
        self._build_reports_tab()

    # =========================================================================
    # 1. SEKME: KİTAP YÖNETİMİ
    # =========================================================================
    def _build_books_tab(self) -> None:
        """Kitap Ekleme Kartı ve Tablo Kartı."""
        card_form = ctk.CTkFrame(self.tab_books, corner_radius=15, fg_color="#1e293b", width=340)
        card_form.pack(side="left", fill="y", padx=(6, 12), pady=10)
        card_form.pack_propagate(False)

        ctk.CTkLabel(
            card_form,
            text="➕ Yeni Kitap Ekle",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#ffffff"
        ).pack(anchor="w", padx=16, pady=(16, 2))

        ctk.CTkLabel(
            card_form,
            text="Envantere yeni kitap kaydı oluşturun.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=16, pady=(0, 14))

        ctk.CTkLabel(card_form, text="Kitap Başlığı (*):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc").pack(anchor="w", padx=16, pady=(4, 2))
        self.entry_book_title = ctk.CTkEntry(card_form, placeholder_text="Örn: Nutuk", corner_radius=10, height=34)
        self.entry_book_title.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(card_form, text="Yazar (*):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc").pack(anchor="w", padx=16, pady=(4, 2))
        self.entry_book_author = ctk.CTkEntry(card_form, placeholder_text="Örn: Mustafa Kemal Atatürk", corner_radius=10, height=34)
        self.entry_book_author.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(card_form, text="ISBN Numarası (*):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc").pack(anchor="w", padx=16, pady=(4, 2))
        self.entry_book_isbn = ctk.CTkEntry(card_form, placeholder_text="Örn: 9789751600010", corner_radius=10, height=34)
        self.entry_book_isbn.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(card_form, text="Kategori:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc").pack(anchor="w", padx=16, pady=(4, 2))
        self.opt_book_category = ctk.CTkOptionMenu(
            card_form,
            values=["Edebiyat", "Bilim Kurgu", "Tarih", "Felsefe", "Bilim", "Genel"],
            corner_radius=10,
            height=34
        )
        self.opt_book_category.set("Edebiyat")
        self.opt_book_category.pack(fill="x", padx=16, pady=(0, 16))

        btn_add = ctk.CTkButton(
            card_form,
            text="✔  Kitabı Kaydet",
            corner_radius=10,
            height=36,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_click_add_book
        )
        btn_add.pack(fill="x", padx=16, pady=(4, 8))

        btn_clear = ctk.CTkButton(
            card_form,
            text="Formu Temizle",
            corner_radius=10,
            height=32,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=11),
            command=self._clear_book_form
        )
        btn_clear.pack(fill="x", padx=16)

        # Sağ Kart: Kitap Arama ve Tablo
        card_table = ctk.CTkFrame(self.tab_books, corner_radius=15, fg_color="#1e293b")
        card_table.pack(side="right", fill="both", expand=True, padx=(6, 6), pady=10)

        search_box = ctk.CTkFrame(card_table, fg_color="transparent")
        search_box.pack(fill="x", padx=16, pady=(14, 10))

        self.entry_book_search = ctk.CTkEntry(
            search_box,
            placeholder_text="Kitap adı, yazar veya kategori arayın...",
            corner_radius=10,
            height=34,
            width=320
        )
        self.entry_book_search.pack(side="left", padx=(0, 8))
        self.entry_book_search.bind("<Return>", lambda e: self._on_click_search_books())

        btn_search = ctk.CTkButton(
            search_box,
            text="🔍 Ara",
            width=80,
            height=34,
            corner_radius=10,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_click_search_books
        )
        btn_search.pack(side="left", padx=4)

        btn_reset = ctk.CTkButton(
            search_box,
            text="Tümünü Göster",
            width=110,
            height=34,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=11),
            command=self.load_books_table
        )
        btn_reset.pack(side="left", padx=4)

        table_container = tk.Frame(card_table, bg="#1e293b")
        table_container.pack(fill="both", expand=True, padx=16, pady=4)

        columns = ("id", "title", "author", "category", "isbn", "status")
        self.tree_books = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        self.tree_books.heading("id", text="ID")
        self.tree_books.heading("title", text="Kitap Başlığı")
        self.tree_books.heading("author", text="Yazar")
        self.tree_books.heading("category", text="Kategori")
        self.tree_books.heading("isbn", text="ISBN")
        self.tree_books.heading("status", text="Durum")

        self.tree_books.column("id", width=50, anchor=tk.CENTER)
        self.tree_books.column("title", width=230)
        self.tree_books.column("author", width=160)
        self.tree_books.column("category", width=120)
        self.tree_books.column("isbn", width=130, anchor=tk.CENTER)
        self.tree_books.column("status", width=95, anchor=tk.CENTER)

        self.tree_books.tag_configure("evenrow", background="#1e293b", foreground="#f8fafc")
        self.tree_books.tag_configure("oddrow", background="#0f172a", foreground="#f8fafc")

        scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree_books.yview)
        self.tree_books.configure(yscrollcommand=scroll_y.set)

        self.tree_books.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        bottom_box = ctk.CTkFrame(card_table, fg_color="transparent")
        bottom_box.pack(fill="x", padx=16, pady=(8, 12))

        btn_delete_book = ctk.CTkButton(
            bottom_box,
            text="🗑️  Seçili Kitabı Sil",
            corner_radius=10,
            height=34,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_click_delete_book
        )
        btn_delete_book.pack(side="right")

    # =========================================================================
    # 2. SEKME: ÜYE VE PERSONEL YÖNETİMİ
    # =========================================================================
    def _build_members_tab(self) -> None:
        """Kullanıcı Ekleme ve Kullanıcı Listesi Kartları."""
        card_form = ctk.CTkFrame(self.tab_members, corner_radius=15, fg_color="#1e293b", width=340)
        card_form.pack(side="left", fill="y", padx=(6, 12), pady=10)
        card_form.pack_propagate(False)

        ctk.CTkLabel(
            card_form,
            text="👤 Yeni Kullanıcı Kaydı",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#ffffff"
        ).pack(anchor="w", padx=16, pady=(16, 2))

        ctk.CTkLabel(
            card_form,
            text="Öğrenci veya Görevli personel ekleyin.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=16, pady=(0, 14))

        ctk.CTkLabel(card_form, text="Ad Soyad (*):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc").pack(anchor="w", padx=16, pady=(4, 2))
        self.entry_member_name = ctk.CTkEntry(card_form, placeholder_text="Örn: Ahmet Yılmaz", corner_radius=10, height=34)
        self.entry_member_name.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(card_form, text="E-posta Adresi (*):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc").pack(anchor="w", padx=16, pady=(4, 2))
        self.entry_member_email = ctk.CTkEntry(card_form, placeholder_text="Örn: ahmet@kutuphane.com", corner_radius=10, height=34)
        self.entry_member_email.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(card_form, text="Kullanıcı Rolü (*):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc").pack(anchor="w", padx=16, pady=(4, 2))
        self.opt_member_role = ctk.CTkOptionMenu(
            card_form,
            values=["Öğrenci / Üye (MEMBER)", "Kütüphaneci / Admin (LIBRARIAN)"],
            corner_radius=10,
            height=34,
            command=self._on_role_change
        )
        self.opt_member_role.set("Öğrenci / Üye (MEMBER)")
        self.opt_member_role.pack(fill="x", padx=16, pady=(0, 8))

        self.lbl_member_limit = ctk.CTkLabel(card_form, text="Maks Kitap Limiti (Üye İçin):", font=ctk.CTkFont(size=11), text_color="#cbd5e1")
        self.lbl_member_limit.pack(anchor="w", padx=16, pady=(2, 2))
        self.entry_member_limit = ctk.CTkEntry(card_form, placeholder_text="3", corner_radius=10, height=32)
        self.entry_member_limit.insert(0, "3")
        self.entry_member_limit.pack(fill="x", padx=16, pady=(0, 8))

        self.lbl_employee_id = ctk.CTkLabel(card_form, text="Personel Sicil No (Görevli İçin):", font=ctk.CTkFont(size=11), text_color="#cbd5e1")
        self.lbl_employee_id.pack(anchor="w", padx=16, pady=(2, 2))
        self.entry_employee_id = ctk.CTkEntry(card_form, placeholder_text="LIB-101", corner_radius=10, height=32)
        self.entry_employee_id.insert(0, "LIB-101")
        self.entry_employee_id.pack(fill="x", padx=16, pady=(0, 16))

        self._on_role_change()

        btn_add_user = ctk.CTkButton(
            card_form,
            text="✔  Kullanıcıyı Kaydet",
            corner_radius=10,
            height=36,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_click_add_member
        )
        btn_add_user.pack(fill="x", padx=16, pady=(4, 8))

        btn_clear_user = ctk.CTkButton(
            card_form,
            text="Formu Temizle",
            corner_radius=10,
            height=32,
            fg_color="#334155",
            hover_color="#475569",
            font=ctk.CTkFont(size=11),
            command=self._clear_member_form
        )
        btn_clear_user.pack(fill="x", padx=16)

        # Sağ Kart: Kullanıcı Tablosu
        card_table = ctk.CTkFrame(self.tab_members, corner_radius=15, fg_color="#1e293b")
        card_table.pack(side="right", fill="both", expand=True, padx=(6, 6), pady=10)

        top_bar = ctk.CTkFrame(card_table, fg_color="transparent")
        top_bar.pack(fill="x", padx=16, pady=(14, 10))

        ctk.CTkLabel(
            top_bar,
            text="👥  Sistemdeki Tüm Kullanıcılar (Üyeler ve Kütüphaneciler/Admin)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        ).pack(side="left")

        btn_refresh = ctk.CTkButton(
            top_bar,
            text="🔄 Yenile",
            width=90,
            height=32,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#475569",
            command=self.load_members_table
        )
        btn_refresh.pack(side="right")

        table_container = tk.Frame(card_table, bg="#1e293b")
        table_container.pack(fill="both", expand=True, padx=16, pady=4)

        columns = ("id", "name", "email", "role", "extra_info")
        self.tree_members = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        self.tree_members.heading("id", text="ID")
        self.tree_members.heading("name", text="Ad Soyad")
        self.tree_members.heading("email", text="E-posta Adresi")
        self.tree_members.heading("role", text="Sistem Rolü")
        self.tree_members.heading("extra_info", text="Detay (Aktif Ödünç / Sicil No)")

        self.tree_members.column("id", width=50, anchor=tk.CENTER)
        self.tree_members.column("name", width=200)
        self.tree_members.column("email", width=240)
        self.tree_members.column("role", width=150, anchor=tk.CENTER)
        self.tree_members.column("extra_info", width=180, anchor=tk.CENTER)

        self.tree_members.tag_configure("evenrow", background="#1e293b", foreground="#f8fafc")
        self.tree_members.tag_configure("oddrow", background="#0f172a", foreground="#f8fafc")

        scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree_members.yview)
        self.tree_members.configure(yscrollcommand=scroll_y.set)

        self.tree_members.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

        bottom_box = ctk.CTkFrame(card_table, fg_color="transparent")
        bottom_box.pack(fill="x", padx=16, pady=(8, 12))

        btn_delete_user = ctk.CTkButton(
            bottom_box,
            text="🗑️  Seçili Kullanıcıyı Sil",
            corner_radius=10,
            height=34,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_click_delete_member
        )
        btn_delete_user.pack(side="right")

    def _on_role_change(self, choice: Optional[str] = None) -> None:
        """Rol değiştiğinde ilgili girdi alanlarını yönetir."""
        role_selected = self.opt_member_role.get()
        if "LIBRARIAN" in role_selected:
            self.entry_member_limit.configure(state="disabled", fg_color="#334155")
            self.entry_employee_id.configure(state="normal", fg_color="#1e293b")
        else:
            self.entry_member_limit.configure(state="normal", fg_color="#1e293b")
            self.entry_employee_id.configure(state="disabled", fg_color="#334155")

    # =========================================================================
    # 3. SEKME: ÖDÜNÇ VE İADE İŞLEMLERİ
    # =========================================================================
    def _build_borrows_tab(self) -> None:
        """Ödünç Verme Kartı, İade Kartı ve Aktif Ödünçler Tablosu."""
        top_box = ctk.CTkFrame(self.tab_borrows, fg_color="transparent")
        top_box.pack(fill="x", padx=6, pady=(6, 12))

        # Sol Kart: Ödünç Verme
        card_borrow = ctk.CTkFrame(top_box, corner_radius=15, fg_color="#1e293b")
        card_borrow.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            card_borrow,
            text="🤝  Kitap Ödünç Verme",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#ffffff"
        ).pack(anchor="w", padx=16, pady=(14, 2))

        ctk.CTkLabel(
            card_borrow,
            text="Maksimum 3 kitap limiti ve rafta kontrolü yapılır.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        ctk.CTkLabel(card_borrow, text="Kitabı Alacak Üye:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc").pack(anchor="w", padx=16, pady=(2, 2))
        self.opt_borrow_member = ctk.CTkOptionMenu(card_borrow, values=["Üye Seçiniz"], corner_radius=10, height=34)
        self.opt_borrow_member.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(card_borrow, text="Ödünç Verilecek Kitap (Raftakiler):", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f8fafc").pack(anchor="w", padx=16, pady=(2, 2))
        self.opt_borrow_book = ctk.CTkOptionMenu(card_borrow, values=["Kitap Seçiniz"], corner_radius=10, height=34)
        self.opt_borrow_book.pack(fill="x", padx=16, pady=(0, 14))

        btn_borrow = ctk.CTkButton(
            card_borrow,
            text="Kitabı Ödünç Ver",
            corner_radius=10,
            height=36,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_click_borrow_book
        )
        btn_borrow.pack(fill="x", padx=16, pady=(0, 14))

        # Sağ Kart: İade Alma ve Ceza Simülatörü
        card_return = ctk.CTkFrame(top_box, corner_radius=15, fg_color="#1e293b")
        card_return.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ctk.CTkLabel(
            card_return,
            text="↩️  Kitap İade Alma ve Ceza Hesabı",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#ffffff"
        ).pack(anchor="w", padx=16, pady=(14, 2))

        ctk.CTkLabel(
            card_return,
            text="Standart süre: 14 gün. Ceza: 5.0 TL / gecikilen gün.",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        ctk.CTkLabel(
            card_return,
            text="Gecikme Simülasyonu (Gün):",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f8fafc"
        ).pack(anchor="w", padx=16, pady=(2, 2))

        ctk.CTkLabel(
            card_return,
            text="* İade sürecine eklenecek ek gecikme gün sayısı (varsayılan: 0):",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=16)

        self.entry_sim_days = ctk.CTkEntry(card_return, placeholder_text="0", corner_radius=10, height=32, width=120)
        self.entry_sim_days.insert(0, "0")
        self.entry_sim_days.pack(anchor="w", padx=16, pady=(4, 14))

        btn_return = ctk.CTkButton(
            card_return,
            text="Seçili Kitabı İade Al",
            corner_radius=10,
            height=36,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_click_return_book
        )
        btn_return.pack(fill="x", padx=16, pady=(0, 14))

        # Alt Kart: Aktif Ödünçler Tablosu
        card_active = ctk.CTkFrame(self.tab_borrows, corner_radius=15, fg_color="#1e293b")
        card_active.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        ctk.CTkLabel(
            card_active,
            text="📋  İade Bekleyen Aktif Ödünç Kayıtları",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff"
        ).pack(anchor="w", padx=16, pady=(12, 8))

        table_container = tk.Frame(card_active, bg="#1e293b")
        table_container.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        columns = ("record_id", "member_name", "book_title", "borrow_date", "allowed_days", "status")
        self.tree_active_borrows = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        self.tree_active_borrows.heading("record_id", text="Kayıt ID")
        self.tree_active_borrows.heading("member_name", text="Ödünç Alan Üye")
        self.tree_active_borrows.heading("book_title", text="Kitap Adı")
        self.tree_active_borrows.heading("borrow_date", text="Ödünç Tarihi")
        self.tree_active_borrows.heading("allowed_days", text="Standart Süre")
        self.tree_active_borrows.heading("status", text="Durum")

        self.tree_active_borrows.column("record_id", width=65, anchor=tk.CENTER)
        self.tree_active_borrows.column("member_name", width=220)
        self.tree_active_borrows.column("book_title", width=260)
        self.tree_active_borrows.column("borrow_date", width=140, anchor=tk.CENTER)
        self.tree_active_borrows.column("allowed_days", width=110, anchor=tk.CENTER)
        self.tree_active_borrows.column("status", width=95, anchor=tk.CENTER)

        self.tree_active_borrows.tag_configure("evenrow", background="#1e293b", foreground="#f8fafc")
        self.tree_active_borrows.tag_configure("oddrow", background="#0f172a", foreground="#f8fafc")

        scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree_active_borrows.yview)
        self.tree_active_borrows.configure(yscrollcommand=scroll_y.set)

        self.tree_active_borrows.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    # =========================================================================
    # 4. SEKME: RAPORLAR VE ANALİTİK
    # =========================================================================
    def _build_reports_tab(self) -> None:
        """Koyu Tema KPI Kartları ve Geçmiş Tablosu."""
        stats_box = ctk.CTkFrame(self.tab_reports, fg_color="transparent")
        stats_box.pack(fill="x", padx=6, pady=(6, 12))

        self.card_total_books = self._create_kpi_card(stats_box, "Toplam Kitap", "0", "#2563eb", "📚")
        self.card_available_books = self._create_kpi_card(stats_box, "Raftaki Kitaplar", "0", "#059669", "📗")
        self.card_borrowed_books = self._create_kpi_card(stats_box, "Ödünçteki Kitaplar", "0", "#dc2626", "📕")
        self.card_total_members = self._create_kpi_card(stats_box, "Toplam Kullanıcı", "0", "#6366f1", "👥")

        card_history = ctk.CTkFrame(self.tab_reports, corner_radius=15, fg_color="#1e293b")
        card_history.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        top_filter = ctk.CTkFrame(card_history, fg_color="transparent")
        top_filter.pack(fill="x", padx=16, pady=(12, 10))

        ctk.CTkLabel(
            top_filter,
            text="Kayıt Filtresi:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff"
        ).pack(side="left", padx=(0, 8))

        self.opt_history_filter = ctk.CTkOptionMenu(
            top_filter,
            values=["Tümü (Geçmiş + Aktif)", "Yalnızca Aktif Ödünçler", "Yalnızca İade Edilenler"],
            corner_radius=10,
            height=32,
            width=220,
            command=lambda v: self.load_history_table()
        )
        self.opt_history_filter.set("Tümü (Geçmiş + Aktif)")
        self.opt_history_filter.pack(side="left", padx=4)

        btn_refresh_hist = ctk.CTkButton(
            top_filter,
            text="🔄 Raporu Güncelle",
            width=130,
            height=32,
            corner_radius=10,
            fg_color="#334155",
            hover_color="#475569",
            command=self.load_history_table
        )
        btn_refresh_hist.pack(side="right")

        table_container = tk.Frame(card_history, bg="#1e293b")
        table_container.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        columns = ("id", "member", "book", "borrow_date", "return_date", "status")
        self.tree_history = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="browse")

        self.tree_history.heading("id", text="İşlem ID")
        self.tree_history.heading("member", text="Üye")
        self.tree_history.heading("book", text="Kitap")
        self.tree_history.heading("borrow_date", text="Alış Tarihi")
        self.tree_history.heading("return_date", text="İade Tarihi")
        self.tree_history.heading("status", text="Durum")

        self.tree_history.column("id", width=65, anchor=tk.CENTER)
        self.tree_history.column("member", width=220)
        self.tree_history.column("book", width=260)
        self.tree_history.column("borrow_date", width=140, anchor=tk.CENTER)
        self.tree_history.column("return_date", width=140, anchor=tk.CENTER)
        self.tree_history.column("status", width=105, anchor=tk.CENTER)

        self.tree_history.tag_configure("evenrow", background="#1e293b", foreground="#f8fafc")
        self.tree_history.tag_configure("oddrow", background="#0f172a", foreground="#f8fafc")

        scroll_y = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree_history.yview)
        self.tree_history.configure(yscrollcommand=scroll_y.set)

        self.tree_history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)

    def _create_kpi_card(
        self,
        parent: ctk.CTkFrame,
        title: str,
        value: str,
        accent_color: str,
        icon: str
    ) -> ctk.CTkLabel:
        """Koyu Temalı Modern KPI Kartı."""
        card = ctk.CTkFrame(parent, corner_radius=15, fg_color="#1e293b")
        card.pack(side="left", fill="x", expand=True, padx=4)

        top_row = ctk.CTkFrame(card, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 0))

        ctk.CTkLabel(
            top_row,
            text=f"{icon}  {title}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        ).pack(side="left")

        lbl_val = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=accent_color
        )
        lbl_val.pack(anchor="w", padx=16, pady=(4, 12))
        return lbl_val

    # =========================================================================
    # 5. Alt Mimari Durum Çubuğu
    # =========================================================================
    def _create_status_bar(self) -> None:
        """Alt kısımdaki parlak konsol şeridi."""
        status_frame = ctk.CTkFrame(self, corner_radius=0, height=32, fg_color="#0f172a")
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)

        self.lbl_architecture_status = ctk.CTkLabel(
            status_frame,
            text="[MİMARİ AKIŞ]: Sistem hazır.",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color="#38bdf8"
        )
        self.lbl_architecture_status.pack(side="left", padx=16, pady=4)

    def set_architecture_status(self, text: str) -> None:
        """Durum çubuğuna mimari akış bilgisini yazar."""
        self.lbl_architecture_status.configure(text=f">> [MİMARİ AKIŞ]: {text}")

    # =========================================================================
    # Veri Yükleme ve Senkronizasyon (Data Loaders)
    # =========================================================================
    def refresh_all_views(self) -> None:
        """Tüm sekmelerdeki verileri veritabanından çekerek günceller."""
        self.load_books_table()
        self.load_members_table()
        self.load_active_borrows_table()
        self.load_borrow_comboboxes()
        self.load_history_table()
        self.update_kpi_cards()

    def load_books_table(self, books: Optional[List[Book]] = None) -> None:
        """Kitap listesini `BookService.get_all_books()` üzerinden çeker ve tabloya basar."""
        for item in self.tree_books.get_children():
            self.tree_books.delete(item)

        book_list = books if books is not None else self.book_service.get_all_books()

        for idx, b in enumerate(book_list):
            status_tr = "Rafta" if b.status == BookStatus.AVAILABLE else "ÖDÜNÇTE"
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.tree_books.insert(
                "",
                tk.END,
                values=(b.id, b.title, b.author, b.category, b.isbn, status_tr),
                tags=(tag,)
            )

    def load_members_table(self) -> None:
        """Sistemdeki tüm kullanıcıları polimorfik olarak listeler."""
        for item in self.tree_members.get_children():
            self.tree_members.delete(item)

        users = self.user_service.list_all_users()
        for idx, u in enumerate(users):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            if isinstance(u, Member):
                role_display = "Öğrenci Üye (MEMBER)"
                extra_info = f"Aktif Ödünç: {len(u.active_borrows)}/{u.max_book_limit}"
            elif isinstance(u, Librarian):
                role_display = "Kütüphaneci / Admin"
                extra_info = f"Sicil No: {u.employee_id}"
            else:
                role_display = u.role
                extra_info = "-"

            self.tree_members.insert(
                "",
                tk.END,
                values=(u.id, u.name, u.email, role_display, extra_info),
                tags=(tag,)
            )

    def load_active_borrows_table(self) -> None:
        """İade bekleyen aktif ödünçleri tabloya doldurur."""
        for item in self.tree_active_borrows.get_children():
            self.tree_active_borrows.delete(item)

        all_records = self.borrow_service.get_all_borrow_history()
        active_records = [r for r in all_records if r.is_active()]

        for idx, r in enumerate(active_records):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            try:
                user = self.user_service.get_user_by_id(r.member_id)
                member_name = f"{user.name} (ID: {user.id})"
            except Exception:
                member_name = f"Üye #{r.member_id}"

            try:
                book = self.book_service.get_book_by_id(r.book_id)
                book_title = f"{book.title} (ID: {book.id})"
            except Exception:
                book_title = f"Kitap #{r.book_id}"

            borrow_date_str = r.borrow_date.strftime("%Y-%m-%d %H:%M")
            self.tree_active_borrows.insert(
                "",
                tk.END,
                values=(r.id, member_name, book_title, borrow_date_str, f"{BorrowService.STANDARD_LOAN_DAYS} Gün", "AKTİF"),
                tags=(tag,)
            )

    def load_borrow_comboboxes(self) -> None:
        """Ödünç verme sekmesindeki üye ve müsait kitap listelerini günceller."""
        members = self.user_service.list_members()
        member_options = [f"{m.id} - {m.name} (Aktif: {len(m.active_borrows)}/{m.max_book_limit})" for m in members]
        if member_options:
            self.opt_borrow_member.configure(values=member_options)
            self.opt_borrow_member.set(member_options[0])
        else:
            self.opt_borrow_member.configure(values=["Kayıtlı üye bulunmuyor"])
            self.opt_borrow_member.set("Kayıtlı üye bulunmuyor")

        available_books = [b for b in self.book_service.get_all_books() if b.is_available()]
        book_options = [f"{b.id} - {b.title} [{b.category}]" for b in available_books]
        if book_options:
            self.opt_borrow_book.configure(values=book_options)
            self.opt_borrow_book.set(book_options[0])
        else:
            self.opt_borrow_book.configure(values=["Müsait kitap bulunmuyor"])
            self.opt_borrow_book.set("Müsait kitap bulunmuyor")

    def load_history_table(self) -> None:
        """Geçmiş ödünç hareketleri tablosunu filtreye göre günceller."""
        for item in self.tree_history.get_children():
            self.tree_history.delete(item)

        records = self.borrow_service.get_all_borrow_history()
        filter_mode = self.opt_history_filter.get().strip()

        if filter_mode == "Yalnızca Aktif Ödünçler":
            records = [r for r in records if r.is_active()]
        elif filter_mode == "Yalnızca İade Edilenler":
            records = [r for r in records if not r.is_active()]

        for idx, r in enumerate(records):
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            try:
                user = self.user_service.get_user_by_id(r.member_id)
                member_name = user.name
            except Exception:
                member_name = f"Üye #{r.member_id}"

            try:
                book = self.book_service.get_book_by_id(r.book_id)
                book_title = book.title
            except Exception:
                book_title = f"Kitap #{r.book_id}"

            borrow_str = r.borrow_date.strftime("%Y-%m-%d %H:%M")
            return_str = r.return_date.strftime("%Y-%m-%d %H:%M") if r.return_date else "Henüz Teslim Edilmedi"
            status_str = "AKTİF" if r.is_active() else "İADE EDİLDİ"

            self.tree_history.insert(
                "",
                tk.END,
                values=(r.id, member_name, book_title, borrow_str, return_str, status_str),
                tags=(tag,)
            )

    def update_kpi_cards(self) -> None:
        """Raporlar sekmesindeki sayısal istatistik kutularını günceller."""
        all_books = self.book_service.get_all_books()
        available_count = sum(1 for b in all_books if b.is_available())
        borrowed_count = len(all_books) - available_count
        users_count = len(self.user_service.list_all_users())

        self.card_total_books.configure(text=str(len(all_books)))
        self.card_available_books.configure(text=str(available_count))
        self.card_borrowed_books.configure(text=str(borrowed_count))
        self.card_total_members.configure(text=str(users_count))

    # =========================================================================
    # Olay Yöneticileri (Event Handlers)
    # =========================================================================
    def _on_click_add_book(self) -> None:
        """Yeni Kitap Ekle Butonu."""
        title = self.entry_book_title.get()
        author = self.entry_book_author.get()
        isbn = self.entry_book_isbn.get()
        category = self.opt_book_category.get()

        self.set_architecture_status(
            "UI (CustomTkinter) -> BookService.add_book() -> BookRepository.add() -> SQLite (kutuphane.db)"
        )

        try:
            new_book = self.book_service.add_book(
                title=title,
                author=author,
                isbn=isbn,
                category=category
            )
            show_custom_message(
                self,
                title="Kitap Kaydedildi",
                message=f"Kitap envantere başarıyla eklendi!\n\nID: #{new_book.id}\nBaşlık: '{new_book.title}'\nYazar: {new_book.author}\nKategori: {new_book.category}",
                msg_type="success"
            )
            self._clear_book_form()
            self.refresh_all_views()
        except ValueError as err:
            show_custom_message(self, title="İş Kuralı İhlali", message=str(err), msg_type="error")

    def _on_click_delete_book(self) -> None:
        """Kitap Sil Butonu."""
        selected = self.tree_books.selection()
        if not selected:
            show_custom_message(self, title="Seçim Yapılmadı", message="Lütfen silmek istediğiniz kitabı tablodan seçiniz.", msg_type="warning")
            return

        values = self.tree_books.item(selected[0], "values")
        book_id = int(values[0])
        book_title = values[1]

        confirm = show_custom_confirm(
            self,
            title="Kitap Silme Onayı",
            message=f"'{book_title}' (ID: #{book_id}) adlı eseri kütüphaneden tamamen silmek istediğinize emin misiniz?"
        )
        if not confirm:
            return

        self.set_architecture_status(
            f"UI -> BookService.delete_book({book_id}) -> [Ödünç Kontrolü] -> BookRepository.delete()"
        )

        try:
            self.book_service.delete_book(book_id)
            show_custom_message(self, title="Kitap Silindi", message=f"'{book_title}' kitabı sistemden başarıyla silindi.", msg_type="success")
            self.refresh_all_views()
        except ValueError as err:
            show_custom_message(self, title="Silme Engellendi", message=str(err), msg_type="error")

    def _on_click_search_books(self) -> None:
        """Kitap Arama Butonu."""
        query = self.entry_book_search.get()
        self.set_architecture_status(f"UI -> BookService.search_books('{query}') -> BookRepository (SQL LIKE)")
        results = self.book_service.search_books(query)
        self.load_books_table(results)

    def _clear_book_form(self) -> None:
        """Kitap formunu temizler."""
        self.entry_book_title.delete(0, "end")
        self.entry_book_author.delete(0, "end")
        self.entry_book_isbn.delete(0, "end")
        self.opt_book_category.set("Edebiyat")

    def _on_click_add_member(self) -> None:
        """Yeni Kullanıcı Ekleme Butonu."""
        name = self.entry_member_name.get()
        email = self.entry_member_email.get()
        role_selection = self.opt_member_role.get()

        try:
            if "LIBRARIAN" in role_selection:
                employee_id = self.entry_employee_id.get().strip()
                self.set_architecture_status(
                    "UI -> UserService.register_librarian() -> UserRepository.add() (Role=LIBRARIAN)"
                )
                new_user = self.user_service.register_librarian(
                    name=name,
                    email=email,
                    employee_id=employee_id
                )
                show_custom_message(
                    self,
                    title="Personel Kaydedildi",
                    message=f"Kütüphaneci / Admin personeli sisteme eklendi!\n\nID: #{new_user.id}\nAd: {new_user.name}\nSicil No: {new_user.employee_id}",
                    msg_type="success"
                )
            else:
                try:
                    limit = int(self.entry_member_limit.get())
                except ValueError:
                    limit = 3

                self.set_architecture_status(
                    "UI -> UserService.register_member() -> UserRepository.add() (Role=MEMBER)"
                )
                new_user = self.user_service.register_member(
                    name=name,
                    email=email,
                    max_book_limit=limit
                )
                show_custom_message(
                    self,
                    title="Üye Kaydedildi",
                    message=f"Öğrenci / Üye başarıyla kaydedildi!\n\nID: #{new_user.id}\nAd: {new_user.name}\nLimit: {new_user.max_book_limit} Kitap",
                    msg_type="success"
                )

            self._clear_member_form()
            self.refresh_all_views()
        except ValueError as err:
            show_custom_message(self, title="İş Kuralı İhlali", message=str(err), msg_type="error")

    def _on_click_delete_member(self) -> None:
        """Kullanıcı Sil Butonu."""
        selected = self.tree_members.selection()
        if not selected:
            show_custom_message(self, title="Seçim Yapılmadı", message="Lütfen silmek istediğiniz kullanıcıyı tablodan seçiniz.", msg_type="warning")
            return

        values = self.tree_members.item(selected[0], "values")
        member_id = int(values[0])
        member_name = values[1]

        confirm = show_custom_confirm(
            self,
            title="Kullanıcı Silme Onayı",
            message=f"'{member_name}' (ID: #{member_id}) isimli kullanıcıyı sistemden silmek istiyor musunuz?"
        )
        if not confirm:
            return

        self.set_architecture_status(
            f"UI -> UserService.delete_user({member_id}) -> [Aktif Kitap Kontrolü] -> UserRepository.delete()"
        )

        try:
            self.user_service.delete_user(member_id)
            show_custom_message(self, title="Kullanıcı Silindi", message=f"'{member_name}' kullanıcısı sistemden başarıyla silindi.", msg_type="success")
            self.refresh_all_views()
        except ValueError as err:
            show_custom_message(self, title="Silme Engellendi", message=str(err), msg_type="error")

    def _clear_member_form(self) -> None:
        """Kullanıcı formunu temizler."""
        self.entry_member_name.delete(0, "end")
        self.entry_member_email.delete(0, "end")
        self.opt_member_role.set("Öğrenci / Üye (MEMBER)")
        self.entry_member_limit.delete(0, "end")
        self.entry_member_limit.insert(0, "3")
        self.entry_employee_id.delete(0, "end")
        self.entry_employee_id.insert(0, "LIB-101")
        self._on_role_change()

    def _on_click_borrow_book(self) -> None:
        """Kitap Ödünç Verme Butonu."""
        member_text = self.opt_borrow_member.get()
        book_text = self.opt_borrow_book.get()

        if not member_text or not book_text or "bulunmuyor" in book_text or "Seçiniz" in member_text:
            show_custom_message(self, title="Eksik Seçim", message="Lütfen geçerli bir üye ve müsait bir kitap seçiniz.", msg_type="warning")
            return

        try:
            member_id = int(member_text.split(" - ")[0])
            book_id = int(book_text.split(" - ")[0])
        except Exception:
            show_custom_message(self, title="Biçim Hatası", message="Seçim formatı anlaşılamadı.", msg_type="error")
            return

        self.set_architecture_status(
            f"UI -> BorrowService.borrow_book(member={member_id}, book={book_id}) -> "
            "[1. Limit Doldu mu? 2. Kitap Rafta mı?] -> BookRepo & BorrowRepo"
        )

        try:
            record = self.borrow_service.borrow_book(member_id=member_id, book_id=book_id)
            show_custom_message(
                self,
                title="Ödünç Verme Başarılı",
                message=(
                    f"Kitap üyeye başarıyla ödünç verildi!\n\n"
                    f"İşlem Kayıt No : #{record.id}\n"
                    f"Ödünç Tarihi   : {record.borrow_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Yasal İade Süresi: {BorrowService.STANDARD_LOAN_DAYS} Gün\n"
                    f"Gecikme Cezası : {BorrowService.DAILY_PENALTY_RATE} TL / gün"
                ),
                msg_type="success"
            )
            self.refresh_all_views()
        except ValueError as err:
            show_custom_message(self, title="Ödünç Verme Engellendi", message=str(err), msg_type="error")

    def _on_click_return_book(self) -> None:
        """Kitap İade Alma ve Ceza Hesaplama Butonu."""
        selected = self.tree_active_borrows.selection()
        if not selected:
            show_custom_message(self, title="Seçim Yapılmadı", message="Lütfen iade edilecek aktif ödünç kaydını tablodan seçiniz.", msg_type="warning")
            return

        values = self.tree_active_borrows.item(selected[0], "values")
        borrow_id = int(values[0])

        try:
            sim_days = int(self.entry_sim_days.get().strip())
        except ValueError:
            sim_days = 0

        simulated_date: Optional[datetime] = None
        if sim_days > 0:
            rec = self.borrow_service._borrow_repo.get_by_id(borrow_id)
            if rec:
                simulated_date = rec.borrow_date + timedelta(days=sim_days)

        self.set_architecture_status(
            f"UI -> BorrowService.return_book(borrow_id={borrow_id}, sim_days={sim_days}) -> "
            "[Ceza Hesabı] -> BorrowRepo.update(RETURNED) & BookRepo.update(AVAILABLE)"
        )

        try:
            receipt: ReturnReceipt = self.borrow_service.return_book(borrow_id=borrow_id, return_date=simulated_date)
            # Modern Koyu Temalı Özel Makbuz/Dekont Penceresini Aç
            show_return_receipt_modal(self, receipt)

            self.entry_sim_days.delete(0, "end")
            self.entry_sim_days.insert(0, "0")
            self.refresh_all_views()
        except ValueError as err:
            show_custom_message(self, title="İade Hatası", message=str(err), msg_type="error")


# =============================================================================
# Ana Giriş Noktası (Composition Root / Application Startup)
# =============================================================================
def main() -> None:
    """
    Uygulamanın Başlatıcı Fonksiyonu.

    Mimari Akış (N-Tier Orchestration):
    1. Veritabanı Yöneticisi ayağa kalkar, 'kutuphane.db' dosyası kontrol edilir.
    2. Tablolar oluşturulur ve boşsa örnek veriler (Seed Data) aktarılır.
    3. Veri Erişim Katmanı (Repositories) nesneleri oluşturulur.
    4. İş Mantığı Katmanı (Services) bağımlılıklarla başlatılır.
    5. CustomTkinter Dark Mode GUI açılarak modern masaüstü arayüzü ekrana getirilir.
    """
    print("[MİMARİ] 1. Katman: SQLite Veritabanı (kutuphane.db) hazırlanıyor...")
    db_manager = DatabaseManager("kutuphane.db")
    db_manager.initialize_tables()
    db_manager.seed_initial_data()

    print("[MİMARİ] 2. Katman: Veri Erişim Katmanı (Repositories) başlatılıyor...")
    book_repo = BookRepository(db_manager)
    user_repo = UserRepository(db_manager)
    borrow_repo = BorrowRepository(db_manager)

    print("[MİMARİ] 3. Katman: İş Mantığı Katmanı (Services) başlatılıyor...")
    book_service = BookService(book_repo)
    user_service = UserService(user_repo, borrow_repo)
    borrow_service = BorrowService(borrow_repo, book_repo, user_repo)

    print("[MİMARİ] 4. Katman: Sunum Katmanı (CustomTkinter Dark Dashboard) başlatılıyor...")
    app = LibraryApp(
        book_service=book_service,
        user_service=user_service,
        borrow_service=borrow_service
    )
    app.mainloop()


if __name__ == "__main__":
    main()
