import asyncio
from datetime import date, timedelta
import database as db

async def mock_seed():
    await db.init_db()
    # Add a user
    await db.create_user(111, "Ali Valiyev", "10-A")
    await db.create_user(222, "Olimjon", "10-A")
    
    # Add exercise
    await db.add_exercise("Matematika")
    await db.add_exercise("Fizika")
    
    today = date.today()
    
    # Submit exercise today
    await db.toggle_exercise_submission(111, 1, today)
    await db.toggle_exercise_submission(222, 2, today)
    
    # Add a book and reading
    await db.add_book("O'tkan kunlar")
    await db.add_reading_submission(111, "O'tkan kunlar", 15, "photo123", today)
    
    print("Seeded database with mock data.")

if __name__ == "__main__":
    asyncio.run(mock_seed())
