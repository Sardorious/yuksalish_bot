from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_for_name = State()
    waiting_for_class = State()


class ReadingLog(StatesGroup):
    waiting_for_book = State()
    waiting_for_pages = State()
    waiting_for_photo = State()   # optional book photo upload


class ExerciseMedia(StatesGroup):
    waiting_for_video = State()   # optional exercise video upload


class EditExercise(StatesGroup):
    waiting_for_new_name = State()
