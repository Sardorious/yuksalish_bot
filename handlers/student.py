from datetime import date, datetime

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_IDS
from keyboards import (
    student_menu_keyboard, teacher_menu_keyboard, admin_menu_keyboard,
    exercises_keyboard, skip_keyboard, class_selection_keyboard, book_selection_keyboard,
    edit_today_keyboard, request_phone_keyboard
)
from states import Registration, ReadingLog, ExerciseMedia, Reminder

router = Router()


# -- Yordamchi: rolga mos klaviatura --

async def get_role_keyboard(user_id: int, db_role: str):
    if user_id in ADMIN_IDS or db_role == "admin":
        return admin_menu_keyboard()
    elif db_role == "teacher":
        return teacher_menu_keyboard()
    else:
        return student_menu_keyboard()


# -- /start --

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if user and user["is_active"] == 1:
        keyboard = await get_role_keyboard(message.from_user.id, user["role"])
        role_text = {
            "admin": "Admin",
            "teacher": "O'qituvchi",
            "student": "O'quvchi",
        }.get(user["role"], "Foydalanuvchi")
        await message.answer(
            f"👋 Qaytib kelganingizdan xursandmiz, **{user['name']}**! ({role_text})\n\n"
            f"Quyidagi tugmalardan birini tanlang:",
            reply_markup=keyboard,
        )
        return

    await state.set_state(Registration.waiting_for_name)
    await message.answer(
        "👋 **Vazifa kuzatuv botiga** xush kelibsiz!\n\n"
        "Keling, ro'yxatdan o'tamiz. Iltimos, **to'liq ismingizni** yuboring:",
        reply_markup=ReplyKeyboardRemove()
    )


# -- Ro'yxatdan o'tish --

@router.message(Registration.waiting_for_name, F.text)
async def fsm_get_name(message: Message, state: FSMContext):
    classes = await db.get_all_classes()
    if not classes:
        return await message.answer(
            "⚠️ Tizimda hali sinflar mavjud emas. Iltimos, admindan sinflarni qo'shishni so'rang."
        )
    await state.update_data(name=message.text.strip())
    
    await state.set_state(Registration.waiting_for_phone)
    await message.answer(
        "📱 Endi, iltimos, **telefon raqamingizni** yuboring:\n"
        "Pastdagi 'Raqamni yuborish' tugmasini bosing yoki +998... shaklida yozing.",
        reply_markup=request_phone_keyboard()
    )

@router.message(Registration.waiting_for_phone, F.contact | F.text)
async def fsm_get_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()
        
    await state.update_data(phone=phone)
    classes = await db.get_all_classes()
    
    await state.set_state(Registration.waiting_for_class)
    await message.answer(
        "📚 Ajoyib! Endi **sinfingizni** ro'yxatdan tanlang:",
        reply_markup=class_selection_keyboard(classes)
    )

