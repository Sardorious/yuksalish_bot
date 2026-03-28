from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Log Exercises"), KeyboardButton(text="📚 Log Reading")],
            [KeyboardButton(text="📊 My Stats Today")],
        ],
        resize_keyboard=True,
    )


def exercises_keyboard(exercises, done_ids: list[int]) -> InlineKeyboardMarkup:
    buttons = []
    for ex in exercises:
        mark = "✅" if ex["id"] in done_ids else "◻️"
        buttons.append(
            [InlineKeyboardButton(text=f"{mark} {ex['name']}", callback_data=f"toggle_ex:{ex['id']}")]
        )
    buttons.append([InlineKeyboardButton(text="✔️ Done", callback_data="exercises_done")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def skip_keyboard(callback_data: str = "skip_media") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⏭ Skip", callback_data=callback_data)]]
    )


def admin_exercise_list_keyboard(exercises, action: str) -> InlineKeyboardMarkup:
    """action: 'delete' or 'edit'"""
    buttons = []
    for ex in exercises:
        if ex["active"]:
            icon = "🗑" if action == "delete" else "✏️"
            buttons.append(
                [InlineKeyboardButton(text=f"{icon} {ex['name']}", callback_data=f"{action}_ex:{ex['id']}")]
            )
    buttons.append([InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
