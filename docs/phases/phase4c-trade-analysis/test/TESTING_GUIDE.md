# Phase 4C Testing Guide

## Overview

This document describes the testing approach for Phase 4C - Trade Analysis & Linking. All tests are implemented as PowerShell scripts that can be run against the running server.

## Prerequisites

1. **Server must be running:**
   ```powershell
   docker-compose up -d
   ```
   Or if running locally:
   ```powershell
   python -m uvicorn server.app:app --reload
   ```

2. **Server should be accessible at:** `http://localhost:8000`

## Test Suites

### 1. API Integration Tests (`test_phase4c_apis.ps1`)

Tests all analytics API endpoints for correct functionality:

- ✅ `GET /analytics/overview` - Overview statistics
- ✅ `GET /analytics/entry-methods` - Statistics per entry method
- ✅ `GET /analytics/entry-methods/{id}` - Detailed stats for specific entry method
- ✅ `GET /analytics/comparison` - Compare entry methods side-by-side
- ✅ `GET /analytics/time-patterns` - Performance by trading session
- ✅ `GET /analytics/direction-patterns` - Performance by direction
- ✅ `GET /trades?session={session}` - Session filtering
- ✅ `GET /trades?entry_method_id={id}` - Entry method filtering
- ✅ `GET /trades?has_entry_method={bool}` - Has entry method filtering

### 2. Edge Cases and Error Handling (`test_phase4c_edge_cases.ps1`)

Tests edge cases and error handling:

- ✅ Analytics overview with no trades (should handle gracefully)
- ✅ Entry method detail with invalid ID (should return 404)
- ✅ Session filter with invalid session (should handle gracefully)
- ✅ Entry method filter with non-existent ID (should return empty)
- ✅ Comparison with no entry methods (should handle gracefully)
- ✅ Time patterns with no trades (should handle gracefully)
- ✅ Direction patterns with no trades (should handle gracefully)
- ✅ Multiple filters combined (session + direction + outcome)
- ✅ Session detection with null entry_time (should handle gracefully)
- ✅ Large limit value (should be capped at 500)

### 3. Statistics Calculation Tests (`test_phase4c_statistics.ps1`)

Tests statistics calculation logic and accuracy:

- ✅ Win rate calculation accuracy
- ✅ Entry method statistics accuracy
- ✅ Session detection accuracy
- ✅ Time patterns statistics accuracy
- ✅ Direction patterns statistics accuracy
- ✅ Average P&L calculation
- ✅ R-multiple calculation

## Running Tests

### Run All Tests

```powershell
cd trading-ai-extension/docs/phases/phase4c-trade-analysis/test
powershell -ExecutionPolicy Bypass -File run_all_tests.ps1
```

### Run Individual Test Suites

```powershell
# API Integration Tests
powershell -ExecutionPolicy Bypass -File test_phase4c_apis.ps1

# Edge Cases
powershell -ExecutionPolicy Bypass -File test_phase4c_edge_cases.ps1

# Statistics Tests
powershell -ExecutionPolicy Bypass -File test_phase4c_statistics.ps1
```

## Manual Testing Checklist

In addition to automated tests, please verify:

### Analytics Dashboard (`/app/analytics.html`)
- [ ] Dashboard loads correctly
- [ ] Overview cards display correct data
- [ ] Charts render properly (dark theme, text visible)
- [ ] Statistics table displays entry methods
- [ ] Data updates when trades are linked to entry methods

### Trade List Filtering (`/app/`)
- [ ] Session filter works (London, NY, Asian)
- [ ] Entry method filter works
- [ ] "Has entry method" filter works
- [ ] Multiple filters work together
- [ ] CSV export works correctly
- [ ] Entry method column displays correctly

### Linking/Unlinking
- [ ] Link trade to setup/entry method works
- [ ] Unlink trade works (via "Unlink" button)
- [ ] Unlink via "No setup"/"No entry method" works
- [ ] Trade list refreshes after linking/unlinking

### Session Detection
- [ ] London session (2 AM - 11 AM EST) detected correctly
- [ ] NY session (8 AM - 4 PM EST) detected correctly
- [ ] Asian session (5 PM - 2 AM EST) detected correctly
- [ ] Overlap period (8 AM - 11 AM) assigned to NY

## Expected Results

### API Integration Tests
- All endpoints should return 200 OK
- Response formats should match expected structure
- Data should be accurate and consistent

### Edge Cases
- Invalid inputs should be handled gracefully
- 404 errors for non-existent resources
- Empty results should return empty arrays, not errors

### Statistics Tests
- Win rates should be calculated correctly (wins / total_trades * 100)
- All statistics should be consistent across endpoints
- Session detection should match expected time ranges

## Troubleshooting

### Server Not Running
```
ERROR Server is not running. Please start the server first.
```
**Solution:** Start the server using `docker-compose up -d` or run the server locally.

### Connection Refused
```
Failed: The remote server returned an error: (500) Internal Server Error
```
**Solution:** Check server logs for errors. Ensure database is accessible and migrations are applied.

### Test Failures
- Check server logs for detailed error messages
- Verify database has test data
- Ensure all migrations are applied
- Check that entry methods and trades are properly linked

## Test Coverage

### Unit Tests
- ✅ Statistics calculation logic
- ✅ Pattern recognition algorithms
- ✅ Filtering/grouping logic
- ✅ Session detection logic

### Integration Tests
- ✅ Statistics API endpoints
- ✅ Filtering API endpoints
- ✅ Dashboard data loading

### Manual Tests
- ✅ Dashboard displays correctly
- ✅ Charts render properly
- ✅ Filtering works as expected
- ✅ Statistics update correctly

## Notes

- Tests assume server is running on `http://localhost:8000`
- Tests use existing database data (no test data is created)
- Some tests may skip if no data exists (e.g., no entry methods)
- Tests verify both happy path and error cases

---

**Last Updated:** 2025-11-05  
**Phase:** Phase 4C - Trade Analysis & Linking

