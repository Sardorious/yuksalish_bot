from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from config import ADMIN_IDS
from keyboards import admin_exercise_list_keyboard
from states import EditExercise

router = Router()


# ── Permission check ───────────────────────────────────────────────────────────

async def check_admin(message: Message) -> bool:
    user = await db.get_user(message.from_user.id)
    return message.from_user.id in ADMIN_IDS or (user is not None and user["role"] == "admin")


# ── /addexercise <name> ────────────────────────────────────────────────────────

@router.message(Command("addexercise"))
async def cmd_add_exercise(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Admin only command.")
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Usage: /addexercise <exercise name>")
    name = args[1].strip()
    success = await db.add_exercise(name)
    if success:
        await message.answer(f"✅ Exercise **{name}** added!")
    else:
        await message.answer(f"⚠️ Exercise **{name}** already exists.")


# ── /exercises ─────────────────────────────────────────────────────────────────

@router.message(Command("exercises"))
async def cmd_list_exercises(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Admin only command.")
    exercises = await db.get_active_exercises()
    if not exercises:
        return await message.answer("📭 No active exercises found.")
    text = "📋 **Active Exercises:**\n\n" + "\n".join(f"• {ex['name']}" for ex in exercises)
    await message.answer(text)


# ── /deleteexercise ────────────────────────────────────────────────────────────

@router.message(Command("deleteexercise"))
async def cmd_delete_exercise(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Admin only command.")
    exercises = await db.get_all_exercises()
    active = [ex for ex in exercises if ex["active"]]
    if not active:
        return await message.answer("📭 No active exercises to delete.")
    await message.answer(
        "Select an exercise to delete:",
        reply_markup=admin_exercise_list_keyboard(active, "delete"),
    )


@router.callback_query(F.data.startswith("delete_ex:"))
async def cb_delete_exercise(call: CallbackQuery):
    ex_id = int(call.data.split(":")[1])
    await db.delete_exercise(ex_id)
    await call.message.edit_text("🗑 Exercise deleted.")
    await call.answer("Deleted!")


# ── /editexercise ──────────────────────────────────────────────────────────────

@router.message(Command("editexercise"))
async def cmd_edit_exercise(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Admin only command.")
    exercises = await db.get_all_exercises()
    active = [ex for ex in exercises if ex["active"]]
    if not active:
        return await message.answer("📭 No active exercises to edit.")
    await message.answer(
        "Select an exercise to edit:",
        reply_markup=admin_exercise_list_keyboard(active, "edit"),
    )


@router.callback_query(F.data.startswith("edit_ex:"))
async def cb_edit_exercise_select(call: CallbackQuery, state: FSMContext):
    ex_id = int(call.data.split(":")[1])
    await state.set_state(EditExercise.waiting_for_new_name)
    await state.update_data(edit_ex_id=ex_id)
    await call.message.edit_text("✏️ Send the new name for this exercise:")
    await call.answer()


@router.message(EditExercise.waiting_for_new_name)
async def fsm_edit_exercise_name(message: Message, state: FSMContext):
    data = await state.get_data()
    ex_id = data["edit_ex_id"]
    new_name = message.text.strip()
    success = await db.update_exercise(ex_id, new_name)
    await state.clear()
    if success:
        await message.answer(f"✅ Exercise renamed to **{new_name}**.")
    else:
        await message.answer(f"⚠️ **{new_name}** already exists.")


# ── /promote <user_id> <role> ──────────────────────────────────────────────────

@router.message(Command("promote"))
async def cmd_promote(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Admin only command.")
    args = message.text.split()
    if len(args) < 3:
        return await message.answer("Usage: /promote <user_id> <teacher|admin|student>")
    try:
        target_id = int(args[1])
        role = args[2].lower()
    except ValueError:
        return await message.answer("❌ Invalid user ID.")
    if role not in ("teacher", "admin", "student"):
        return await message.answer("❌ Role must be: teacher, admin, or student")
    user = await db.get_user(target_id)
    if not user:
        return await message.answer(f"❌ User {target_id} not found in the database.")
    await db.promote_user(target_id, role)
    await message.answer(f"✅ **{user['name']}** is now a **{role}**.")


# ── /students ──────────────────────────────────────────────────────────────────

@router.message(Command("students"))
async def cmd_students(message: Message):
    if not await check_admin(message):
        return await message.answer("❌ Admin only command.")
    students = await db.get_all_students()
    if not students:
        return await message.answer("📭 No students registered yet.")
    text = f"👥 **Students ({len(students)} total):**\n"
    current_class = None
    for s in students:
        if s["class_name"] != current_class:
            current_class = s["class_name"]
            text += f"\n📌 **{current_class}**\n"
        text += f"  • {s['name']} (`{s['telegram_id']}`)\n"
    await message.answer(text)


# ── Cancel ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "cancel")
async def cb_cancel(call: CallbackQuery):
    await call.message.edit_text("❌ Cancelled.")
    await call.answer()
