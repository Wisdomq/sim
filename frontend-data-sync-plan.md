# Frontend Data Sync Issues - Analysis & Plan

## Problem Analysis

The frontend improvements are not reflecting actual database data. Based on the implementation, here are the identified issues:

### Root Causes

1. **Branch Home Screen - Local Database Dependency**
   - Changed from API calls to local database (`getSimCardsForBranch`, `getBas`)
   - Local database may be stale or not synced
   - No mechanism to ensure data freshness
   - User might not have synced recently

2. **Sync Mechanism Issues**
   - Background sync might not be running properly
   - Sync errors might be silently failing
   - No user visibility into sync status
   - No manual sync trigger

3. **Data Inconsistency**
   - API data (HQ/BA screens) is accurate
   - Local database data (Branch screen) is inaccurate
   - This confirms the issue is with local database synchronization

4. **Initial Data Population**
   - Local database might not be populated on first login
   - No initial sync trigger
   - Users might see empty data on first use

## Proposed Solutions

### Option 1: Hybrid Approach (Recommended)
**Use API for summary metrics, fallback to local database**

**Branch Home Screen:**
- Change back to API calls for summary metrics (like original plan)
- Keep local database for detailed views (stock, BA list)
- Add loading states and error handling
- Add manual refresh button

**Benefits:**
- Accurate data from server
- Faster than building complex sync logic
- Consistent with HQ/BA implementation
- Minimal changes needed

**Implementation:**
- Revert Branch home screen to use API calls
- Add `FutureProvider` for weekly report data
- Show loading states
- Add error handling with retry option
- Add refresh button

### Option 2: Enhanced Sync Strategy
**Improve local database synchronization**

**Changes Needed:**
- Force initial sync on login
- Add manual sync button
- Improve sync error visibility
- Add "last synced" timestamp
- Add data freshness indicators
- Implement periodic background sync

**Benefits:**
- True offline capability
- Faster subsequent loads
- Better user experience

**Drawbacks:**
- More complex implementation
- More points of failure
- Harder to debug sync issues
- May still have stale data issues

### Option 3: Progressive Enhancement
**Use API first, cache in local database**

**Approach:**
- Always fetch summary metrics from API
- Cache results in local database
- Use cached data when offline
- Show "last updated" timestamp
- Auto-refresh when online

**Benefits:**
- Best of both worlds
- Accurate when online
- Works offline with cached data
- Clear data freshness indicators

**Drawbacks:**
- More complex caching logic
- Cache invalidation needed
- Still needs sync infrastructure

## Recommended Implementation Plan

### Phase 1: Quick Fix (Immediate)
**Revert Branch home screen to API calls**

1. Change `_branchSummaryProvider` back to API-based implementation
2. Use `ApiConfig.reports` endpoint (like HQ home screen)
3. Add proper loading and error states
4. Add manual refresh button
5. Remove dependency on local database for summary metrics

**Estimated Time:** 30 minutes
**Risk:** Low (reverting to known working pattern)

### Phase 2: Data Consistency (Short-term)
**Ensure API-based metrics are consistent**

1. Standardize summary metric approach across all roles
2. Use same API endpoints where possible
3. Add consistent error handling
4. Add loading skeletons
5. Add refresh functionality

**Estimated Time:** 1 hour
**Risk:** Low

### Phase 3: Enhanced Offline Support (Long-term)
**Improve sync infrastructure**

1. Add forced sync on login
2. Add manual sync button to home screens
3. Improve sync error visibility
4. Add data freshness indicators
5. Implement periodic background sync
6. Add sync status to home screens

**Estimated Time:** 3-4 hours
**Risk:** Medium

## Specific Code Changes Needed

### Branch Home Screen (Priority 1)
```dart
// Change from local database to API calls
final _branchSummaryProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  try {
    final client = ref.read(apiClientProvider);
    final now = DateTime.now();
    final weekStart = now.subtract(Duration(days: now.weekday - 1));

    final resp = await client.post(
      ApiConfig.reports,
      data: {
        'period_type': 'WEEKLY',
        'period_start': '${weekStart.year}-${weekStart.month.toString().padLeft(2, '0')}-${weekStart.day.toString().padLeft(2, '0')}',
        'period_end': '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}',
      },
    );

    final data = resp.data as Map<String, dynamic>;
    final branches = (data['branch_reports'] as List?) ?? [];
    
    // Find current user's branch
    final auth = ref.read(authProvider);
    if (auth is! AuthAuthenticated) return {};
    
    final myBranch = branches.firstWhere(
      (b) => (b as Map<String, dynamic>)['branch_id'] == auth.user.branchId,
      orElse: () => branches.isNotEmpty ? branches.first as Map<String, dynamic> : {},
    );

    final bas = (myBranch['ba_summaries'] as List?) ?? [];

    return {
      'total_sales': myBranch['total_sales_count'] ?? 0,
      'total_commission': myBranch['total_commission_owed'] ?? 0,
      'performance': myBranch['performance_percentage'] ?? 0,
      'ba_count': bas.length,
    };
  } catch (e) {
    return {};
  }
});
```

### Add Refresh Functionality
```dart
// Add refresh button to Branch home screen
IconButton(
  icon: const Icon(Icons.refresh),
  onPressed: () => ref.invalidate(_branchSummaryProvider),
  tooltip: 'Refresh data',
)
```

### Add Loading State Improvements
```dart
// Better loading states
summaryAsync.when(
  loading: () => _LoadingSkeleton(),
  error: (e, _) => _ErrorCard(
    message: 'Failed to load data',
    onRetry: () => ref.invalidate(_branchSummaryProvider),
  ),
  data: (summary) => _BranchSummaryCards(summary: summary),
)
```

## Testing Strategy

1. **API Response Validation**
   - Test with actual backend data
   - Verify data accuracy
   - Test error handling

2. **Network Conditions**
   - Test with slow network
   - Test with network errors
   - Test offline behavior

3. **User Experience**
   - Test loading states
   - Test error recovery
   - Test refresh functionality

## Rollback Plan

If API-based approach has issues:
1. Keep local database approach but add data freshness indicators
2. Add "last synced" timestamp
3. Add manual sync button
4. Show warnings when data is stale

## Success Criteria

1. Summary metrics match backend data accurately
2. Loading states are clear and user-friendly
3. Error handling is robust with recovery options
4. Refresh functionality works reliably
5. Performance is acceptable (API calls don't feel slow)

## Timeline

- **Phase 1 (Immediate):** 30 minutes - Revert to API calls
- **Phase 2 (Today):** 1 hour - Standardize approach
- **Phase 3 (This Week):** 3-4 hours - Enhanced offline support

## Recommendation

**Start with Phase 1 immediately** - This is the quickest fix and aligns with the working HQ/BA implementations. The API-based approach is proven to work and provides accurate data.