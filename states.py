from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_class = State()


class AddExercise(StatesGroup):
    waiting_for_name = State()


class EditExercise(StatesGroup):
    waiting_for_new_name = State()


class SetGroup(StatesGroup):
    waiting_for_class = State()
    waiting_for_chat_id = State()


class ReadingLog(StatesGroup):
    waiting_for_book = State()
    waiting_for_pages = State()
    waiting_for_photo = State()


class ExerciseMedia(StatesGroup):
    waiting_for_video = State()


class AddClass(StatesGroup):
    waiting_for_name = State()


class AddBook(StatesGroup):
    waiting_for_name = State()


class EditClass(StatesGroup):
    waiting_for_new_name = State()


class EditBook(StatesGroup):
    waiting_for_new_name = State()


class TeacherReport(StatesGroup):
    waiting_for_date = State()
    waiting_for_date_range = State()


class ManageStudent(StatesGroup):
    waiting_for_new_class = State()


# New state for reminder setting
class Reminder(StatesGroup):
    waiting_for_time = State()
