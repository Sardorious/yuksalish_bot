from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

# ── Role-based reply keyboards ─────────────────────────────────────────────────

def student_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Mashqlarni belgilash"), KeyboardButton(text="📚 Kitob o'qishni belgilash")],
            [KeyboardButton(text="📊 Bugungi natijalarim")],
        ],
        resize_keyboard=True,
    )


def teacher_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Bugungi hisobot"), KeyboardButton(text="📅 Sana bo'yicha hisobot")],
            [KeyboardButton(text="⚠️ Belgilamaganlar")],
        ],
        resize_keyboard=True,
    )


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Mashq qo'shish"), KeyboardButton(text="🗑 Mashq o'chirish")],
            [KeyboardButton(text="✏️ Mashq tahrirlash"), KeyboardButton(text="📋 Mashqlar ro'yxati")],
            [KeyboardButton(text="👥 O'quvchilar ro'yxati"), KeyboardButton(text="🔗 Sinf guruhini ulash")],
            [KeyboardButton(text="📊 Bugungi hisobot"), KeyboardButton(text="⚠️ Belgilamaganlar")],
            [KeyboardButton(text="📅 Sana bo'yicha hisobot")],
        ],
        resize_keyboard=True,
    )


# Alias so student.py import stays clean
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return student_menu_keyboard()


# ── Inline keyboards ───────────────────────────────────────────────────────────

def exercises_keyboard(exercises, done_ids: list[int]) -> InlineKeyboardMarkup:
    buttons = []
    for ex in exercises:
        mark = "✅" if ex["id"] in done_ids else "◻️"
        buttons.append(
            [InlineKeyboardButton(text=f"{mark} {ex['name']}", callback_data=f"toggle_ex:{ex['id']}")]
        )
    buttons.append([InlineKeyboardButton(text="✔️ Tayyor", callback_data="exercises_done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def skip_keyboard(callback_data: str = "skip_media") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=callback_data)]]
    )


def admin_exercise_list_keyboard(exercises, action: str) -> InlineKeyboardMarkup:
    buttons = []
    for ex in exercises:
        if ex["active"]:
            icon = "🗑" if action == "delete" else "✏️"
            buttons.append(
                [InlineKeyboardButton(text=f"{icon} {ex['name']}", callback_data=f"{action}_ex:{ex['id']}")]
            )
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
