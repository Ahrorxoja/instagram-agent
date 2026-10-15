import os
import logging
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from app.config import settings

logger = logging.getLogger(__name__)

HEADERS = [
    "ID",
    "Ism",
    "Instagram",
    "Telefon raqam",
    "Telegramda mavjud",
    "Telegram Username",
    "Telegram ID",
    "Xabar yuborildi",    # Dropdown: Ha, Yo'q
    "Telefon qilindi",    # Dropdown: Ha, Yo'q
    "Holati (Status)",     # Dropdown: Yangi, Javob berdi, Rad etildi, Sotildi
    "Izoh (Notes)",
    "Qo'shilgan sana"
]

def apply_styles_and_validation(ws):
    """
    Excel jadvaliga:
    1. Dropdown (Data Validation) - Ha/Yo'q va Status
    2. Sarlavha dizayni (rang, qalin shrift)
    3. Ustun kengliklarini moslash
    """
    # 1. Sarlavha stili
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for col_num in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    # 2. Dropdown (Data Validation) yaratish
    # Ha/Yo'q tanlovi (8-ustun: Xabar yuborildi, 9-ustun: Telefon qilindi)
    dv_yes_no = DataValidation(
        type="list",
        formula1='"Ha,Yo\'q"',
        allow_blank=True,
        showDropDown=False
    )
    dv_yes_no.error = "Faqat 'Ha' yoki 'Yo\'q' ni tanlashingiz mumkin"
    dv_yes_no.errorTitle = "Noto'g'ri qiymat"
    dv_yes_no.prompt = "Ro'yxatdan 'Ha' yoki 'Yo\'q' ni tanlang"
    dv_yes_no.promptTitle = "Tanlov"

    ws.add_data_validation(dv_yes_no)
    dv_yes_no.add("H2:H5000")  # Xabar yuborildi
    dv_yes_no.add("I2:I5000")  # Telefon qilindi

    # Status tanlovi (10-ustun)
    dv_status = DataValidation(
        type="list",
        formula1='"Yangi,Javob berdi,Rad etildi,Sotildi,Bog\'lanib bo\'lmadi"',
        allow_blank=True,
        showDropDown=False
    )
    dv_status.error = "Ro'yxatdagi mavjud holatlardan birini tanlang"
    dv_status.errorTitle = "Noto'g'ri status"
    ws.add_data_validation(dv_status)
    dv_status.add("J2:J5000")

    # 3. Ustun kengliklarini avtomatik sozlash
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val = str(cell.value or "")
            if len(val) > max_len:
                max_len = len(val)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

def ensure_excel_file():
    """Excel fayli mavjudligini ta'minlash, yo'q bo'lsa sarlavhalar va dropdownlar bilan yaratish"""
    file_path = settings.EXCEL_FILE_PATH
    if not os.path.exists(file_path):
        wb = Workbook()
        ws = wb.active
        ws.title = "Mijozlar"
        ws.append(HEADERS)
        apply_styles_and_validation(ws)
        wb.save(file_path)
        logger.info(f"Yangi Excel fayl yaratildi: {file_path}")

def append_lead_to_excel(lead_dict: dict):
    """Yangi leadni Excel fayliga qo'shish"""
    try:
        ensure_excel_file()
        file_path = settings.EXCEL_FILE_PATH
        wb = load_workbook(file_path)
        ws = wb["Mijozlar"]
        
        row = [
            lead_dict.get("id"),
            lead_dict.get("full_name"),
            lead_dict.get("instagram_username") or "-",
            lead_dict.get("phone_number"),
            "Ha" if lead_dict.get("telegram_found") else "Yo'q",
            f"@{lead_dict.get('telegram_username')}" if lead_dict.get("telegram_username") else "-",
            lead_dict.get("telegram_id") or "-",
            "Ha" if lead_dict.get("message_sent") else "Yo'q",
            "Ha" if lead_dict.get("phone_called") else "Yo'q",
            lead_dict.get("status") or "Yangi",
            lead_dict.get("notes") or "",
            lead_dict.get("created_at") or "-"
        ]
        ws.append(row)

        # Qator katakchalarini tekislash
        current_row = ws.max_row
        center_align = Alignment(horizontal="center", vertical="center")
        for col_idx in [1, 4, 5, 7, 8, 9, 10, 12]:
            ws.cell(row=current_row, column=col_idx).alignment = center_align

        wb.save(file_path)
        logger.info(f"Lead ID {lead_dict.get('id')} Excelga saqlandi.")
    except Exception as e:
        logger.error(f"Excelga yozishda xatolik: {e}")

def update_lead_in_excel(lead_id: int, status: str = None, message_sent: bool = None, phone_called: bool = None):
    """Exceldagi mavjud mijoz holatini yangilash"""
    try:
        file_path = settings.EXCEL_FILE_PATH
        if not os.path.exists(file_path):
            return
        wb = load_workbook(file_path)
        ws = wb["Mijozlar"]
        
        for row in range(2, ws.max_row + 1):
            if ws.cell(row=row, column=1).value == lead_id:
                if message_sent is not None:
                    ws.cell(row=row, column=8, value="Ha" if message_sent else "Yo'q")
                if phone_called is not None:
                    ws.cell(row=row, column=9, value="Ha" if phone_called else "Yo'q")
                if status is not None:
                    ws.cell(row=row, column=10, value=status)
                break
        wb.save(file_path)
    except Exception as e:
        logger.error(f"Excelni yangilashda xatolik: {e}")
