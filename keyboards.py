from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

# ── Role-based reply keyboards ─────────────────────────────────────────────────

def request_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
    )

def student_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Vazifalarni belgilash"), KeyboardButton(text="📚 Kitob o'qishni belgilash")],
            [KeyboardButton(text="💪 Vazifa natijalari"), KeyboardButton(text="📚 Kitob natijalari")],
        ],
        resize_keyboard=True,
    )


def teacher_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💪 Vazifalar hisoboti"), KeyboardButton(text="📚 Kitoblar hisoboti")],
            [KeyboardButton(text="📅 Sana bo'yicha (Vazifa)"), KeyboardButton(text="📅 Sana bo'yicha (Kitob)")],
            [KeyboardButton(text="📚 Kitoblarni boshqarish")],
            [KeyboardButton(text="⚠️ Belgilamaganlar"), KeyboardButton(text="📷 Bugungi media")],
        ],
        resize_keyboard=True,
    )


def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Vazifa qo'shish"), KeyboardButton(text="🗑 Vazifa o'chirish")],
            [KeyboardButton(text="✏️ Vazifa tahrirlash"), KeyboardButton(text="📋 Vazifalar ro'yxati")],
            [KeyboardButton(text="🏫 Sinflarni boshqarish"), KeyboardButton(text="📚 Kitoblarni boshqarish")],
            [KeyboardButton(text="🔗 Sinf guruhini ulash"), KeyboardButton(text="👥 O'quvchilarni boshqarish")],
            [KeyboardButton(text="💪 Vazifalar hisoboti"), KeyboardButton(text="📚 Kitoblar hisoboti")],
            [KeyboardButton(text="📅 Sana bo'yicha (Vazifa)"), KeyboardButton(text="📅 Sana bo'yicha (Kitob)")],
            [KeyboardButton(text="⚠️ Belgilamaganlar")],
        ],
        resize_keyboard=True,
    )


# Alias so student.py import stays clean
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return student_menu_keyboard()


# ── Inline keyboards ───────────────────────────────────────────────────────────

def exercises_keyboard(exercises, done_ids: list[int]) -> InlineKeyboardMarkup:
    buttons = []
    # Two columns for exercises
    for i in range(0, len(exercises), 2):
        row = []
        # First item
        ex1 = exercises[i]
        mark1 = "✅" if ex1["id"] in done_ids else "◻️"
        row.append(InlineKeyboardButton(text=f"{mark1} {ex1['name']}", callback_data=f"toggle_ex:{ex1['id']}"))
        # Second item if exists
        if i + 1 < len(exercises):
            ex2 = exercises[i+1]
            mark2 = "✅" if ex2["id"] in done_ids else "◻️"
            row.append(InlineKeyboardButton(text=f"{mark2} {ex2['name']}", callback_data=f"toggle_ex:{ex2['id']}"))
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="✔️ Tayyor", callback_data="exercises_done")])
    buttons.append([InlineKeyboardButton(text="🚫 Bugun vazifa bajarolmadim", callback_data="skip_exercises_all")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def skip_keyboard(callback_data: str = "skip_media") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⏭ O'tkazib yuborish", callback_data=callback_data)]]
    )


def admin_exercise_list_keyboard(exercises, action: str) -> InlineKeyboardMarkup:
    buttons = []
    active_ex = [ex for ex in exercises if ex["active"]]
    icon = "🗑" if action == "delete" else "✏️"
    
    # Two columns
    for i in range(0, len(active_ex), 2):
        row = [InlineKeyboardButton(text=f"{icon} {active_ex[i]['name']}", callback_data=f"{action}_ex:{active_ex[i]['id']}")]
        if i + 1 < len(active_ex):
            row.append(InlineKeyboardButton(text=f"{icon} {active_ex[i+1]['name']}", callback_data=f"{action}_ex:{active_ex[i+1]['id']}"))
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_class_manager_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Sinf qo'shish", callback_data="add_class")],
            [InlineKeyboardButton(text="✏️ Sinf tahrirlash", callback_data="list_edit_class")],
            [InlineKeyboardButton(text="🗑 Sinf o'chirish", callback_data="list_delete_class")],
            [InlineKeyboardButton(text="📋 Sinflar ro'yxati", callback_data="list_classes")],
        ]
    )


