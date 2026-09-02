import asyncio
import io
from datetime import date, timedelta
import openpyxl

import database as db

def build_excel_local(start_date, end_date, students, report_type, class_name=None):
    from handlers.teacher import build_excel
    return build_excel(start_date, end_date, students, report_type, class_name)

async def main():
    today = date.today()
    # 1. Day
    start_day = today
    end_day = today
    
    # 2. Week
    start_week = today - timedelta(days=today.weekday())
    end_week = today

    # 3. Month
    start_month = today.replace(day=1)
    end_month = today

    # 4. Custom (e.g. 2026-03-20 to 2026-04-06)
    start_custom = date(2026, 3, 20)
    end_custom = today

    periods = [
        ("today", start_day, end_day),
        ("week", start_week, end_week),
        ("month", start_month, end_month),
        ("custom", start_custom, end_custom)
    ]
    
    for pd_name, s, e in periods:
        data = await db.get_report_data(s, e)
        if data:
            # Exercise
            try:
                wb_ex = build_excel_local(s, e, data, "exercise")
                with open(f"report_exercise_{pd_name}.xlsx", "wb") as f:
                    f.write(wb_ex.read())
            except Exception as ex:
                print(f"Error building exercise excel for {pd_name}: {ex}")

            # Reading
            try:
                wb_rd = build_excel_local(s, e, data, "reading")
                with open(f"report_reading_{pd_name}.xlsx", "wb") as f:
                    f.write(wb_rd.read())
            except Exception as ex:
                 print(f"Error building reading excel for {pd_name}: {ex}")

if __name__ == "__main__":
    asyncio.run(main())
