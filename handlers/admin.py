from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_IDS
from keyboards import (
    admin_menu_keyboard, admin_exercise_list_keyboard, 
    admin_class_manager_keyboard, class_selection_keyboard,
    admin_book_manager_keyboard, book_selection_keyboard, book_delete_keyboard,
    book_edit_keyboard, admin_student_manager_keyboard, student_selection_keyboard
)
from states import AddExercise, EditExercise, SetGroup, AddClass, AddBook, EditClass, EditBook, ManageStudent

router = Router()


# ── Ruxsat tekshiruvi ──────────────────────────────────────────────────────────

async def check_admin(message: Message) -> bool:
    user = await db.get_user(message.from_user.id)
    return message.from_user.id in ADMIN_IDS or (user is not None and user["role"] == "admin")


# ── ➕ Mashq qo'shish ──────────────────────────────────────────────────────────

@router.message(F.text == "➕ Mashq qo'shish")
async def btn_add_exercise(message: Message, state: FSMContext):
    if not await check_admin(message):
        return await message.answer("❌ Bu tugma faqat admin uchun.")
    await state.set_state(AddExercise.waiting_for_name)
    await message.answer("✏️ Yangi mashq nomini yuboring:")


@router.message(AddExercise.waiting_for_name, F.text)
async def fsm_add_exercise_name(message: Message, state: FSMContext):
    name = message.text.strip()
    success = await db.add_exercise(name)
    await state.clear()
    if success:
        await message.answer(f"✅ **{name}** mashqi qo'shildi!", reply_markup=admin_menu_keyboard())
    else:
        await message.answer(f"⚠️ **{name}** mashqi allaqachon mavjud.", reply_markup=admin_menu_keyboard())


# ── 🗑 Mashq o'chirish ─────────────────────────────────────────────────────────

