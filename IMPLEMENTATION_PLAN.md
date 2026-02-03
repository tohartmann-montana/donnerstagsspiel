# Implementation Plan: Real Data Integration with Performance Optimization

## Overview
Migrate the Donnerstagsspieler app from mock data to real Excel data (500-2000 songs, 10-30 Runden) with critical performance optimizations to ensure sub-second response times.

## Current Performance Analysis
- **search_songs()**: O(n·m·k) complexity → 4-7s for 1000 songs (CRITICAL)
- **get_song_connections()**: O(n²) complexity → 1-6s (HIGH)
- **get_all_songs/contributors()**: No caching → repeated computation on every rerun (HIGH)
- **UI rendering**: No pagination → renders all results (MEDIUM)

## Target Performance
- Search: <1s for 2000 songs
- Song connections: <0.5s
- Initial load: <2s
- Overall improvement: ~85%

---

## Phase 1: High-Priority Optimizations (85% improvement)

### 1.1 Add Caching to Data Loading Functions
**File**: [main.py](main.py)
**Lines**: ~118-160 (get_all_songs, get_all_contributors)

**Changes**:
```python
@st.cache_data
def get_all_songs(worksheets):
    # Existing implementation

@st.cache_data
def get_all_contributors(worksheets):
    # Existing implementation
```

**Impact**: Eliminates repeated computation on every rerun
**Expected**: 0.5-1s improvement on page interactions

---

### 1.2 Optimize search_songs() with RapidFuzz process.extract()
**File**: [main.py](main.py)
**Lines**: ~214-314

**Current Problem**: Triple nested loops iterating through all songs
**Solution**: Use process.extract() to get top matches in single pass

**Implementation**:
1. Build song index with metadata (sheet_name, col_idx, row_idx, contributor)
2. Use `process.extract(query, song_list, scorer=fuzz.token_sort_ratio, limit=100)`
3. Filter by threshold and format results

**Impact**: Reduces from O(n·m·k) to O(n log n)
**Expected**: 4-7s → 0.5-1s for 1000 songs

---

### 1.3 Optimize get_song_connections() with Pre-built Index
**File**: [main.py](main.py)
**Lines**: ~160-212

**Current Problem**: Iterates through all worksheets/columns for each lookup
**Solution**: Build song-to-cluster mapping dictionary once at load time

**Implementation**:
```python
@st.cache_data
def build_song_cluster_index(worksheets):
    """Build dictionary mapping song → list of cluster metadata"""
    song_clusters = defaultdict(list)
    for sheet_name, df in worksheets.items():
        for col_idx in range(1, len(df.columns)):
            # Store cluster metadata for all songs in column
            cluster_info = {
                'sheet_name': sheet_name,
                'col_idx': col_idx,
                'seed_track': ...,
                'all_songs': [...],
                'contributors': {...}
            }
            for song in all_songs_in_column:
                song_clusters[song].append(cluster_info)
    return dict(song_clusters)

def get_song_connections(song_name, song_cluster_index):
    """O(1) lookup instead of O(n²) search"""
    return song_cluster_index.get(song_name, [])
```

**Impact**: Reduces from O(n²) to O(1) lookup
**Expected**: 1-6s → 0.05-0.5s

---

## Phase 2: Medium-Priority Optimizations

### 2.1 Add Pagination to Search Results
**File**: [main.py](main.py)
**Location**: After search results generation (~440-470)

**Implementation**:
- Add `st.session_state.page_number` and `st.session_state.results_per_page = 20`
- Show only current page of results
- Add "Previous" / "Next" buttons
- Display "Showing 1-20 of 234 results"

**Impact**: Faster UI rendering with many results
**Expected**: Improves perceived performance for 100+ results

---

### 2.2 Pre-compile Contributor Lookup Dictionary
**File**: [main.py](main.py)

**Implementation**:
```python
@st.cache_data
def build_contributor_lookup(worksheets):
    """Pre-build mapping of (sheet, col, row) → contributor"""
    contributor_map = {}
    for sheet_name, df in worksheets.items():
        for col_idx in range(1, len(df.columns)):
            # Map seed track
            contributor_map[(sheet_name, col_idx, 0)] = extract_contributor_from_row2(...)
            # Map matching songs
            for row_idx in range(2, len(df)):
                contributor_map[(sheet_name, col_idx, row_idx)] = df.iloc[row_idx, 0]
    return contributor_map
```

