from datetime import date

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_IDS
from keyboards import student_menu_keyboard, teacher_menu_keyboard, admin_menu_keyboard, exercises_keyboard, skip_keyboard
from states import Registration, ReadingLog, ExerciseMedia

router = Router()


# ── Yordamchi: rolga mos klaviatura ───────────────────────────────────────────

async def get_role_keyboard(user_id: int, db_role: str):
    if user_id in ADMIN_IDS or db_role == "admin":
        return admin_menu_keyboard()
    elif db_role == "teacher":
        return teacher_menu_keyboard()
    else:
        return student_menu_keyboard()


# ── /start ─────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = await db.get_user(message.from_user.id)
    if user:
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
        "👋 **Mashq kuzatuv botiga** xush kelibsiz!\n\n"
        "Keling, ro'yxatdan o'tamiz. Iltimos, **to'liq ismingizni** yuboring:"
    )


# ── Ro'yxatdan o'tish ──────────────────────────────────────────────────────────

@router.message(Registration.waiting_for_name)
async def fsm_get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(Registration.waiting_for_class)
    await message.answer("📚 Ajoyib! Endi **sinf nomingizni** yuboring (masalan: 5-A sinf):")


@router.message(Registration.waiting_for_class)
async def fsm_get_class(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    class_name = message.text.strip()
    await db.create_user(message.from_user.id, name, class_name)
    await state.clear()
    await message.answer(
        f"✅ **Muvaffaqiyatli ro'yxatdan o'tdingiz!**\n\n"
        f"👤 Ism: {name}\n"
        f"🏫 Sinf: {class_name}\n\n"
        f"Quyidagi menyu orqali kunlik mashqlaringizni belgilang.",
        reply_markup=student_menu_keyboard(),
    )


# ── 📋 Mashqlarni belgilash ────────────────────────────────────────────────────

@router.message(F.text == "📋 Mashqlarni belgilash")
async def btn_log_exercises(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return await message.answer("Iltimos, avval /start buyrug'i orqali ro'yxatdan o'ting.")
    exercises = await db.get_active_exercises()
    if not exercises:
        return await message.answer("📭 Hozircha mashqlar yo'q. Admindan qo'shishni so'rang!")
    done_ids = await db.get_student_exercise_ids_today(message.from_user.id)
    await message.answer(
        "📋 **Bugungi mashqlar**\n"
        "Belgilash ✅ / bekor qilish uchun bosing. Tugatgach **Tayyor** tugmasini bosing.",
        reply_markup=exercises_keyboard(exercises, done_ids),
    )


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

    if done_names:
        summary = "✅ **Belgilangan mashqlar:**\n" + "\n".join(f"  • {n}" for n in done_names)
    else:
        summary = "📭 Hech qanday mashq tanlanmagan."

    await call.message.edit_text(summary)
    await call.answer("Saqlandi!")

    await state.set_state(ExerciseMedia.waiting_for_video)
    await call.message.answer(
        "📹 Mashqlaringizning **videosini** yuklashni xohlaysizmi? (ixtiyoriy)\n"
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


# ── 📚 Kitob o'qishni belgilash ───────────────────────────────────────────────

@router.message(F.text == "📚 Kitob o'qishni belgilash")
async def btn_log_reading(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user:
        return await message.answer("Iltimos, avval /start buyrug'i orqali ro'yxatdan o'ting.")
    await state.set_state(ReadingLog.waiting_for_book)
    await message.answer("📚 Qaysi kitobni o'qiyapsiz? **Kitob nomini** yuboring:")


@router.message(ReadingLog.waiting_for_book)
async def fsm_reading_book(message: Message, state: FSMContext):
    await state.update_data(book_name=message.text.strip())
    await state.set_state(ReadingLog.waiting_for_pages)
    await message.answer("📄 Bugun nechta **bet** o'qidingiz? Raqam yuboring:")


@router.message(ReadingLog.waiting_for_pages)
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


@router.message(ReadingLog.waiting_for_photo, F.photo)
async def fsm_reading_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_reading_submission(
        message.from_user.id, data["book_name"], data["pages_read"],
        photo_file_id=message.photo[-1].file_id,
    )
    await state.clear()
    user = await db.get_user(message.from_user.id)
    keyboard = await get_role_keyboard(message.from_user.id, user["role"] if user else "student")
    await message.answer(
        f"✅ **Kitob o'qish belgilandi!**\n\n"
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
    await call.message.edit_text(
        f"✅ **Kitob o'qish belgilandi!**\n\n"
        f"📖 Kitob: {data['book_name']}\n"
        f"📄 Betlar: {data['pages_read']}"
    )
    await call.answer()


# ── 📊 Bugungi natijalarim ─────────────────────────────────────────────────────

@router.message(F.text == "📊 Bugungi natijalarim")
async def btn_my_stats(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return await message.answer("Iltimos, avval /start buyrug'i orqali ro'yxatdan o'ting.")

    today = date.today()
    done_ids = await db.get_student_exercise_ids_today(message.from_user.id)
    exercises = await db.get_active_exercises()
    done_names = [ex["name"] for ex in exercises if ex["id"] in done_ids]
    video = await db.get_exercise_video(message.from_user.id)
    reading = await db.get_reading_today(message.from_user.id)

    text = f"📊 **Bugungi natijalar — {today.strftime('%d.%m.%Y')}**\n\n"
    if done_names:
        text += "💪 **Mashqlar:**\n" + "\n".join(f"  ✅ {n}" for n in done_names)
        text += f"\n  🎥 Video: {'yuklandi ✅' if video else 'yuklanmagan'}\n\n"
    else:
        text += "💪 **Mashqlar:** Hali belgilanmagan\n\n"
    if reading:
        text += (
            f"📚 **Kitob o'qish:**\n"
            f"  📖 {reading['book_name']} — {reading['pages_read']} bet\n"
            f"  📷 Rasm: {'yuklandi ✅' if reading['photo_file_id'] else 'yuklanmagan'}"
        )
    else:
        text += "📚 **Kitob o'qish:** Hali belgilanmagan"

    await message.answer(text)
