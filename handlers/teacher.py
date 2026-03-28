import io
from datetime import date, datetime
from itertools import groupby

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_IDS
from keyboards import teacher_menu_keyboard, admin_menu_keyboard
from states import TeacherReport

router = Router()


# ── Ruxsat tekshiruvi ──────────────────────────────────────────────────────────

async def check_teacher(message: Message) -> bool:
    user = await db.get_user(message.from_user.id)
    return message.from_user.id in ADMIN_IDS or (
        user is not None and user["role"] in ("teacher", "admin")
    )


async def get_menu(message: Message):
    user = await db.get_user(message.from_user.id)
    if message.from_user.id in ADMIN_IDS or (user and user["role"] == "admin"):
        return admin_menu_keyboard()
    return teacher_menu_keyboard()


def parse_date(date_str: str) -> date | None:
    try:
        return datetime.strptime(date_str.strip(), "%d.%m.%Y").date()
    except ValueError:
        try:
            return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None


# ── Excel yaratish ─────────────────────────────────────────────────────────────

def build_excel(target_date: date, students: list[dict], class_name: str | None = None) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    title_suffix = f" — {class_name}" if class_name else ""
    ws.title = f"{target_date}{title_suffix}"[:31]

    HDR_FONT  = Font(bold=True, color="FFFFFF", size=11)
    HDR_FILL  = PatternFill(start_color="1A3C5E", end_color="1A3C5E", fill_type="solid")
    ALT_FILL  = PatternFill(start_color="EAF3FB", end_color="EAF3FB", fill_type="solid")
    TITLE_FONT = Font(bold=True, size=13, color="1A3C5E")
    CENTER    = Alignment(horizontal="center", vertical="center", wrap_text=True)
    LEFT      = Alignment(horizontal="left",   vertical="center", wrap_text=True)
    THIN      = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"),  bottom=Side(style="thin"),
    )
    YES_FONT = Font(color="27AE60", bold=True)
    NO_FONT  = Font(color="E74C3C")

    ws.merge_cells("A1:H1")
    tc = ws["A1"]
    tc.value = f"Kunlik hisobot — {target_date.strftime('%d.%m.%Y')}{title_suffix}"
    tc.font = TITLE_FONT
    tc.alignment = CENTER
    ws.row_dimensions[1].height = 28

    headers = ["#", "Ism", "Sinf", "Bajarilgan mashqlar", "Video", "Kitob", "Betlar", "Rasm"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font = HDR_FONT
        cell.fill = HDR_FILL
        cell.alignment = CENTER
        cell.border = THIN
    ws.row_dimensions[2].height = 20

    for idx, s in enumerate(students, 1):
        row  = idx + 2
        fill = ALT_FILL if idx % 2 == 0 else None
        has_video = "✅ Ha" if s["exercise_video"] else "❌ Yo'q"
        has_photo = "✅ Ha" if (s["reading"] and s["reading"]["photo_file_id"]) else "❌ Yo'q"
        values = [
            idx,
            s["name"],
            s["class_name"],
            ", ".join(s["exercises"]) if s["exercises"] else "—",
            has_video,
            s["reading"]["book_name"]  if s["reading"] else "—",
            s["reading"]["pages_read"] if s["reading"] else "—",
            has_photo,
        ]
        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = THIN
            cell.alignment = CENTER if col != 4 else LEFT
            if fill:
                cell.fill = fill
            if col in (5, 8):
                cell.font = YES_FONT if "Ha" in str(val) else NO_FONT
        ws.row_dimensions[row].height = 18

    widths = [4, 22, 14, 42, 10, 28, 8, 10]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = w

    total_row = len(students) + 3
    ws.merge_cells(f"A{total_row}:H{total_row}")
    sc = ws[f"A{total_row}"]
    sc.value = (
        f"Jami: {len(students)} o'quvchi  |  "
        f"Mashq: {sum(1 for s in students if s['exercises'])}  |  "
        f"Video: {sum(1 for s in students if s['exercise_video'])}  |  "
        f"O'qish: {sum(1 for s in students if s['reading'])}  |  "
        f"Rasm: {sum(1 for s in students if s['reading'] and s['reading']['photo_file_id'])}"
    )
    sc.font = Font(bold=True, size=10, color="1A3C5E")
    sc.alignment = CENTER
    ws.row_dimensions[total_row].height = 18

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out


async def send_report(message: Message, target_date: date):
    """Generate report, send to requester, then send per-class to each linked group."""
    report_data = await db.get_report_data(target_date)
    if not report_data:
        return await message.answer("📭 Hali hech qanday o'quvchi ro'yxatdan o'tmagan.")

    # Send full report to requester
    excel = build_excel(target_date, report_data)
    await message.answer_document(
        BufferedInputFile(excel.read(), filename=f"hisobot_{target_date}.xlsx"),
        caption=(
            f"📊 **Kunlik hisobot — {target_date.strftime('%d.%m.%Y')}**\n"
            f"👥 O'quvchilar: {len(report_data)}\n"
            f"💪 Mashq belgilagan: {sum(1 for s in report_data if s['exercises'])}\n"
            f"📚 Kitob o'qigan: {sum(1 for s in report_data if s['reading'])}"
        ),
    )

    # Send per-class report to each linked group
    class_groups = await db.get_all_class_groups()
    if not class_groups:
        return

    # Group students by class
    from itertools import groupby
    sorted_data = sorted(report_data, key=lambda x: x["class_name"])
    for class_name, group_iter in groupby(sorted_data, key=lambda x: x["class_name"]):
        chat_id = class_groups.get(class_name)
        if not chat_id:
            continue
        class_students = list(group_iter)
        class_excel = build_excel(target_date, class_students, class_name=class_name)
        caption = (
            f"📊 **{class_name} — {target_date.strftime('%d.%m.%Y')} hisoboti**\n"
            f"👥 O'quvchilar: {len(class_students)}\n"
            f"💪 Mashq: {sum(1 for s in class_students if s['exercises'])}\n"
            f"📚 O'qish: {sum(1 for s in class_students if s['reading'])}"
        )
        try:
            await message.bot.send_document(
                chat_id=chat_id,
                document=BufferedInputFile(class_excel.read(), filename=f"hisobot_{class_name}_{target_date}.xlsx"),
                caption=caption,
            )
        except Exception as e:
            await message.answer(f"⚠️ **{class_name}** guruhiga yuborishda xatolik: {e}")


# ── 📊 Bugungi hisobot ─────────────────────────────────────────────────────────

@router.message(F.text == "📊 Bugungi hisobot")
async def btn_report_today(message: Message):
    if not await check_teacher(message):
        return await message.answer("❌ Bu tugma faqat o'qituvchi/admin uchun.")
    await message.answer(f"⏳ Bugungi hisobot tayyorlanmoqda...")
    await send_report(message, date.today())


# ── 📅 Sana bo'yicha hisobot ───────────────────────────────────────────────────

@router.message(F.text == "📅 Sana bo'yicha hisobot")
async def btn_report_by_date(message: Message, state: FSMContext):
    if not await check_teacher(message):
        return await message.answer("❌ Bu tugma faqat o'qituvchi/admin uchun.")
    await state.set_state(TeacherReport.waiting_for_date)
    await message.answer("📅 Hisobot sanasini yuboring:\nFormat: **28.03.2026**")


@router.message(TeacherReport.waiting_for_date)
async def fsm_report_date(message: Message, state: FSMContext):
    target_date = parse_date(message.text)
    if not target_date:
        return await message.answer("❌ Noto'g'ri sana formati. Masalan: **28.03.2026**")
    await state.clear()
    await message.answer(f"⏳ {target_date.strftime('%d.%m.%Y')} uchun hisobot tayyorlanmoqda...")
    await send_report(message, target_date)


# ── ⚠️ Belgilamaganlar ─────────────────────────────────────────────────────────

@router.message(F.text == "⚠️ Belgilamaganlar")
async def btn_missing(message: Message):
    if not await check_teacher(message):
        return await message.answer("❌ Bu tugma faqat o'qituvchi/admin uchun.")

    today = date.today()
    missing = await db.get_missing_students(today)
    if not missing:
        return await message.answer(
            f"🎉 Barcha o'quvchilar bugun ({today.strftime('%d.%m.%Y')}) belgilagan!"
        )
    text = f"⚠️ **Belgilamaganlar — {today.strftime('%d.%m.%Y')}:**\n"
    current_class = None
    for s in missing:
        if s["class_name"] != current_class:
            current_class = s["class_name"]
            text += f"\n📌 **{current_class}**\n"
        text += f"  • {s['name']}\n"
    await message.answer(text)