@router.message(F.text == "🗑 Mashq o'chirish")
async def btn_delete_exercise(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Bu tugma faqat admin uchun.")
    exercises = await db.get_all_exercises()
    active = [ex for ex in exercises if ex["active"]]
    if not active:
        return await message.answer("📭 O'chirish uchun faol mashqlar yo'q.")
    await message.answer("O'chirish uchun mashqni tanlang:", reply_markup=admin_exercise_list_keyboard(active, "delete"))


@router.callback_query(F.data.startswith("delete_ex:"))
async def cb_delete_exercise(call: CallbackQuery):
    ex_id = int(call.data.split(":")[1])
    await db.delete_exercise(ex_id)
    await call.message.edit_text("🗑 Mashq o'chirildi.")
    await call.answer("O'chirildi!")


# ── ✏️ Mashq tahrirlash ────────────────────────────────────────────────────────

@router.message(F.text == "✏️ Mashq tahrirlash")
async def btn_edit_exercise(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Bu tugma faqat admin uchun.")
    exercises = await db.get_all_exercises()
    active = [ex for ex in exercises if ex["active"]]
    if not active:
        return await message.answer("📭 Tahrirlash uchun faol mashqlar yo'q.")
    await message.answer("Tahrirlash uchun mashqni tanlang:", reply_markup=admin_exercise_list_keyboard(active, "edit"))


@router.callback_query(F.data.startswith("edit_ex:"))
async def cb_edit_exercise_select(call: CallbackQuery, state: FSMContext):
    ex_id = int(call.data.split(":")[1])
    await state.set_state(EditExercise.waiting_for_new_name)
    await state.update_data(edit_ex_id=ex_id)
    await call.message.edit_text("✏️ Mashqning yangi nomini yuboring:")
    await call.answer()


@router.message(EditExercise.waiting_for_new_name, F.text)
async def fsm_edit_exercise_name(message: Message, state: FSMContext):
    data = await state.get_data()
    new_name = message.text.strip()
    success = await db.update_exercise(data["edit_ex_id"], new_name)
    await state.clear()
    if success:
        await message.answer(f"✅ Mashq nomi **{new_name}** ga o'zgartirildi.", reply_markup=admin_menu_keyboard())
    else:
        await message.answer(f"⚠️ **{new_name}** nomi allaqachon mavjud.", reply_markup=admin_menu_keyboard())


# ── 📋 Mashqlar ro'yxati ───────────────────────────────────────────────────────

@router.message(F.text == "📋 Mashqlar ro'yxati")
async def btn_list_exercises(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Bu tugma faqat admin uchun.")
    exercises = await db.get_active_exercises()
    if not exercises:
        return await message.answer("📭 Faol mashqlar topilmadi.")
    text = "📋 **Faol mashqlar:**\n\n" + "\n".join(f"• {ex['name']}" for ex in exercises)
    await message.answer(text)


# ── 👥 O'quvchilarni boshqarish ──────────────────────────────────────────────────

@router.message(F.text == "👥 O'quvchilarni boshqarish")
async def btn_students(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Bu tugma faqat admin uchun.")
    await message.answer("👥 O'quvchilarni boshqarish menyusi:", reply_markup=admin_student_manager_keyboard())


@router.callback_query(F.data == "list_all_students")
async def cb_list_all_students(call: CallbackQuery):
    students = await db.get_all_students()
    if not students:
        return await call.message.edit_text("📭 Hali hech qanday o'quvchi ro'yxatdan o'tmagan.", reply_markup=admin_student_manager_keyboard())
    text = f"👥 **O'quvchilar ({len(students)} nafar):**\n"
    current_class = None
    for s in students:
        if s["class_name"] != current_class:
            current_class = s["class_name"]
            text += f"\n📌 **{current_class}**\n"
        phone_txt = s.get("phone") or "raqam yo'q"
        text += f"  • {s['name']} (tel: {phone_txt})\n"
    await call.message.edit_text(text, reply_markup=admin_student_manager_keyboard())
    await call.answer()


@router.callback_query(F.data.in_({"edit_student_class", "delete_student_from_db"}))
async def cb_choose_action_student(call: CallbackQuery, state: FSMContext):
    action = call.data
    await state.update_data(student_action=action)
    classes = await db.get_all_classes()
    if not classes:
         return await call.message.edit_text("📭 Hali sinflar qo'shilmagan.", reply_markup=admin_student_manager_keyboard())
    await call.message.edit_text(
        "🏫 O'quvchini topish uchun avval **sinfini** tanlang:",
        reply_markup=class_selection_keyboard(classes, prefix="adm_class_sel")
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_class_sel:"))
async def cb_select_class_for_student(call: CallbackQuery, state: FSMContext):
    class_name = call.data.split(":")[1]
    students = await db.get_students_by_class(class_name)
    if not students:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        return await call.message.edit_text(
            f"📭 {class_name} sinfida faol o'quvchilar yo'q.", 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Qaytish", callback_data="cancel")]])
        )
        
    data = await state.get_data()
    action = data.get("student_action")
    await call.message.edit_text(
        f"👥 **{class_name}** sinfi o'quvchilari. Kerakli o'quvchini tanlang:",
        reply_markup=student_selection_keyboard(students, action="adm_stu_sel")
    )
    await call.answer()


@router.callback_query(F.data.startswith("adm_stu_sel:"))
async def cb_select_student_finally(call: CallbackQuery, state: FSMContext):
    stu_id = int(call.data.split(":")[1])
    data = await state.get_data()
    action = data.get("student_action")
    
    if action == "delete_student_from_db":
        await db.deactivate_user(stu_id)
        await state.clear()
        await call.message.edit_text("✅ O'quvchi tizimdan o'chirildi (Ma'lumotlari muzlatildi).")
    
    elif action == "edit_student_class":
        await state.update_data(edit_student_id=stu_id)
        await state.set_state(ManageStudent.waiting_for_new_class)
        classes = await db.get_all_classes()
        await call.message.edit_text(
            "🏫 O'quvchi uchun **yangi sinfni** tanlang:",
            reply_markup=class_selection_keyboard(classes)
        )
    await call.answer()


@router.callback_query(ManageStudent.waiting_for_new_class, F.data.startswith("select_class:"))
async def cb_new_class_for_student(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    stu_id = data["edit_student_id"]
    new_class = call.data.split(":")[1]
    await db.update_user_class(stu_id, new_class)
    await state.clear()
    await call.message.edit_text(f"✅ O'quvchi muvaffaqiyatli **{new_class}** sinfiga o'tkazildi.")
    await call.answer()


# ── 🔗 Sinf guruhini ulash ─────────────────────────────────────────────────────

@router.message(F.text == "🔗 Sinf guruhini ulash")
async def btn_set_group(message: Message, state: FSMContext):
    if not await check_admin(message):
        return await message.answer("❌ Bu tugma faqat admin uchun.")

    classes = await db.get_all_classes()
    if not classes:
        return await message.answer("📭 Hali sinflar qo'shilmagan. Avval sinf qo'shing.")

    await message.answer(
        "Qaysi sinf uchun guruh ulaysiz? Ro'yxatdan tanlang:",
        reply_markup=class_selection_keyboard(classes, "set_group_cls")
    )


@router.callback_query(F.data.startswith("set_group_cls:"))
async def cb_set_group_class(call: CallbackQuery, state: FSMContext):
    class_name = call.data.split(":")[1]
    await state.update_data(class_name=class_name)
    await state.set_state(SetGroup.waiting_for_chat_id)
    await call.message.edit_text(
        f"📌 Tanlangan sinf: **{class_name}**\n\n"
        "📲 Endi shu sinf Telegram guruhining **Chat ID** sini yuboring.\n\n"
        "💡 Guruh ID sini bilish uchun botni guruhga qo'shing va `@userinfobot` ga forward qiling.\n"
        "Guruh ID odatda `-100` bilan boshlanadi, masalan: `-1001234567890`"
    )
    await call.answer()


@router.message(SetGroup.waiting_for_chat_id, F.text)
async def fsm_set_group_chat_id(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ Noto'g'ri Chat ID. Raqam yuboring (masalan: -1001234567890).")
    data = await state.get_data()
    class_name = data["class_name"]
    await db.set_class_group(class_name, chat_id)
    await state.clear()
    await message.answer(
        f"✅ **{class_name}** sinfi guruhiga muvaffaqiyatli ulandi!\n"
        f"Chat ID: `{chat_id}`",
        reply_markup=admin_menu_keyboard(),
    )


# ── 🏫 Sinflarni boshqarish ───────────────────────────────────────────────────

@router.message(F.text == "🏫 Sinflarni boshqarish")
async def btn_manage_classes(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Bu tugma faqat admin uchun.")
    await message.answer("🏫 **Sinflarni boshqarish menyusi**", reply_markup=admin_class_manager_keyboard())


@router.callback_query(F.data == "add_class")
async def cb_add_class_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AddClass.waiting_for_name)
    await call.message.edit_text("✏️ Yangi sinf nomini yuboring (masalan: 5-A sinf):")
    await call.answer()


@router.message(AddClass.waiting_for_name, F.text)
async def fsm_add_class_name(message: Message, state: FSMContext):
    name = message.text.strip()
    success = await db.add_class(name)
    await state.clear()
    if success:
        await message.answer(f"✅ **{name}** sinfi qo'shildi!", reply_markup=admin_menu_keyboard())
    else:
        await message.answer(f"⚠️ **{name}** sinfi allaqachon mavjud.", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "list_classes")
async def cb_list_classes(call: CallbackQuery):
    classes = await db.get_all_classes()
    if not classes:
        return await call.message.edit_text("📭 Sinflar ro'yxati bo'sh.", reply_markup=admin_class_manager_keyboard())
    text = "📋 **Mavjud sinflar:**\n\n" + "\n".join(f"• {c}" for c in classes)
    await call.message.edit_text(text, reply_markup=admin_class_manager_keyboard())
    await call.answer()


@router.callback_query(F.data == "list_delete_class")
async def cb_list_delete_class(call: CallbackQuery):
    classes = await db.get_all_classes()
    if not classes:
        return await call.message.edit_text("📭 O'chirish uchun sinflar yo'q.", reply_markup=admin_class_manager_keyboard())
    await call.message.edit_text("O'chirish uchun sinfni tanlang:", reply_markup=class_selection_keyboard(classes, "delete_cls"))
    await call.answer()


@router.callback_query(F.data.startswith("delete_cls:"))
async def cb_delete_class(call: CallbackQuery):
    class_name = call.data.split(":")[1]
    await db.delete_class(class_name)
    await call.message.edit_text(f"🗑 **{class_name}** sinfi o'chirildi.")
    await call.answer("O'chirildi!")


@router.callback_query(F.data == "list_edit_class")
async def cb_list_edit_class(call: CallbackQuery):
    classes = await db.get_all_classes()
    if not classes:
        return await call.message.edit_text("📭 Tahrirlash uchun sinflar yo'q.", reply_markup=admin_class_manager_keyboard())
    await call.message.edit_text("Tahrirlash uchun sinfni tanlang:", reply_markup=class_selection_keyboard(classes, "edit_cls"))
    await call.answer()


@router.callback_query(F.data.startswith("edit_cls:"))
async def cb_edit_class_select(call: CallbackQuery, state: FSMContext):
    class_name = call.data.split(":")[1]
    await state.update_data(old_class_name=class_name)
    await state.set_state(EditClass.waiting_for_new_name)
    await call.message.edit_text(f"✏️ **{class_name}** sinfining yangi nomini yuboring:")
    await call.answer()


@router.message(EditClass.waiting_for_new_name, F.text)
async def fsm_edit_class_name(message: Message, state: FSMContext):
    data = await state.get_data()
    old_name = data["old_class_name"]
    new_name = message.text.strip()
    success = await db.update_class(old_name, new_name)
    await state.clear()
    if success:
        await message.answer(f"✅ Sinf nomi **{old_name}** dan **{new_name}** ga o'zgartirildi.", reply_markup=admin_menu_keyboard())
    else:
        await message.answer(f"⚠️ **{new_name}** nomi allaqachon mavjud yoki xatolik yuz berdi.", reply_markup=admin_menu_keyboard())


# ── Bekor qilish (inline) ──────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel")
async def cb_cancel(call: CallbackQuery):
    await call.message.edit_text("❌ Bekor qilindi.")
    await call.answer()

