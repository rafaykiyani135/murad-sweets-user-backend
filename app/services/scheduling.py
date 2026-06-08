from datetime import datetime, date, time, timedelta, timezone
from typing import List, Tuple
from fastapi import HTTPException

# Map slots to approximate start times for lead-time calculation
SLOT_TIMES = {
    "Morning": time(10, 0),
    "Afternoon": time(13, 0),
    "Evening": time(17, 0)
}

def validate_schedule(scheduled_date: date, slot: str, max_prep_time_hours: int) -> bool:
    """
    Validates if the scheduled date and slot respect:
    1. Date is in the future (minimum tomorrow).
    2. Lead prep time is respected.
    """
    now = datetime.now(timezone.utc)
    
    # 1. Date check: must be >= tomorrow (local date)
    # Note: For simplicity and server time alignment, we compare date objects.
    # The client must select tomorrow or later.
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    if scheduled_date < tomorrow:
        raise HTTPException(
            status_code=400,
            detail="Fulfillment date must be scheduled at least 1 day in advance (tomorrow or later)."
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
