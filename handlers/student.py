from datetime import date

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import main_menu_keyboard, exercises_keyboard, skip_keyboard
from states import Registration, ReadingLog, ExerciseMedia

router = Router()


# ── /start — registration flow ─────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if user:
        await message.answer(
            f"👋 Welcome back, **{user['name']}**!\n\nWhat would you like to log today?",
            reply_markup=main_menu_keyboard(),
        )
        return
    await state.set_state(Registration.waiting_for_name)
    await message.answer(
        "👋 Welcome to the **Exercise Tracker Bot**!\n\n"
        "Let's get you registered. Please send your **full name**:"
    )


@router.message(Registration.waiting_for_name)
async def fsm_get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(Registration.waiting_for_class)
    await message.answer("📚 Great! Now send your **class name** (e.g. Grade 5A):")


@router.message(Registration.waiting_for_class)
async def fsm_get_class(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    class_name = message.text.strip()
    await db.create_user(message.from_user.id, name, class_name)
    await state.clear()
    await message.answer(
        f"✅ **Registered successfully!**\n\n"
        f"👤 Name: {name}\n"
        f"🏫 Class: {class_name}\n\n"
        f"Use the menu below to start logging.",
        reply_markup=main_menu_keyboard(),
    )


# ── 📋 Log Exercises ───────────────────────────────────────────────────────────

@router.message(F.text == "📋 Log Exercises")
async def btn_log_exercises(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return await message.answer("Please /start to register first.")
    exercises = await db.get_active_exercises()
    if not exercises:
        return await message.answer("📭 No exercises available yet. Ask your admin to add some!")
    done_ids = await db.get_student_exercise_ids_today(message.from_user.id)
    await message.answer(
        "📋 **Today's Exercises**\nTap to check ✅ / uncheck. Press **Done** when finished.",
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
        summary = "✅ **Exercises logged:**\n" + "\n".join(f"  • {n}" for n in done_names)
    else:
        summary = "📭 No exercises selected yet."

    await call.message.edit_text(summary)
    await call.answer("Saved!")

    # Ask for optional exercise video
    await state.set_state(ExerciseMedia.waiting_for_video)
    await call.message.answer(
        "📹 Want to upload a **video** of your exercises? (optional)\n"
        "Send a video, or tap **Skip**.",
        reply_markup=skip_keyboard("skip_exercise_video"),
    )


@router.message(ExerciseMedia.waiting_for_video, F.video)
async def fsm_exercise_video(message: Message, state: FSMContext):
    file_id = message.video.file_id
    await db.save_exercise_video(message.from_user.id, file_id)
    await state.clear()
    await message.answer("🎥 Video uploaded! Great job 💪", reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "skip_exercise_video", ExerciseMedia.waiting_for_video)
async def cb_skip_exercise_video(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("⏭ Video skipped.")
    await call.answer()


# ── 📚 Log Reading ─────────────────────────────────────────────────────────────

@router.message(F.text == "📚 Log Reading")
async def btn_log_reading(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if not user:
        return await message.answer("Please /start to register first.")
    await state.set_state(ReadingLog.waiting_for_book)
    await message.answer("📚 What book are you reading? Send the **book name**:")


@router.message(ReadingLog.waiting_for_book)
async def fsm_reading_book(message: Message, state: FSMContext):
    await state.update_data(book_name=message.text.strip())
    await state.set_state(ReadingLog.waiting_for_pages)
    await message.answer("📄 How many **pages** did you read today? Send a number:")


@router.message(ReadingLog.waiting_for_pages)
async def fsm_reading_pages(message: Message, state: FSMContext):
    try:
        pages = int(message.text.strip())
        if pages <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("⚠️ Please send a valid number of pages (e.g. 15).")

    await state.update_data(pages_read=pages)
    await state.set_state(ReadingLog.waiting_for_photo)
    await message.answer(
        "📷 Want to upload a **photo** of the book? (optional)\n"
        "Send a photo, or tap **Skip**.",
        reply_markup=skip_keyboard("skip_book_photo"),
    )


@router.message(ReadingLog.waiting_for_photo, F.photo)
async def fsm_reading_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    photo_file_id = message.photo[-1].file_id  # highest resolution
    await db.add_reading_submission(
        message.from_user.id,
        data["book_name"],
        data["pages_read"],
        photo_file_id=photo_file_id,
    )
    await state.clear()
    await message.answer(
        f"✅ **Reading logged!**\n\n"
        f"📖 Book: {data['book_name']}\n"
        f"📄 Pages: {data['pages_read']}\n"
        f"📷 Photo: uploaded",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "skip_book_photo", ReadingLog.waiting_for_photo)
async def cb_skip_book_photo(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await db.add_reading_submission(
        call.from_user.id,
        data["book_name"],
        data["pages_read"],
        photo_file_id=None,
    )
    await state.clear()
    await call.message.edit_text(
        f"✅ **Reading logged!**\n\n"
        f"📖 Book: {data['book_name']}\n"
        f"📄 Pages: {data['pages_read']}"
    )
    await call.answer()


# ── 📊 My Stats Today ──────────────────────────────────────────────────────────

@router.message(F.text == "📊 My Stats Today")
async def btn_my_stats(message: Message):
    user = await db.get_user(message.from_user.id)
    if not user:
        return await message.answer("Please /start to register first.")

    today = date.today()
    done_ids = await db.get_student_exercise_ids_today(message.from_user.id)
    exercises = await db.get_active_exercises()
    done_names = [ex["name"] for ex in exercises if ex["id"] in done_ids]
    video = await db.get_exercise_video(message.from_user.id)
    reading = await db.get_reading_today(message.from_user.id)

    text = f"📊 **Your Stats — {today.strftime('%d %B %Y')}**\n\n"

    if done_names:
        text += "💪 **Exercises:**\n" + "\n".join(f"  ✅ {n}" for n in done_names)
        text += f"\n  🎥 Video: {'uploaded' if video else 'not uploaded'}\n\n"
    else:
        text += "💪 **Exercises:** None logged\n\n"

    if reading:
        text += (
            f"📚 **Reading:**\n"
            f"  📖 {reading['book_name']} — {reading['pages_read']} pages\n"
            f"  📷 Photo: {'uploaded' if reading['photo_file_id'] else 'not uploaded'}"
        )
    else:
        text += "📚 **Reading:** None logged"

    await message.answer(text)
