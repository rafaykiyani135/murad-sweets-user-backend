from datetime import datetime, date, time, timedelta
from typing import List, Tuple
from fastapi import HTTPException

# Map slots to approximate start times for lead-time calculation
SLOT_TIMES = {
    "Morning": time(10, 0),
    "Afternoon": time(13, 0),
    "Evening": time(17, 0)
}

# Preferred dates start tomorrow and stay inside a 90-day window from today.
MAX_SCHEDULE_DAYS = 90

def validate_schedule(scheduled_date: date, slot: str, max_prep_time_hours: int) -> bool:
    """
    Validates if the scheduled date and slot respect:
    1. Date is tomorrow or later (today and every earlier date are rejected).
    2. Date is within 90 days of today.
    3. Lead prep time is respected.
    """
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    latest = today + timedelta(days=MAX_SCHEDULE_DAYS)

    if scheduled_date < tomorrow:
        raise HTTPException(
            status_code=400,
            detail="Fulfillment date must be scheduled at least 1 day in advance (tomorrow or later)."
        )

    if scheduled_date > latest:
        raise HTTPException(
            status_code=400,
            detail=f"Fulfillment date must be within {MAX_SCHEDULE_DAYS} days from today."
        )

    # 2. Preorder lead-time check
    if max_prep_time_hours > 0:
        slot_time = SLOT_TIMES.get(slot, time(12, 0))  # Default to noon if slot not matched
        scheduled_datetime = datetime.combine(scheduled_date, slot_time).replace(tzinfo=None)
        
        # Convert now to naive local time for direct combination comparison
        local_now = datetime.now()
        lead_time_required = timedelta(hours=max_prep_time_hours)
        
        if scheduled_datetime < local_now + lead_time_required:
            raise HTTPException(
                status_code=400,
                detail=f"Selected date/time does not respect the minimum lead time of {max_prep_time_hours} hours required for your items."
            )
            
    return True