def admin_book_manager_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Kitob qo'shish", callback_data="add_book")],
            [InlineKeyboardButton(text="✏️ Kitob tahrirlash", callback_data="list_edit_book")],
            [InlineKeyboardButton(text="🗑 Kitob o'chirish", callback_data="list_delete_book")],
            [InlineKeyboardButton(text="📋 Kitoblar ro'yxati", callback_data="list_books")],
        ]
    )

def admin_student_manager_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Barcha o'quvchilar ro'yxati", callback_data="list_all_students")],
            [InlineKeyboardButton(text="✏️ Sinfni o'zgartirish", callback_data="edit_student_class")],
            [InlineKeyboardButton(text="🗑 O'quvchini o'chirish", callback_data="delete_student_from_db")],
        ]
    )


def class_selection_keyboard(classes: list[str], prefix: str = "select_class") -> InlineKeyboardMarkup:
    buttons = []
    # Two columns
    for i in range(0, len(classes), 2):
        row = [InlineKeyboardButton(text=classes[i], callback_data=f"{prefix}:{classes[i]}")]
        if i + 1 < len(classes):
            row.append(InlineKeyboardButton(text=classes[i+1], callback_data=f"{prefix}:{classes[i+1]}"))
        buttons.append(row)
    
    if prefix != "select_class": # if it's for admin deletion or something else
        buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def student_selection_keyboard(students: list[dict], action: str) -> InlineKeyboardMarkup:
    buttons = []
    # Two columns
    for i in range(0, len(students), 2):
        row = [InlineKeyboardButton(text=f"{students[i]['name']}", callback_data=f"{action}:{students[i]['telegram_id']}")]
        if i + 1 < len(students):
            row.append(InlineKeyboardButton(text=f"{students[i+1]['name']}", callback_data=f"{action}:{students[i+1]['telegram_id']}"))
        buttons.append(row)
            
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def book_selection_keyboard(books: list[dict], last_book: str | None = None) -> InlineKeyboardMarkup:
    buttons = []
    
    # Priority: last read book
    if last_book:
        buttons.append([InlineKeyboardButton(text=f"📖 Oxirgi: {last_book}", callback_data=f"select_book:{last_book}")])
    
    # Two columns for other books
    for i in range(0, len(books), 2):
        row = [InlineKeyboardButton(text=books[i]["name"], callback_data=f"select_book:{books[i]['name']}")]
        if i + 1 < len(books):
            row.append(InlineKeyboardButton(text=books[i+1]["name"], callback_data=f"select_book:{books[i+1]['name']}"))
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="🚫 Bugun o'qiyolmadim", callback_data="skip_reading_all")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def book_delete_keyboard(books: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    # Two columns
    for i in range(0, len(books), 2):
        row = [InlineKeyboardButton(text=f"🗑 {books[i]['name']}", callback_data=f"delete_book:{books[i]['id']}:{books[i]['name']}")]
        if i + 1 < len(books):
            row.append(InlineKeyboardButton(text=f"🗑 {books[i+1]['name']}", callback_data=f"delete_book:{books[i+1]['id']}:{books[i+1]['name']}"))
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def book_edit_keyboard(books: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    # Two columns
    for i in range(0, len(books), 2):
        row = [InlineKeyboardButton(text=f"✏️ {books[i]['name']}", callback_data=f"edit_book:{books[i]['id']}")]
        if i + 1 < len(books):
            row.append(InlineKeyboardButton(text=f"✏️ {books[i+1]['name']}", callback_data=f"edit_book:{books[i+1]['id']}"))
        buttons.append(row)
        
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def edit_today_keyboard(section: str, has_removable_item: bool = False) -> InlineKeyboardMarkup:
    """Shows 'Edit' button when student already submitted today, and options to delete selectively."""
    cb = f"edit_today_{section}"
    buttons = [[InlineKeyboardButton(text="✏️ O'zgartirish", callback_data=cb)]]
    if section == "exercises" and has_removable_item:
        buttons.append([InlineKeyboardButton(text="🗑 Videoni o'chirish", callback_data="del_today_video")])
    elif section == "reading" and has_removable_item:
        buttons.append([InlineKeyboardButton(text="🗑 Kitob qaydini o'chirish", callback_data="del_today_reading")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
