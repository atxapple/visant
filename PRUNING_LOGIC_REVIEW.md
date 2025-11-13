# Pruning Logic Review - Issues Found

## Issues Identified

### 1. **Frontend Timezone Conversion Issue** (CRITICAL)
**Location**: `cloud/web/templates/admin.html:682`

**Problem**:
```javascript
if (beforeDate) payload.before_date = new Date(beforeDate).toISOString();
```

When a user selects a date/time in a `datetime-local` input (e.g., "2025-11-13T14:30"), JavaScript interprets it as **local time** and converts it to UTC. This can cause unexpected behavior:

- User in EST (UTC-5) selects: `2025-11-13T14:30` (2:30 PM local)
- JavaScript converts to: `2025-11-13T19:30:00.000Z` (7:30 PM UTC)
- Backend compares: `captured_at < 2025-11-13T19:30:00Z`
- **Issue**: If user expects to delete captures before 2:30 PM local time, the comparison uses 7:30 PM UTC, which may not match their expectation.

**Impact**: Users in different timezones will see different results for the same date selection.

### 2. **Backend Timezone Handling Issue** (CRITICAL)
**Location**: `cloud/api/routes/admin.py:388`

**Problem**:
```python
if request.before_date:
    before_dt = datetime.fromisoformat(request.before_date.replace('Z', '+00:00'))
    query = query.filter(Capture.captured_at < before_dt)
```

**Issues**:
1. If `request.before_date` doesn't have timezone info (e.g., "2025-11-13T19:30:00"), `fromisoformat` creates a **naive datetime**.
2. The database `captured_at` field is stored as `DateTime` (line 155 in models.py), which may be timezone-aware or naive depending on how it was stored.
3. Comparing timezone-aware and naive datetimes can cause incorrect results or errors.
4. No error handling for invalid date formats.

**Impact**: Incorrect date comparisons, potential timezone mismatch errors.

### 3. **Missing Timezone Awareness** (MEDIUM)
**Location**: `cloud/api/routes/admin.py:388`

The code doesn't ensure the datetime is timezone-aware before comparison. It should:
- Ensure `before_dt` is timezone-aware (UTC)
- Handle both timezone-aware and naive datetimes from the database

### 4. **No Input Validation** (LOW)
**Location**: `cloud/api/routes/admin.py:387-389`

No validation for:
- Invalid date formats
- Empty strings
- Malformed ISO 8601 strings

## Recommended Fixes

### Fix 1: Frontend - Proper Timezone Handling
Convert the datetime-local input to UTC explicitly, considering the user's timezone:

```javascript
if (beforeDate) {
    // datetime-local input is in user's local timezone
    // Convert to UTC ISO string explicitly
    const localDate = new Date(beforeDate);
    payload.before_date = localDate.toISOString();
}
```

**Better approach**: Keep the conversion but add a comment explaining the behavior, or convert to UTC explicitly.

### Fix 2: Backend - Ensure Timezone Awareness
Use a helper function similar to `_parse_datetime_filter` in `devices.py`:

```python
def _parse_prune_date(date_str: str) -> datetime:
    """Parse ISO 8601 date string and ensure timezone-aware datetime in UTC."""
    if not date_str or not date_str.strip():
        raise ValueError("Empty date string")
    
    date_str = date_str.strip()
    
    # Try ISO 8601 format (with timezone)
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to UTC if not already
        if dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        return dt
    except ValueError as e:
        raise ValueError(f"Invalid date format: '{date_str}'. Expected ISO 8601 format.")
```

### Fix 3: Add Error Handling
Wrap date parsing in try-except and return proper error messages.

### Fix 4: Database Comparison
Ensure both sides of the comparison are timezone-aware:

```python
if request.before_date:
    try:
        before_dt = _parse_prune_date(request.before_date)
        # Ensure captured_at comparison works with timezone-aware datetime
        query = query.filter(Capture.captured_at < before_dt)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid before_date format: {str(e)}"
        )
```

## Testing Recommendations

1. Test with different timezones (EST, PST, UTC, etc.)
2. Test with timezone-aware and naive datetimes
3. Test edge cases (midnight, DST transitions)
4. Test invalid date formats
5. Verify the comparison logic matches user expectations

