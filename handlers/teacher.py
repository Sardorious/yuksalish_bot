import io
from datetime import date, datetime

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

import database as db
from config import ADMIN_IDS

router = Router()


# ── Permission check ───────────────────────────────────────────────────────────

async def check_teacher(message: Message) -> bool:
    user = await db.get_user(message.from_user.id)
    return message.from_user.id in ADMIN_IDS or (
        user is not None and user["role"] in ("teacher", "admin")
    )


def parse_date(date_str: str) -> date | None:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


# ── Excel generation ───────────────────────────────────────────────────────────

async def generate_excel_report(target_date: date, report_data: list[dict]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Report {target_date}"

    # ── Styles ──
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
    YES_FONT  = Font(color="27AE60", bold=True)
    NO_FONT   = Font(color="E74C3C")

    # ── Row 1: title ──
    ws.merge_cells("A1:H1")
    tc = ws["A1"]
    tc.value     = f"📋 Exercise & Reading Report — {target_date.strftime('%d %B %Y')}"
    tc.font      = TITLE_FONT
    tc.alignment = CENTER
    ws.row_dimensions[1].height = 28

    # ── Row 2: headers ──
    headers = ["#", "Name", "Class", "Exercises Done", "Video", "Book", "Pages", "Photo"]
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col, value=h)
        cell.font      = HDR_FONT
        cell.fill      = HDR_FILL
        cell.alignment = CENTER
        cell.border    = THIN
    ws.row_dimensions[2].height = 20

    # ── Data rows ──
    for idx, s in enumerate(report_data, 1):
        row   = idx + 2
        fill  = ALT_FILL if idx % 2 == 0 else None

        has_video = "✅ Yes" if s["exercise_video"] else "❌ No"
        has_photo = "✅ Yes" if (s["reading"] and s["reading"]["photo_file_id"]) else "❌ No"

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
            cell            = ws.cell(row=row, column=col, value=val)
            cell.border     = THIN
            cell.alignment  = CENTER if col != 4 else LEFT
            if fill:
                cell.fill = fill
            # Colour Yes/No cells
            if col in (5, 8):
                cell.font = YES_FONT if "Yes" in str(val) else NO_FONT

        ws.row_dimensions[row].height = 18

    # ── Column widths ──
    widths = [4, 22, 14, 42, 10, 28, 8, 10]
    for col, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = w

    # ── Summary row ──
    total_row = len(report_data) + 3
    ws.merge_cells(f"A{total_row}:H{total_row}")
    sc = ws[f"A{total_row}"]
    with_ex   = sum(1 for s in report_data if s["exercises"])
    with_read = sum(1 for s in report_data if s["reading"])
    with_vid  = sum(1 for s in report_data if s["exercise_video"])
    with_pic  = sum(1 for s in report_data if s["reading"] and s["reading"]["photo_file_id"])
    sc.value = (
        f"Total: {len(report_data)} students  |  "
        f"Exercises: {with_ex}  |  Videos: {with_vid}  |  "
        f"Reading: {with_read}  |  Photos: {with_pic}"
    )
    sc.font      = Font(bold=True, size=10, color="1A3C5E")
    sc.alignment = CENTER
    ws.row_dimensions[total_row].height = 18

    out = io.BytesIO()
    wb.save(out)
    out.seek(0)
    return out


# ── /report [date] ─────────────────────────────────────────────────────────────

@router.message(Command("report"))
async def cmd_report(message: Message):
    if not await check_teacher(message):
        return await message.answer("❌ Teacher/Admin only command.")

    args = message.text.split()
    if len(args) >= 2:
        target_date = parse_date(args[1])
        if not target_date:
            return await message.answer("❌ Invalid date. Use format: /report YYYY-MM-DD")
    else:
        target_date = date.today()

    await message.answer(f"⏳ Generating report for **{target_date.strftime('%d %B %Y')}**…")

    report_data = await db.get_report_data(target_date)
    if not report_data:
        return await message.answer("📭 No students registered yet.")

    excel_file = await generate_excel_report(target_date, report_data)
    with_ex   = sum(1 for s in report_data if s["exercises"])
    with_read = sum(1 for s in report_data if s["reading"])

    await message.answer_document(
        BufferedInputFile(excel_file.read(), filename=f"report_{target_date}.xlsx"),
        caption=(
            f"📊 **Daily Report — {target_date.strftime('%d %B %Y')}**\n"
            f"👥 Students: {len(report_data)}\n"
            f"💪 Logged exercises: {with_ex}\n"
            f"📚 Logged reading: {with_read}"
        ),
    )


# ── /missing [date] ────────────────────────────────────────────────────────────

@router.message(Command("missing"))
async def cmd_missing(message: Message):
    if not await check_teacher(message):
        return await message.answer("❌ Teacher/Admin only command.")

    args = message.text.split()
    if len(args) >= 2:
        target_date = parse_date(args[1])
        if not target_date:
            return await message.answer("❌ Invalid date. Use format: /missing YYYY-MM-DD")
    else:
        target_date = date.today()

    missing = await db.get_missing_students(target_date)
    if not missing:
        return await message.answer(
            f"🎉 All students have submitted for **{target_date.strftime('%d %B %Y')}**!"
        )

    text = f"⚠️ **Missing submissions — {target_date.strftime('%d %B %Y')}:**\n"
    current_class = None
    for s in missing:
        if s["class_name"] != current_class:
            current_class = s["class_name"]
            text += f"\n📌 **{current_class}**\n"
        text += f"  • {s['name']}\n"
    await message.answer(text)