@router.callback_query(Registration.waiting_for_class, F.data.startswith("select_class:"))
async def fsm_get_class(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    phone = data.get("phone", "")
    class_name = call.data.split(":")[1]
    
    await db.create_user(call.from_user.id, name, class_name, phone=phone)
    await state.clear()
    
    await call.message.edit_text(
        f"✅ **Muvaffaqiyatli ro'yxatdan o'tdingiz!**\n\n"
        f"👤 Ism: {name}\n"
        f"📞 Telefon: {phone}\n"
        f"🏫 Sinf: {class_name}\n\n"
        f"Quyidagi menyu orqali joriy vazifalaringizni belgilang."
    )
    await call.message.answer("Asosiy menyu:", reply_markup=student_menu_keyboard())
    await call.answer()


# -- 📋 Vazifalarni belgilash --

@router.message(F.text == "📋 Vazifalarni belgilash")
async def btn_log_exercises(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or user["is_active"] == 0:
        return await message.answer("Iltimos, avval /start buyrug'i orqali ro'yxatdan o'ting.")

    # Already submitted today?
    already = await db.has_submitted_exercises_today(message.from_user.id)
    if already:
        done_ids = await db.get_student_exercise_ids_today(message.from_user.id)
        exercises = await db.get_active_exercises()
        done_names = [ex["name"] for ex in exercises if ex["id"] in done_ids]
        video = await db.get_exercise_video(message.from_user.id)
        summary = f"👤 **O'quvchi:** {user['name']}\n"
        summary += "✅ **Bugun vazifalaringiz yuborilgan:**\n"
        if done_names:
            summary += "\n".join(f"  ✅ {n}" for n in done_names)
        else:
            summary += "  📭 Hech qanday vazifa belgilanmagan"
        summary += f"\n🎥 Video: {'yuklandi ✅' if video else 'yuklanmagan'}"
        return await message.answer(
            summary + "\n\n✏️ O'zgartirmoqchimisiz?",
            reply_markup=edit_today_keyboard("exercises", has_removable_item=bool(video))
        )

    exercises = await db.get_active_exercises()
    if not exercises:
        return await message.answer("📭 Hozircha vazifalar yo'q. Admindan qo'shishni so'rang!")
    done_ids = await db.get_student_exercise_ids_today(message.from_user.id)
    await message.answer(
        "📋 **Bugungi vazifalar**\n"
        "Belgilash ✅ / bekor qilish uchun bosing. Tugatgach **Tayyor** tugmasini bosing.",
        reply_markup=exercises_keyboard(exercises, done_ids),
    )


@router.callback_query(F.data == "edit_today_exercises", StateFilter("*"))
async def cb_edit_today_exercises(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await db.unmark_exercises_submitted(call.from_user.id)
    exercises = await db.get_active_exercises()
    done_ids = await db.get_student_exercise_ids_today(call.from_user.id)
    await call.message.edit_text(
        "✏️ **Vazifalarni o'zgartiring:**\n"
        "Belgilash ✅ / bekor qilish uchun bosing. Tugatgach **Tayyor** tugmasini bosing.",
        reply_markup=exercises_keyboard(exercises, done_ids),
    )
    await call.answer()


@router.callback_query(F.data.startswith("toggle_ex:"))
async def cb_toggle_exercise(call: CallbackQuery):
    ex_id = int(call.data.split(":")[1])
    await db.toggle_exercise_submission(call.from_user.id, ex_id)
    exercises = await db.get_active_exercises()
    done_ids = await db.get_student_exercise_ids_today(call.from_user.id)
    await call.message.edit_reply_markup(reply_markup=exercises_keyboard(exercises, done_ids))
    await call.answer()


@router.callback_query(F.data == "exercises_done")
async def cb_exercises_done(call: CallbackQuery, state: FSMContext):
    done_ids = await db.get_student_exercise_ids_today(call.from_user.id)
    exercises = await db.get_active_exercises()
    done_names = [ex["name"] for ex in exercises if ex["id"] in done_ids]

    # Mark as submitted
    await db.mark_exercises_submitted(call.from_user.id)

    user = await db.get_user(call.from_user.id)
    name = user["name"] if user else "O'quvchi"

    if done_names:
        summary = f"👤 **O'quvchi:** {name}\n✅ **Belgilangan vazifalar:**\n" + "\n".join(f"  • {n}" for n in done_names)
    else:
        summary = f"👤 **O'quvchi:** {name}\n📭 Hech qanday vazifa tanlanmagan."

    await call.message.edit_text(summary)
    await call.answer("Saqlandi!")

    await state.set_state(ExerciseMedia.waiting_for_video)
    await call.message.answer(
        "📹 Vazifalaringizning **videosini** yuklashni xohlaysizmi? (ixtiyoriy)\n"
        "Video yuboring yoki **O'tkazib yuborish** tugmasini bosing.",
        reply_markup=skip_keyboard("skip_exercise_video"),
    )


@router.message(ExerciseMedia.waiting_for_video, F.video)
async def fsm_exercise_video(message: Message, state: FSMContext):
    await db.save_exercise_video(message.from_user.id, message.video.file_id)
    await state.clear()
    user = await db.get_user(message.from_user.id)
    keyboard = await get_role_keyboard(message.from_user.id, user["role"] if user else "student")
    await message.answer("🎥 Video yuklandi! Zo'r ish 💪", reply_markup=keyboard)


@router.callback_query(F.data == "skip_exercise_video", ExerciseMedia.waiting_for_video)
async def cb_skip_exercise_video(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⏭ Video o'tkazib yuborildi.")
    await call.answer()


# -- 📚 Kitob o'qishni belgilash --

@router.message(F.text == "📚 Kitob o'qishni belgilash")
async def btn_log_reading(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user or user["is_active"] == 0:
        return await message.answer("Iltimos, avval /start buyrug'i orqali ro'yxatdan o'ting.")

    # Already submitted reading today?
    reading = await db.get_reading_today(message.from_user.id)
    if reading:
        summary = (
            f"👤 **O'quvchi:** {user['name']}\n"
            f"📚 **Bugun kitob o'qish belgilangan:**\n\n"
            f"📖 Kitob: {reading['book_name']}\n"
            f"📄 Betlar: {reading['pages_read']}\n"
            f"📷 Rasm: {'yuklandi ✅' if reading['photo_file_id'] else 'yuklanmagan'}\n\n"
            f"✏️ O'zgartirmoqchimisiz?"
        )
        return await message.answer(summary, reply_markup=edit_today_keyboard("reading", has_removable_item=True))

    books = await db.get_all_books()
    if not books:
        return await message.answer("📭 Hozircha kitoblar yo'q. Ustozingizdan qo'shishni so'rang!")
    last_book = await db.get_last_read_book(message.from_user.id)
    await state.set_state(ReadingLog.waiting_for_book)
    await message.answer(
        "📚 Qaysi kitobni o'qiyapsiz? Ro'yxatdan tanlang:",
        reply_markup=book_selection_keyboard(books, last_book)
    )


@router.callback_query(F.data == "edit_today_reading", StateFilter("*"))
async def cb_edit_today_reading(call: CallbackQuery, state: FSMContext):
    await state.clear()
    books = await db.get_all_books()
    if not books:
        await call.message.edit_text("📭 Hozircha kitoblar yo'q.")
        return
    last_book = await db.get_last_read_book(call.from_user.id)
    await state.set_state(ReadingLog.waiting_for_book)
    await call.message.edit_text(
        "✏️ Qaysi kitobni o'qidingiz? Tanlang:",
        reply_markup=book_selection_keyboard(books, last_book)
    )
    await call.answer()


@router.callback_query(ReadingLog.waiting_for_book, F.data.startswith("sel_bk:"))
async def cb_select_book(call: CallbackQuery, state: FSMContext):
    book_id = int(call.data.split(":")[1])
    book = await db.get_book_by_id(book_id)
    book_name = book["name"] if book else "Noma'lum kitob"
    await state.update_data(book_name=book_name)
    await state.set_state(ReadingLog.waiting_for_pages)
    await call.message.edit_text(f"📖 Tanlangan kitob: **{book_name}**\n\n📄 Bugun nechta **bet** o'qidingiz? Raqam yuboring:")
    await call.answer()


@router.message(ReadingLog.waiting_for_book, F.text)
async def fsm_reading_book_manual(message: Message):
    await message.answer("⚠️ Iltimos, kitobni ro'yxatdan tanlang. Agar kitob yo'q bo'lsa, ustozingizga murojaat qiling.")


@router.message(ReadingLog.waiting_for_pages, F.text)
async def fsm_reading_pages(message: Message, state: FSMContext):
    try:
        pages = int(message.text.strip())
        if pages <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("⚠️ Iltimos, to'g'ri bet raqamini yuboring (masalan: 15).")
    await state.update_data(pages_read=pages)
    await state.set_state(ReadingLog.waiting_for_photo)
    await message.answer(
        "📷 Kitobning **rasmini** yuklashni xohlaysizmi? (ixtiyoriy)\n"
        "Rasm yuboring yoki **O'tkazib yuborish** tugmasini bosing.",
        reply_markup=skip_keyboard("skip_book_photo"),
    )


@router.message(F.text == "/reminder")
async def cmd_reminder(message: Message, state: FSMContext):
    # Disable reminder
    if message.get_args().strip().lower() == "off":
        await db.disable_reminder(message.from_user.id)
        await message.answer("✅ Eslatma o'chirildi.")
        return
    await state.set_state(Reminder.waiting_for_time)
    await message.answer("⏰ Iltimos, eslatma vaqtini HH:MM formatida kiriting (24‑soat).")

@router.message(Reminder.waiting_for_time, F.text)
async def set_reminder_time(message: Message, state: FSMContext):
    time_str = message.text.strip()
    # Simple validation
    try:
        datetime.strptime(time_str, "%H:%M")
    except Exception:
        await message.answer("⚠️ Noto'g'ri format. Iltimos, HH:MM formatida vaqt kiriting.")
        return
    await db.set_reminder(message.from_user.id, time_str)
    await state.clear()
    await message.answer(f"✅ Eslatma {time_str} da har kuni yuboriladi.")

# Callbacks from reminder notifications
@router.callback_query(F.data == "reminder_exercises")
async def cb_reminder_exercises(call: CallbackQuery):
    await call.message.delete()
    await btn_log_exercises(call.message)
    await call.answer()

@router.callback_query(F.data == "reminder_reading")
async def cb_reminder_reading(call: CallbackQuery):
    await call.message.delete()
    await btn_log_reading(call.message)
    await call.answer()

async def fsm_reading_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_reading_submission(
        message.from_user.id, data["book_name"], data["pages_read"],
        photo_file_id=message.photo[-1].file_id,
    )
    await state.clear()
    user = await db.get_user(message.from_user.id)
    name = user["name"] if user else "O'quvchi"
    keyboard = await get_role_keyboard(message.from_user.id, user["role"] if user else "student")
    await message.answer(
        f"👤 **O'quvchi:** {name}\n"
        f"✅ **Kitob o'qish belgilandi!**\n"
        f"📅 **Sana:** {date.today().strftime('%d.%m.%Y')}\n"
        f"📖 Kitob: {data['book_name']}\n"
        f"📄 Betlar: {data['pages_read']}\n"
        f"📷 Rasm: yuklandi ✅",
        reply_markup=keyboard,
    )


@router.callback_query(F.data == "skip_book_photo", ReadingLog.waiting_for_photo)
async def cb_skip_book_photo(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await db.add_reading_submission(
        call.from_user.id, data["book_name"], data["pages_read"], photo_file_id=None,
    )
    await state.clear()
    user = await db.get_user(call.from_user.id)
    name = user["name"] if user else "O'quvchi"
    await call.message.edit_text(
        f"👤 **O'quvchi:** {name}\n"
        f"✅ **Kitob o'qish belgilandi!**\n"
        f"📅 **Sana:** {date.today().strftime('%d.%m.%Y')}\n"
        f"📖 Kitob: {data['book_name']}\n"
        f"📄 Betlar: {data['pages_read']}"
    )
    await call.answer()


# -- Bugungi natijalar: Vazifa --

@router.message(F.text == "💪 Vazifa natijalari")
async def btn_my_exercise_stats(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or user["is_active"] == 0:
        return await message.answer("Iltimos, avval /start buyrug'i orqali ro'yxatdan o'ting.")

    today = date.today()
    done_ids = await db.get_student_exercise_ids_today(message.from_user.id)
    exercises = await db.get_active_exercises()
    done_names = [ex["name"] for ex in exercises if ex["id"] in done_ids]
    video = await db.get_exercise_video(message.from_user.id)

    text = f"👤 **O'quvchi:** {user['name']}\n"
    text += f"📊 **Bugungi vazifalar — {today.strftime('%d.%m.%Y')}**\n\n"
    
    # Check for skips
    stats = await db.get_report_data(today)
    my_stats = next((s for s in stats if s["telegram_id"] == message.from_user.id), None)

    if my_stats and my_stats["exercises"] == ["Bajarmadi 🚫"]:
         text += "💪 **Holat:** Bajarmadi 🚫"
    elif done_names:
        text += "💪 **Bajarilganlar:**\n" + "\n".join(f"  ✅ {n}" for n in done_names)
        text += f"\n  🎥 Video: {'yuklandi ✅' if video else 'yuklanmagan'}"
    else:
        text += "💪 **Holat:** Hali belgilanmagan"

    await message.answer(text)


# -- Bugungi natijalar: Kitob --

@router.message(F.text == "📚 Kitob natijalari")
async def btn_my_reading_stats(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user or user["is_active"] == 0:
        return await message.answer("Iltimos, avval /start buyrug'i orqali ro'yxatdan o'ting.")

    today = date.today()
    reading = await db.get_reading_today(message.from_user.id)

    text = f"👤 **O'quvchi:** {user['name']}\n"
    text += f"📊 **Bugungi kitob o'qish — {today.strftime('%d.%m.%Y')}**\n\n"
    
    # Check for skips
    stats = await db.get_report_data(today)
    my_stats = next((s for s in stats if s["telegram_id"] == message.from_user.id), None)

    if my_stats and my_stats["reading"] and my_stats["reading"]["book_name"] == "Bajarmadi 🚫":
         text += "📚 **Holat:** Bajarmadi 🚫"
    elif reading:
        text += (
            f"📚 **Bajarilgan:**\n"
            f"  📖 {reading['book_name']} — {reading['pages_read']} bet\n"
            f"  📷 Rasm: {'yuklandi ✅' if reading['photo_file_id'] else 'yuklanmagan'}"
        )
    else:
        text += "📚 **Holat:** Hali belgilanmagan"

    await message.answer(text)


@router.callback_query(F.data == "del_today_video", StateFilter("*"))
async def cb_del_today_video(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await db.delete_exercise_video_today(call.from_user.id)
    await call.message.edit_text("✅ Video muvaffaqiyatli o'chirildi! Qolgan vazifalar saqlanib qoldi.")
    await call.answer()

@router.callback_query(F.data == "del_today_reading", StateFilter("*"))
async def cb_del_today_reading(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await db.reset_reading_today(call.from_user.id)
    await call.message.edit_text("✅ Bugungi kitob o'qish qaydi muvaffaqiyatli o'chirildi!")
    await call.answer()


@router.callback_query(F.data == "skip_exercises_all", StateFilter("*"))
async def cb_skip_exercises_all(call: CallbackQuery, state: FSMContext):
    await db.add_skip_submission(call.from_user.id, "exercise_skip")
    await db.mark_exercises_submitted(call.from_user.id)
    user = await db.get_user(call.from_user.id)
    name = user["name"] if user else "O'quvchi"
    await call.message.edit_text(f"👤 **O'quvchi:** {name}\n🚫 Bugun vazifa bajarilmasligi belgilandi.")
    await call.answer("Saqlandi")
    
    await state.set_state(ExerciseMedia.waiting_for_video)
    await call.message.answer(
        "📹 Vazifalaringizning **videosini** yuklashni xohlaysizmi? (ixtiyoriy)\n"
        "Video yuboring yoki **O'tkazib yuborish** tugmasini bosing.",
        reply_markup=skip_keyboard("skip_exercise_video"),
    )

@router.callback_query(F.data == "skip_reading_all", StateFilter("*"))
async def cb_skip_reading_all(call: CallbackQuery, state: FSMContext):
    await db.add_skip_submission(call.from_user.id, "reading_skip")
    await state.clear()
    user = await db.get_user(call.from_user.id)
    name = user["name"] if user else "O'quvchi"
    await call.message.edit_text(f"👤 **O'quvchi:** {name}\n🚫 Bugun kitob o'qilmasligi belgilandi.")
    await call.answer("Saqlandi")
    
    user = await db.get_user(call.from_user.id)
    keyboard = await get_role_keyboard(call.from_user.id, user["role"] if user else "student")
    await call.message.answer("Asosiy menyuga qaytdik.", reply_markup=keyboard)