**Impact**: Eliminates repeated string parsing
**Expected**: Minor improvement (0.1-0.2s)

---

## Phase 3: Real Data Integration

### 3.1 Data Validation Script
**New File**: [validate_excel.py](validate_excel.py)

**Purpose**: Validate real Excel file structure before import

**Checks**:
- Sheet naming format (e.g., "Runde 4")
- Row 1: Ausgangssongs (string values)
- Row 2: "Ausgangssong von: Name" format
- Row 3+: Matching songs with contributors in Column A
- No duplicate Ausgangssongs within same sheet
- Contributor names are consistent

**Usage**: `python validate_excel.py path/to/real_data.xlsx`

---

### 3.2 Update Excel Path in main.py
**File**: [main.py](main.py)
**Line**: ~416 (excel_path assignment)

**Change**:
```python
# Option 1: Direct path
excel_path = "real_data.xlsx"

# Option 2: File uploader (for flexibility)
uploaded_file = st.file_uploader("Excel-Datei hochladen", type=['xlsx'])
if uploaded_file:
    excel_path = uploaded_file
else:
    st.stop()
```

---

### 3.3 Performance Benchmarking
**New File**: [benchmark.py](benchmark.py)

**Purpose**: Measure performance before/after optimizations

**Metrics**:
- Data loading time
- Search time for various query types
- Song connections lookup time
- Memory usage
- Cache effectiveness

**Usage**: `python benchmark.py`

---

## Phase 4: Testing & Validation

### 4.1 Functional Testing Checklist
- [ ] Autocomplete shows relevant suggestions (2+ chars)
- [ ] Fuzzy search works with typos (threshold 70%+)
- [ ] Match score badges color-coded correctly
- [ ] Contributor filtering works (clickable DJ names)
- [ ] Song connections (🔗) shows all related songs
- [ ] Mobile responsive design works on smartphone
- [ ] Dark theme renders correctly
- [ ] Logo displays properly

### 4.2 Performance Testing
- [ ] Search <1s with 500 songs
- [ ] Search <1s with 1000 songs
- [ ] Search <1s with 2000 songs
- [ ] Song connections <0.5s
- [ ] Page load <2s
- [ ] No lag on contributor filtering
- [ ] Pagination works smoothly

### 4.3 Data Integrity Testing
- [ ] All Ausgangssongs imported correctly
- [ ] Contributor mapping accurate (dual mapping system)
- [ ] Round/week numbering correct
- [ ] No duplicate songs in results
- [ ] All sheets processed

---

## Implementation Order

### Sprint 1: Core Performance (Priority: CRITICAL)
1. Add @st.cache_data to get_all_songs() and get_all_contributors()
2. Optimize search_songs() with process.extract()
3. Build song cluster index and optimize get_song_connections()
4. Test with mock data to verify performance improvements

**Estimated Impact**: 85% performance improvement

### Sprint 2: Real Data (Priority: HIGH)
1. Create validate_excel.py script
2. Validate real Excel file
3. Update excel_path in main.py
4. Run functional tests

### Sprint 3: Polish (Priority: MEDIUM)
1. Add pagination to search results
2. Pre-compile contributor lookup
3. Create benchmark.py for ongoing monitoring
4. Final performance testing with real data

---

## Rollback Plan
If performance issues persist with 2000 songs:
1. **Option A**: Implement database backend (SQLite) with indexes
2. **Option B**: Add server-side caching (Redis)
3. **Option C**: Lazy loading (only load visible sheets)

---

## Success Criteria
✅ Search responds in <1s for 2000 songs
✅ Song connections load in <0.5s
✅ All functional features work with real data
✅ Mobile optimization maintained
✅ No regression in UX/UI quality

---

## Files to Modify
1. [main.py](main.py) - All optimization changes
2. [validate_excel.py](validate_excel.py) - NEW FILE
3. [benchmark.py](benchmark.py) - NEW FILE
4. [CLAUDE.md](CLAUDE.md) - Update with optimization notes

## Files to Create
- validate_excel.py
- benchmark.py

## Estimated Timeline
- Sprint 1 (Core Performance): Implementation focused
- Sprint 2 (Real Data): Testing focused
- Sprint 3 (Polish): Enhancement focused
