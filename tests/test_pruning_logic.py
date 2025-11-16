#!/usr/bin/env python3
"""
Test script for pruning logic validation.

Tests the date parsing logic used in pruning endpoint.
"""

from datetime import datetime, timezone


def _parse_prune_date(date_str: str) -> datetime:
    """
    Parse ISO 8601 date string and ensure timezone-aware datetime in UTC.
    
    Handles both timezone-aware and naive ISO strings.
    Always returns UTC timezone-aware datetime for consistent database comparisons.
    """
    if not date_str or not date_str.strip():
        raise ValueError("Empty date string")
    
    date_str = date_str.strip()
    
    # Try ISO 8601 format (with or without timezone)
    try:
        # Replace 'Z' with '+00:00' for fromisoformat compatibility
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Ensure timezone-aware (assume UTC if naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to UTC if not already
        if dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
        return dt
    except ValueError as e:
        raise ValueError(f"Invalid date format: '{date_str}'. Expected ISO 8601 format (e.g., '2025-11-13T19:30:00Z').")


def test_timezone_parsing():
    """Test timezone parsing with various formats."""
    print("=" * 70)
    print("Testing Timezone Parsing")
    print("=" * 70)
    
    test_cases = [
        # (input, expected_utc_hour, description)
        ("2025-11-13T19:30:00Z", 19, "ISO 8601 with Z"),
        ("2025-11-13T19:30:00+00:00", 19, "ISO 8601 with +00:00"),
        ("2025-11-13T19:30:00-05:00", 0, "ISO 8601 with EST (UTC-5)"),
        ("2025-11-13T19:30:00+08:00", 11, "ISO 8601 with PST+8 (UTC+8)"),
        ("2025-11-13T19:30:00", 19, "ISO 8601 naive (assumed UTC)"),
        ("2025-11-13T00:00:00Z", 0, "Midnight UTC"),
        ("2025-11-13T23:59:59Z", 23, "End of day UTC"),
    ]
    
    passed = 0
    failed = 0
    
    for input_str, expected_hour, description in test_cases:
        try:
            result = _parse_prune_date(input_str)
            
            # Verify it's timezone-aware
            if result.tzinfo is None:
                print(f"[FAIL] {description}")
                print(f"   Input: {input_str}")
                print(f"   Error: Result is timezone-naive")
                failed += 1
                continue
            
            # Verify it's UTC
            if result.tzinfo != timezone.utc:
                print(f"[FAIL] {description}")
                print(f"   Input: {input_str}")
                print(f"   Error: Result is not UTC (got {result.tzinfo})")
                failed += 1
                continue
            
            # Verify hour matches expected
            if result.hour != expected_hour:
                print(f"[FAIL] {description}")
                print(f"   Input: {input_str}")
                print(f"   Expected hour: {expected_hour}, Got: {result.hour}")
                print(f"   Result: {result}")
                failed += 1
                continue
            
            print(f"[PASS] {description}")
            print(f"   Input: {input_str} -> {result} (UTC)")
            passed += 1
            
        except Exception as e:
            print(f"[FAIL] {description}")
            print(f"   Input: {input_str}")
            print(f"   Error: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\nTimezone Parsing: {passed} passed, {failed} failed")
    return failed == 0


def test_error_handling():
    """Test error handling for invalid inputs."""
    print("\n" + "=" * 70)
    print("Testing Error Handling")
    print("=" * 70)
    
    invalid_cases = [
        ("", "Empty string"),
        ("   ", "Whitespace only"),
        ("invalid-date", "Invalid format"),
        ("2025-13-45T99:99:99Z", "Invalid date values"),
        ("not-a-date", "Completely invalid"),
    ]
    
    # Valid cases that should work (date-only is valid ISO 8601)
    valid_cases = [
        ("2025-11-13", "Date only (treated as midnight UTC)"),
    ]
    
    passed = 0
    failed = 0
    
    for input_str, description in invalid_cases:
        try:
            result = _parse_prune_date(input_str)
            print(f"[FAIL] {description}")
            print(f"   Input: {input_str}")
            print(f"   Error: Should have raised ValueError, but got: {result}")
            failed += 1
        except ValueError as e:
            print(f"[PASS] {description}")
            print(f"   Input: {input_str}")
            print(f"   Error message: {str(e)}")
            passed += 1
        except Exception as e:
            print(f"[WARN] {description}")
            print(f"   Input: {input_str}")
            print(f"   Got {type(e).__name__} instead of ValueError: {e}")
            failed += 1
    
    # Test valid cases
    print("\nValid edge cases:")
    for input_str, description in valid_cases:
        try:
            result = _parse_prune_date(input_str)
            print(f"[PASS] {description}")
            print(f"   Input: {input_str} -> {result}")
            passed += 1
        except Exception as e:
            print(f"[FAIL] {description}")
            print(f"   Input: {input_str}")
            print(f"   Error: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\nError Handling: {passed} passed, {failed} failed")
    return failed == 0


def test_date_comparison_logic():
    """Test that date comparisons work correctly."""
    print("\n" + "=" * 70)
    print("Testing Date Comparison Logic")
    print("=" * 70)
    
    # Simulate database timestamps (timezone-aware UTC)
    db_timestamps = [
        datetime(2025, 11, 13, 14, 30, 0, tzinfo=timezone.utc),  # 2:30 PM UTC
        datetime(2025, 11, 13, 19, 30, 0, tzinfo=timezone.utc),  # 7:30 PM UTC
        datetime(2025, 11, 13, 20, 0, 0, tzinfo=timezone.utc),   # 8:00 PM UTC
    ]
    
    test_cases = [
        # (before_date_input, expected_count, description)
        # Note: Filter is "captured_at < before_dt", so exact matches are NOT included
        ("2025-11-13T15:00:00Z", 1, "Before 3 PM UTC (should include 2:30 PM, not 3 PM)"),
        ("2025-11-13T19:30:00Z", 1, "Before 7:30 PM UTC (should include 2:30 PM, not 7:30 PM itself)"),
        ("2025-11-13T19:31:00Z", 2, "Before 7:31 PM UTC (should include 2:30 and 7:30 PM)"),
        ("2025-11-13T20:00:00Z", 2, "Before 8:00 PM UTC (should include 2:30 and 7:30, not 8:00)"),
        ("2025-11-13T21:00:00Z", 3, "Before 9:00 PM UTC (should include all)"),
        ("2025-11-13T14:00:00Z", 0, "Before 2:00 PM UTC (should include none)"),
    ]
    
    passed = 0
    failed = 0
    
    for before_date_input, expected_count, description in test_cases:
        try:
            before_dt = _parse_prune_date(before_date_input)
            
            # Simulate the filter: captured_at < before_dt
            matching = [ts for ts in db_timestamps if ts < before_dt]
            actual_count = len(matching)
            
            if actual_count != expected_count:
                print(f"[FAIL] {description}")
                print(f"   Input: {before_date_input}")
                print(f"   Expected {expected_count} matches, got {actual_count}")
                print(f"   Before date: {before_dt}")
                print(f"   Matching timestamps: {matching}")
                failed += 1
            else:
                print(f"[PASS] {description}")
                print(f"   Input: {before_date_input} -> {actual_count} matches")
                passed += 1
                
        except Exception as e:
            print(f"[FAIL] {description}")
            print(f"   Input: {before_date_input}")
            print(f"   Error: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\nDate Comparison: {passed} passed, {failed} failed")
    return failed == 0


def test_timezone_conversion_examples():
    """Test real-world timezone conversion scenarios."""
    print("\n" + "=" * 70)
    print("Testing Real-World Timezone Conversions")
    print("=" * 70)
    
    # Simulate what frontend sends (UTC ISO strings from datetime-local input)
    scenarios = [
        {
            "user_timezone": "EST (UTC-5)",
            "user_input": "2025-11-13T14:30",  # 2:30 PM local
            "frontend_sends": "2025-11-13T19:30:00.000Z",  # 7:30 PM UTC
            "description": "EST user selects 2:30 PM local -> 7:30 PM UTC"
        },
        {
            "user_timezone": "PST (UTC-8)",
            "user_input": "2025-11-13T14:30",  # 2:30 PM local
            "frontend_sends": "2025-11-13T22:30:00.000Z",  # 10:30 PM UTC
            "description": "PST user selects 2:30 PM local -> 10:30 PM UTC"
        },
        {
            "user_timezone": "UTC",
            "user_input": "2025-11-13T14:30",  # 2:30 PM local
            "frontend_sends": "2025-11-13T14:30:00.000Z",  # 2:30 PM UTC
            "description": "UTC user selects 2:30 PM -> 2:30 PM UTC"
        },
    ]
    
    passed = 0
    failed = 0
    
    for scenario in scenarios:
        try:
            result = _parse_prune_date(scenario["frontend_sends"])
            
            # Verify it parses correctly
            if result.tzinfo != timezone.utc:
                print(f"[FAIL] {scenario['description']}")
                print(f"   Error: Result is not UTC")
                failed += 1
                continue
            
            # Verify the hour matches what frontend sent
            expected_hour = int(scenario["frontend_sends"].split("T")[1].split(":")[0])
            if result.hour != expected_hour:
                print(f"[FAIL] {scenario['description']}")
                print(f"   Expected hour: {expected_hour}, Got: {result.hour}")
                failed += 1
                continue
            
            print(f"[PASS] {scenario['description']}")
            print(f"   Parsed: {result}")
            passed += 1
            
        except Exception as e:
            print(f"[FAIL] {scenario['description']}")
            print(f"   Error: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\nTimezone Conversions: {passed} passed, {failed} failed")
    return failed == 0


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\n" + "=" * 70)
    print("Testing Edge Cases")
    print("=" * 70)
    
    edge_cases = [
        ("2025-11-13T00:00:00.000Z", "Midnight with milliseconds"),
        ("2025-11-13T23:59:59.999Z", "End of day with milliseconds"),
        ("2024-12-31T23:59:59Z", "Year boundary"),
        ("2025-01-01T00:00:00Z", "Year start"),
    ]
    
    # Invalid edge cases (should fail)
    invalid_edge_cases = [
        ("2025-02-29T12:00:00Z", "Invalid leap year date (2025 not a leap year)"),
    ]
    
    passed = 0
    failed = 0
    
    for input_str, description in edge_cases:
        try:
            result = _parse_prune_date(input_str)
            
            if result.tzinfo != timezone.utc:
                print(f"[FAIL] {description}")
                print(f"   Input: {input_str}")
                print(f"   Error: Result is not UTC")
                failed += 1
                continue
            
            print(f"[PASS] {description}")
            print(f"   Input: {input_str} -> {result}")
            passed += 1
            
        except Exception as e:
            print(f"[FAIL] {description}")
            print(f"   Input: {input_str}")
            print(f"   Error: {type(e).__name__}: {e}")
            failed += 1
    
    # Test invalid edge cases
    print("\nInvalid edge cases (should fail):")
    for input_str, description in invalid_edge_cases:
        try:
            result = _parse_prune_date(input_str)
            print(f"[FAIL] {description}")
            print(f"   Input: {input_str}")
            print(f"   Error: Should have raised ValueError, but got: {result}")
            failed += 1
        except ValueError as e:
            print(f"[PASS] {description}")
            print(f"   Input: {input_str}")
            print(f"   Error message: {str(e)}")
            passed += 1
        except Exception as e:
            print(f"[WARN] {description}")
            print(f"   Input: {input_str}")
            print(f"   Got {type(e).__name__} instead of ValueError: {e}")
            failed += 1
    
    print(f"\nEdge Cases: {passed} passed, {failed} failed")
    return failed == 0


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("PRUNING LOGIC TEST SUITE")
    print("=" * 70)
    print()
    
    results = []
    
    # Run all test suites
    results.append(("Timezone Parsing", test_timezone_parsing()))
    results.append(("Error Handling", test_error_handling()))
    results.append(("Date Comparison", test_date_comparison_logic()))
    results.append(("Timezone Conversions", test_timezone_conversion_examples()))
    results.append(("Edge Cases", test_edge_cases()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("[SUCCESS] ALL TESTS PASSED")
        return 0
    else:
        print("[ERROR] SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
