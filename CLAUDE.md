# CLAUDE.md - Donnerstagsspieler Project Documentation

## Project Overview
Streamlit-based song matching application for "DJs unter sich" (dus) - tracks song history and connections from weekly DJ sessions.

## Critical Data Structure

### Excel File Structure (FLEXIBLE FORMAT)

The app supports **two formats** for Row 2:

**Format 1: Original (with prefix)**
```
Column A     | Column B          | Column C          | Column D
-------------|-------------------|-------------------|------------------
Row 1: None  | Ausgangssong 1    | Ausgangssong 2    | Ausgangssong 3
Row 2: "eingegeben von ⬇️" | "Ausgangssong von: Name1" | "Ausgangssong von: Name2" | ...
Row 3: DJ Name 1 | Matching Song 1.1 | Matching Song 2.1 | Matching Song 3.1
Row 4: DJ Name 2 | Matching Song 1.2 | Matching Song 2.2 | Matching Song 3.2
...
```

**Format 2: Clean (direct names) ✓ RECOMMENDED**
```
Column A     | Column B          | Column C          | Column D
-------------|-------------------|-------------------|------------------
Row 1: Name  | Ausgangssong 1    | Ausgangssong 2    | Ausgangssong 3
Row 2: Runden-Leiter | Name1      | Name2             | Name3
Row 3: DJ Name 1 | Matching Song 1.1 | Matching Song 2.1 | Matching Song 3.1
Row 4: DJ Name 2 | Matching Song 1.2 | Matching Song 2.2 | Matching Song 3.2
...
```

**Both formats work!** The code automatically detects and handles both.

**IMPORTANT CONTRIBUTOR MAPPING:**
- **Seed tracks (Row 1)**: Contributor is in Row 2 of the SAME COLUMN
- **Matching songs (Row 3+)**: Contributor is in Column A of the SAME ROW

**Common Mistake:** Mapping all contributors from Column A → This is WRONG for seed tracks!

## Design System

### Color Theme (Dark Premium)
```toml
Primary:     #8B5CF6  (Vibrant Purple - from dus branding)
Background:  #0F172A  (Deep Navy/Slate)
Secondary:   #1E293B  (Lighter Slate)
Text:        #E2E8F0  (Light Grey)
```

**Why Dark Theme:**
- Modern, professional look for music apps
- Easier on eyes during long sessions
- Matches industry standards (Spotify, SoundCloud)

### Responsive Breakpoints
- **Mobile**: ≤768px (stack layouts, smaller fonts)
- **Tablet**: 769px-1024px (medium sizing)
- **Desktop**: ≥1024px (full layout)

## Key Features & Implementation

### 1. Fuzzy Search (RapidFuzz)
- Uses `partial_ratio` and `token_sort_ratio`
- Default threshold: 70% (adjustable 50-100%)
- Handles typos, partial matches, case-insensitive

### 2. Song Connections
- Shows all songs in same cluster (column)
- Tracks which Runde/Woche they appear in
- Displays contributor for each song

### 3. Contributor View
- Click any DJ name to see all their songs
- Shows both Ausgangssongs (⭐) and regular songs (🎵)
- Lists which Runde/Woche for each

### 4. Autocomplete
- Shows top 5 suggestions after 2+ characters
- Clickable suggestions auto-fill search
- Updates in real-time

### 5. Song Normalization (Deduplication)
- Normalizes song names for comparison (preserves original for display)
- Handles: accents/diacritics (é→e), quotes/apostrophes, dashes, multiple spaces
- Groups spelling variants together (e.g., "Daft Punk - One More Time" = "Daft Punk – One More Time")
- Shows variant count badge when multiple spellings exist

### 6. Best Of Tab
- Shows top 50 songs by occurrence count
- Medal emojis for top 3 (🥇🥈🥉)
- Click to view song connections
- Shows variant count for deduplicated songs

### 7. Pagination
- Search results: 5 per page
- Connections: 10 per page
- Contributor songs: 15 per page
- Best Of: 15 per page
- Prev/Next navigation with page indicator

### 8. Feedback System
- Users can submit feedback via the **Feedback tab** (💬)
- Three feedback types: Bug 🐛, Feature 💡, Other 💬
- Optional contact field for follow-up
- Stored locally in `data/feedback.json`
- **Functions:**
  - `add_feedback(type, description, contact)` - saves new entry
  - `load_feedback()` - loads all feedback as list
  - `save_feedback(list)` - writes feedback to JSON

### 9. Admin Mode
- Access via URL parameter: `?admin=true`
- Shows 4th tab: **Admin** (🔐)
- Admin tab displays:
  - All submitted feedback entries
  - CSV export button
  - Entry details: type, description, contact, timestamp, theme
- **IMPORTANT:** Admin mode must be enabled via `st.query_params`, NOT hardcoded!
```python
# CORRECT - Enable via URL parameter
is_admin = st.query_params.get("admin", "false").lower() == "true"

# WRONG - Never hardcode this!
is_admin = False  # This disables admin permanently
```

## Common Mistakes & How to Avoid

### ❌ Mistake 1: Wrong Contributor Mapping
**What happened:** Initially mapped all contributors from Column A
**Why wrong:** Seed tracks have contributors in Row 2 (same column)
**Solution:** Dual mapping system implemented in `search_songs()` and `get_song_connections()`

### ❌ Mistake 2: Mock Data Structure Mismatch
**What happened:** Old mock file had different structure than real data
**Why wrong:** Tests passed but real data failed
**Solution:** Always regenerate mock data after structure changes

### ❌ Mistake 3: Desktop-Only Design
**What happened:** Initial design didn't consider mobile users
**Why wrong:** Many users access on smartphones
**Solution:** Mobile-first CSS with responsive breakpoints

### ❌ Mistake 4: Unclear Round Naming
**What happened:** Used worksheet names directly
**Why wrong:** Not informative enough
**Solution:** Format as "Runde X, Woche Y" where Y = column index

### ❌ Mistake 5: Autocomplete Session State Bug
**What happened:** Tried to modify `st.session_state.search_input` after the widget was created
**Error:** `StreamlitAPIException: st.session_state.search_input cannot be modified after the widget with key search_input is instantiated`
**Why wrong:** Streamlit doesn't allow modifying a widget's session state after instantiation in the same run
**Solution:** Use separate session state variable `selected_suggestion`:
```python
# Initialize
if 'selected_suggestion' not in st.session_state:
    st.session_state.selected_suggestion = None

# Create text input with suggestion value
default_value = st.session_state.selected_suggestion if st.session_state.selected_suggestion else ""
search_query = st.text_input("🔍 Song finden:", value=default_value, key="search_input")

# Clear after use
if st.session_state.selected_suggestion:
    st.session_state.selected_suggestion = None

# Button sets the separate variable
if st.button(suggestion, key=f"suggest_{suggestion}"):
    st.session_state.selected_suggestion = suggestion
    st.rerun()
```

### ❌ Mistake 6: Assuming Single Data Format
**What happened:** Validation script expected exact "Ausgangssong von: Name" format
**Why wrong:** User's real data had cleaner format with direct names in Row 2
**Solution:** Code already flexible with if/else clause:
```python
if "Ausgangssong von" in text:
    seed_contributor = text.replace("Ausgangssong von:", "").strip()
else:
    seed_contributor = text.strip()  # Handles direct names
```
**Learning:** Always design for format flexibility, don't force users to change their data

### ❌ Mistake 7: XSS Vulnerability in HTML Rendering
**What happened:** Song names were interpolated directly into `unsafe_allow_html=True` markdown
**Why wrong:** Malicious song names like `<script>alert('XSS')</script>` could execute
**Solution:** Escape all user data with `html.escape()` before rendering:
```python
import html
escaped_song = html.escape(song)
st.markdown(f"**{escaped_song}** <span>...</span>", unsafe_allow_html=True)
```

### ❌ Mistake 8: Unhandled File Write Errors
**What happened:** `save_likes()` had no try-except block
**Why wrong:** Read-only file or disk full would crash app with stack trace
**Solution:** Wrap file operations with error handling:
```python
def save_likes(likes):
    try:
        with open(LIKES_FILE, 'w', encoding='utf-8') as f:
            json.dump(likes, f, ensure_ascii=False, indent=2)
    except (IOError, OSError) as e:
        st.warning(f"Likes konnten nicht gespeichert werden: {e}")
```

### ❌ Mistake 9: Widget Keys with Special Characters
**What happened:** Song names used directly as widget keys (`key=f"suggest_{song}"`)
**Why wrong:** Special characters (quotes, newlines) cause Streamlit key collisions
**Solution:** Use index-based keys instead:
```python
for idx, suggestion in enumerate(suggestions):
    st.button(suggestion, key=f"suggest_{idx}")  # NOT key=f"suggest_{suggestion}"
```

### ❌ Mistake 10: Double-Click Adds Multiple Likes
**What happened:** No debounce on like buttons
**Why wrong:** Rapid clicks trigger multiple `st.rerun()` cycles, adding multiple likes
**Solution:** Session state debounce with 500ms cooldown:
```python
def add_like(song_name):
    import time
    debounce_key = f"last_like_{hash(song_name) % 10000}"
    if debounce_key in st.session_state:
        if time.time() - st.session_state[debounce_key] < 0.5:
            return  # Skip if <500ms since last like
    st.session_state[debounce_key] = time.time()
    # ... proceed with like
```

### ❌ Mistake 11: Treating Song Variants as Separate Songs
**What happened:** "Daft Punk – One More Time" and "Daft Punk - One More Time" counted separately
**Why wrong:** Same song appears multiple times in Best Of, inflates song counts incorrectly
**Solution:** Normalize song names for comparison while preserving originals for display:
```python
def normalize_song_name(song):
    # Remove accents, standardize quotes/dashes, lowercase
    normalized = unicodedata.normalize('NFD', song.lower())
    normalized = re.sub(r'[–—−]', '-', normalized)  # All dashes to hyphen
    # ... more normalization
    return normalized

# Index structure tracks variants:
song_index[normalized] = {
    'variants': ['Original 1', 'Original 2'],  # Keep all spellings
    'clusters': [...],
    'count': total_occurrences
}
```
**Learning:** Always normalize for comparison, display original for users

### ❌ Mistake 12: Missing Supabase Secrets in Cloud
**What happened:** App deployed but shows "Database not available" error
**Why wrong:** Forgot to add secrets in Streamlit Cloud dashboard
**Solution:** Always verify secrets are configured:
```toml
# In Streamlit Cloud → App Settings → Secrets
[supabase]
url = "https://xxx.supabase.co"
anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

USE_DATABASE = "true"
```
**Verification:** Check `is_database_available()` returns True after deployment

### ❌ Mistake 13: Using SERVICE_KEY in Cloud Secrets
**What happened:** Put `SUPABASE_SERVICE_KEY` in Streamlit Cloud secrets
**Why wrong:** Service key has admin privileges, should never be exposed in client-side app
**Solution:**
- Cloud: Use only `anon_key` (read + RLS-protected writes)
- Local push script: Use `SERVICE_KEY` in `.env` (never committed)
```bash
# .env (local only, in .gitignore)
SUPABASE_SERVICE_KEY=eyJ...  # Only for push_to_supabase.py
```

### ❌ Mistake 14: Forgetting to Run schema.sql Before Push
**What happened:** `push_to_supabase.py` fails with "relation does not exist"
**Why wrong:** Tables and functions don't exist in new Supabase project
**Solution:** Always run schema.sql in Supabase SQL Editor before first data push:
1. Go to Supabase Dashboard → SQL Editor
2. Paste contents of `schema.sql`
3. Click "Run" → Verify "Success" message
4. Then run `python push_to_supabase.py`

### ❌ Mistake 15: Cloud Caching Stale Database Data
**What happened:** Data pushed to Supabase but app shows old data
**Why wrong:** `@st.cache_data(ttl=300)` caches for 5 minutes
**Solution:** Either wait 5 minutes or manually clear cache:
```python
# In db.py - clear_cache() function
load_all_data_from_db.clear()
get_all_songs_from_db.clear()
get_all_contributors_from_db.clear()
get_top_songs_db.clear()
```
**Note:** For immediate updates during testing, reduce TTL or add a cache-clear button

### ❌ Mistake 16: Hardcoded Admin Mode
**What happened:** `is_admin = False` was hardcoded, disabling admin tab permanently
**Why wrong:** Admin tab (which shows user feedback) was never visible, even with `?admin=true`
**Solution:** Enable admin via URL parameter, never hardcode:
```python
# CORRECT
is_admin = st.query_params.get("admin", "false").lower() == "true"

# WRONG - This disables admin forever!
is_admin = False
```
**Learning:** Feature flags should be configurable, not hardcoded. Use URL params or environment variables.

### ❌ Mistake 17: Tab Content Outside Tab Block
**What happened:** Content after `with tab_search:` was at wrong indentation level
**Why wrong:** Search content rendered outside tabs, breaking tab navigation
**Solution:** Ensure ALL tab content is properly indented inside `with tab_X:` block:
```python
# CORRECT
with tab_search:
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input(...)  # Inside tab_search
    # ... all search content indented here

# WRONG - col1 content is OUTSIDE tab_search!
with tab_search:
    col1, col2 = st.columns([3, 1])
with col1:  # <-- Same indentation as tab_search = OUTSIDE!
    search_query = st.text_input(...)
```
**Learning:** Always verify indentation when working with Streamlit tabs/columns.

## Song Normalization Logic (Sprint 5)

### Why Normalization?
DJs enter song names inconsistently:
- "Daft Punk - One More Time" vs "Daft Punk – One More Time" (en-dash vs hyphen)
- "Beyoncé" vs "Beyonce" (accents)
- "Rock'n'Roll" vs "Rock'n'Roll" (curly vs straight quotes)

Without normalization, these appear as separate songs in statistics.

### Normalization Rules
```python
def normalize_song_name(song: str) -> str:
    # 1. Lowercase
    # 2. Remove accents (NFD + strip combining marks)
    # 3. Standardize quotes: '' ´ ` → '
    # 4. Standardize double quotes: "" „ → "
    # 5. Standardize dashes: – — − → -
    # 6. Collapse multiple spaces
    # 7. Normalize "artist - song" spacing
    # 8. Strip whitespace
```

### Index Structure
```python
song_index = {
    "normalized_name": {
        "variants": ["Original 1", "Original 2", ...],  # All spelling variants
        "clusters": [...],  # Where these songs appear
        "count": 5  # Total occurrences across all variants
    }
}
```

### Example
```
Input variants:
  - "Daft Punk – One More Time"
  - "Daft Punk - One More Time"
  - "daft punk - one more time"

Normalized key: "daft punk - one more time"
Displayed as: First variant encountered
Variant badge: "3 Varianten" (with tooltip)
```

## Streamlit Debugging Patterns

### Widget Session State Rules
1. **NEVER modify a widget's session state after the widget is created in the same run**
   - BAD: `st.session_state.search_input = "new value"` after `st.text_input(..., key="search_input")`
   - GOOD: Use separate variable, set value on creation, clear after use

2. **Pattern for pre-filling widgets:**
   ```python
   # Step 1: Store value in separate session state variable
   st.session_state.my_temp_value = "something"

   # Step 2: Use it to initialize widget
   value = st.session_state.my_temp_value or ""
   widget = st.text_input("Label", value=value, key="my_widget")

   # Step 3: Clear temp variable after use
   if st.session_state.my_temp_value:
       st.session_state.my_temp_value = None
   ```

3. **Common errors and fixes:**
   - `StreamlitAPIException: cannot be modified after widget is instantiated`
     - Fix: Use separate temp variable pattern above
   - Widget value not updating when session state changes
     - Fix: Use `value=` parameter, not session state assignment

### Performance Debugging
- Use `python benchmark.py` to test performance with real data
- Check Streamlit warnings about missing caching
- Monitor cache hit rates with `st.cache_data` decorators

## File Structure
```
donnerstagsspiel/
├── data/
│   ├── song_matcher_mock.xlsx     # Mock data for testing
│   ├── donnerstagsspiel-data.xlsx # Real production data
│   ├── likes.json                 # User likes storage (local only)
│   └── feedback.json              # User feedback storage (local only)
├── .streamlit/
│   ├── config.toml                # Theme configuration
│   └── secrets.toml.example       # Template for cloud secrets
├── .claude/
│   └── settings.local.json        # Claude Code settings
├── main.py                        # Main application (dual-mode)
├── db.py                          # Database functions (Supabase REST API)
├── schema.sql                     # PostgreSQL schema for Supabase
├── push_to_supabase.py            # Script to push Excel data to cloud
├── create_mock_data.py            # Mock data generator
├── benchmark.py                   # Performance testing
├── validate_excel.py              # Excel structure validation
├── validate_data.py               # Data validation utility
├── find_duplicates.py             # Duplicate song finder
├── requirements.txt               # Dependencies
├── runtime.txt                    # Python version for Streamlit Cloud
├── .env.example                   # Template for local environment vars
├── .gitignore                     # Git exclusions
├── README.md                      # User documentation
├── USER_GUIDE.md                  # Tester guide (German)
├── CLAUDE.md                      # This file (dev documentation)
└── IMPLEMENTATION_PLAN.md         # Historical implementation plan
```

## Database Architecture (Cloud Mode)

### Tables (schema.sql)
```sql
runden      → Round/worksheet metadata (name, display_name)
clusters    → Seed track groups (runde_id, column_index, seed_track, seed_contributor)
songs       → Individual songs (cluster_id, song_name, contributor, row_index)
likes       → Song likes counter (song_name, like_count)
```

### Views & Functions
- `song_search_view` - Materialized view joining all tables for fast queries
- `search_songs(query, threshold, max_results)` - pg_trgm fuzzy search
- `get_song_clusters(song_name)` - Find all clusters containing a song
- `get_top_songs(max_results)` - Top songs by normalized occurrence count
- `increment_like(song_name)` - Add/increment like count
- `get_all_likes()` - Return all likes as dict

### Key Database Functions (db.py)
```python
# Configuration
get_supabase_credentials()  # From st.secrets or os.environ
supabase_request(method, endpoint, data, params)  # REST API wrapper
is_database_available()  # Test connection

# Data Loading
load_all_data_from_db()  # All songs from song_search_view
get_all_songs_from_db()  # Unique song names for autocomplete
get_all_contributors_from_db()  # Unique contributors

# Search & Connections
search_songs_db(query, fuzzy_threshold)  # Uses pg_trgm
get_song_connections_db(song_name)  # Find clusters for a song
get_cluster_songs(cluster_id)  # All songs in a cluster

# Likes
get_likes_db()  # All likes as {song: count}
add_like_db(song_name)  # Increment like counter

# Statistics
get_top_songs_db(limit)  # Top songs by occurrence
get_contributor_songs_db(name)  # Songs by contributor
```

### Caching Strategy
All database read functions use `@st.cache_data(ttl=300)` (5 minute cache).
Use `clear_cache()` to force refresh after data updates.

## Key Functions

### `normalize_song_name(song)` [NEW]
- **Purpose:** Normalize song names for comparison (not display)
- **Handles:** Lowercase, accents/diacritics, quotes, apostrophes, dashes, spaces
- **Returns:** Normalized string for matching
- **Example:** `"Daft Punk – One More Time"` → `"daft punk - one more time"`

### `build_song_index(worksheets)` [UPDATED - CACHED]
- **Purpose:** Pre-build optimized index with normalization support
- **Returns:** Dict mapping normalized_name -> {variants: list, clusters: list, count: int}
- **Cached:** Yes (@st.cache_data) - built once, reused
- **Performance:** ~0.025s for 36 songs, ~1.2s for 8,956 songs

### `search_songs(query, song_index, fuzzy_threshold)` [OPTIMIZED]
- **Purpose:** Find all songs matching the query using process.extract()
- **Parameters:** song_index (from build_song_index), NOT worksheets
- **Returns:** List of dicts with matched songs, contributors, scores
- **Performance:** O(n log n) instead of O(n·m·k) - 85% faster

### `get_song_connections(song_name, song_index)` [OPTIMIZED]
- **Purpose:** Find all clusters containing a specific song
- **Parameters:** song_index (from build_song_index), NOT worksheets
- **Returns:** List of dicts with all songs in each cluster
- **Performance:** O(1) lookup instead of O(n²) - 90% faster

### `get_all_songs(worksheets)` & `get_all_contributors(worksheets)` [CACHED]
- **Purpose:** Extract unique songs/contributors for autocomplete
- **Returns:** Sorted lists
- **Cached:** Yes (@st.cache_data) - no repeated computation
- **Performance:** Instant on subsequent calls (cached)

### `get_top_songs(song_index, limit)` [NEW]
- **Purpose:** Return top songs sorted by occurrence count
- **Parameters:** song_index (pre-built), limit (default 50)
- **Returns:** List of dicts with name, normalized, count, variants
- **Used by:** Best Of tab

### `render_pagination(items, page_key, items_per_page)` [NEW]
- **Purpose:** Calculate pagination state and return paginated items
- **Returns:** Tuple (paginated_items, current_page, total_pages, start_num, end_num, total_items)
- **Used by:** All paginated views

### `render_pagination_controls(page_key, current_page, total_pages)` [NEW]
- **Purpose:** Render Prev/Next navigation buttons
- **Behavior:** Only shows if more than one page exists

## Session State Variables
```python
# Navigation state
st.session_state.selected_contributor  # Currently filtered DJ
st.session_state.selected_song         # Currently viewed song connections
st.session_state.search_input          # Search box value (managed by widget)
st.session_state.selected_suggestion   # Temporary variable for autocomplete selection
st.session_state.navigation_history    # Stack for breadcrumb trail
st.session_state.last_search_query     # Preserved search when drilling

# Pagination state
st.session_state.page_search           # Current page in search results
st.session_state.page_connections      # Current page in connections view
st.session_state.page_contributor      # Current page in contributor view
st.session_state.page_bestof           # Current page in Best Of tab

# Pagination context tracking (for reset on context change)
st.session_state.prev_search_query        # Detect search context changes
st.session_state.prev_selected_song       # Detect song context changes
st.session_state.prev_selected_contributor # Detect contributor context changes

# Feedback state
st.session_state.feedback_submitted       # True after successful feedback submission
```

**IMPORTANT:** Never modify `search_input` directly - it's managed by the text_input widget. Use `selected_suggestion` to pre-fill the search box on rerun.

## UI/UX Patterns

### Match Score Badges
```python
100%:    Green (#00CC00)   ✓  Perfect match
85-99%:  Light Green       ~  Very good
70-84%:  Orange (#FFB800)  ~  Good
<70%:    Red (#FF6B6B)     ?  Weak (usually filtered)
```

### Icons & Meaning
- 🎯 Search results/matches
- ⭐ Ausgangssong (seed track)
- 🎵 Regular matched song
- 👤 Contributor/DJ
- 🔗 Song connections
- 📍 Location (Runde/Woche)
- 🏠 Home/Search (breadcrumbs)
- 🏆 Best Of / Rankings
- 🥇🥈🥉 Top 3 ranking medals
- ❤️ Liked song
- 🤍 Not liked (click to like)
- 📥 Export/Download
- 🔍 Search tab
- ← Zurück / ← Zur Suche (back navigation)

### UI Structure
```
Main Screen (no selection):
├── Tab: 🔍 Suche
│   ├── Search input + threshold slider
│   ├── Autocomplete suggestions
│   └── Paginated search results (5/page)
└── Tab: 🏆 Best Of
    └── Top 50 songs by occurrence (15/page)

Song Connections Screen (selected_song):
├── Back button + Breadcrumbs
├── Song title
└── Paginated clusters (10/page)
    └── Each cluster shows all connected songs

Contributor Screen (selected_contributor):
├── Back button + Breadcrumbs
├── Contributor name
└── Paginated songs by this DJ (15/page)
```

## Performance Optimizations (Sprint 1 - COMPLETED)

### Architecture Changes (Feb 2026)
**Problem:** Original implementation had O(n·m·k) complexity - would take 4-7s for 1000+ songs

**Solution:** Three-tier optimization strategy achieving ~85% performance improvement

### Optimization 1: Caching Data Functions ✓
```python
@st.cache_data
def get_all_songs(worksheets): ...

@st.cache_data
def get_all_contributors(worksheets): ...
```
- **Impact:** Eliminates repeated computation on every rerun
- **Improvement:** 0.5-1s saved per page interaction

### Optimization 2: Song Index with process.extract() ✓
```python
@st.cache_data
def build_song_index(worksheets):
    """Pre-build index: song -> [cluster_info, ...]"""
    # Returns dict mapping each song to its cluster locations
    ...

def search_songs(query, song_index, fuzzy_threshold):
    # Use RapidFuzz process.extract() for O(n log n) search
    candidate_matches = process.extract(query, all_song_names, ...)
    ...
```
- **Before:** O(n·m·k) - triple nested loops through all songs
- **After:** O(n log n) - single pass with process.extract()
- **Impact:** 4-7s → 0.5-1s for 1000 songs (85% improvement)

### Optimization 3: O(1) Connection Lookup ✓
```python
def get_song_connections(song_name, song_index):
    # Direct dictionary lookup instead of iteration
    return song_index.get(song_name, [])
```
- **Before:** O(n²) - iterate through all worksheets/columns
- **After:** O(1) - direct dictionary lookup
- **Impact:** 1-6s → 0.05-0.5s (90% improvement)

### Performance Benchmarks
**Mock Data (36 songs):**
- Index build: 0.025s (one-time, cached)
- Search: <0.001s (target: <1s) ✓
- Connection lookup: <0.001s (target: <0.5s) ✓

**Real Data (8,956 songs, 7,706 unique):**
- Data loading: 2.465s (one-time)
- Index build: 1.211s (one-time, cached) ✓
- Search: 0.038s average (target: <1s) - **26x faster than target!** ✓
- Connection lookup: <0.001s (target: <0.5s) - **Perfect!** ✓
- Dataset: 8 Runden (worksheets), ~20 Wochen per Runde

**Performance Comparison:**
- Original unoptimized: Would be 4-7s for 8,956 songs
- Optimized version: 0.038s (99.5% faster!)
- Scales beautifully beyond expected 2000 songs

### Remaining Optimizations (Future)
- [x] Add pagination (5-15 results per page) - ✓ Implemented in Sprint 5
- [ ] Pre-compile contributor lookup dictionary
- [ ] Add database backend if >10,000 songs

## Deployment Notes

### Data Modes
The app supports two modes controlled by `USE_DATABASE` environment variable:

| Mode | When | Data Source | Likes Storage |
|------|------|-------------|---------------|
| **Excel** (default) | Local dev | `data/*.xlsx` | `data/likes.json` |
| **Database** | Cloud deployment | Supabase PostgreSQL | Supabase `likes` table |

**Auto-detection:** In Streamlit Cloud, database mode is forced automatically (Excel files aren't deployed).

### Local Development
```bash
streamlit run main.py
# Runs on http://localhost:8501 in Excel mode
```

### Cloud Deployment (Streamlit Cloud + Supabase)

**Files required for deployment:**
- `runtime.txt` - Python version (3.11.0)
- `.streamlit/secrets.toml.example` - Template for cloud secrets
- `schema.sql` - Database schema for Supabase
- `push_to_supabase.py` - Script to push Excel data to cloud

**Deployment sequence:**
1. Create Supabase project → Run `schema.sql` in SQL Editor
2. Set up `.env` locally with `SUPABASE_SERVICE_KEY`
3. Run `python push_to_supabase.py --migrate-likes`
4. Push code to GitHub
5. Deploy on Streamlit Cloud
6. Add secrets in Streamlit Cloud dashboard:
   ```toml
   [supabase]
   url = "https://xxx.supabase.co"
   anon_key = "eyJ..."
   USE_DATABASE = "true"
   ```

### Environment Variables
| Variable | Local (.env) | Cloud (secrets.toml) | Purpose |
|----------|--------------|----------------------|---------|
| `SUPABASE_URL` | Required for DB mode | Required | Project URL |
| `SUPABASE_ANON_KEY` | Required for DB mode | Required | Public API key (read) |
| `SUPABASE_SERVICE_KEY` | Required for push script | NOT NEEDED | Admin key (write) |
| `USE_DATABASE` | `false` (default) | `true` | Enable database mode |

## Future Feature Ideas (Not Implemented)
- [ ] Spotify integration (search links)
- [ ] Network graph visualization of song connections
- [x] Export to playlist (CSV) - ✓ Implemented in Sprint 4
- [x] Statistics dashboard (most popular songs) - ✓ Best Of tab in Sprint 5
- [ ] Admin panel to edit data directly
- [ ] Song recommendations based on history
- [ ] Most active contributors leaderboard

## Testing Checklist

Before major changes:
1. ✅ Test with mock data (create_mock_data.py)
2. ✅ Test with real data (if available)
3. ✅ Test on mobile (browser DevTools)
4. ✅ Test search edge cases (empty, special chars, very long)
5. ✅ Test all clickable elements (contributors, songs, links)
6. ✅ Verify contributor mapping (seed vs. regular)
7. ✅ Check responsive design (mobile/tablet/desktop)

## Dependencies & Versions
```
streamlit >= 1.28.0    # Web framework
pandas >= 2.0.0        # Data manipulation
openpyxl >= 3.1.0      # Excel file handling
rapidfuzz >= 3.0.0     # Fuzzy string matching
supabase >= 2.0.0      # Cloud database client
python-dotenv >= 1.0.0 # Environment variable loading
```

**Why these versions:**
- Streamlit 1.28+: Session state improvements, native Supabase support
- Pandas 2.0+: Better performance
- RapidFuzz: Much faster than fuzzywuzzy
- Supabase 2.0+: Stable Python client for PostgreSQL
- python-dotenv: Load `.env` files for local development

## Git Workflow (if using git)
```bash
# Never commit these:
data/*.xlsx (except mock)
.streamlit/secrets.toml
__pycache__/
*.pyc
```

## Contact & Support
- Project: Donnerstagsspieler (DJs unter sich)
- Framework: Streamlit + Python
- Primary use case: Song history search and connections
- Target users: DJs in the "dus" community

## Security Hardening (Sprint 3 - COMPLETED)

### Fixes Applied (Feb 2026)

| Issue | Severity | Fix |
|-------|----------|-----|
| XSS via song names | CRITICAL | `html.escape()` on all user data in `unsafe_allow_html` |
| save_likes crash | HIGH | try-except with German error message |
| Widget key collision | MEDIUM | Index-based keys (`suggest_{idx}`) |
| Input length DoS | MEDIUM | `max_chars=200` on search input |
| Double-click likes | LOW | 500ms session state debounce |
| No loading feedback | UX | `st.spinner()` during data load |

### Security Checklist
- [x] HTML escape user data in `unsafe_allow_html` sections
- [x] Error handling on file writes
- [x] Input length validation
- [x] Widget key sanitization
- [x] Button debouncing
- [x] Loading state indicators
- [ ] Rate limiting (not needed for single-user)
- [ ] File locking for concurrent writes (future if multi-user)

## DJ Workflow Features (Sprint 4 - COMPLETED)

### Navigation Improvements

**Breadcrumb Navigation** - Enables infinite drilling into song connections:
```python
# Session state for navigation history
st.session_state.navigation_history = []  # Stack of {'type': 'song'|'contributor', 'value': name}

# Helper functions
navigate_to_song(song_name)      # Push current state, navigate to song
navigate_to_contributor(name)    # Push current state, navigate to contributor
navigate_back()                  # Pop from history, restore previous view
render_breadcrumbs()             # Show clickable breadcrumb trail
```

**Preserved Search Context** - Query persists when navigating:
```python
st.session_state.last_search_query = ""  # Saved when clicking 🔗 or 👤
# Restored via selected_suggestion when navigating back to search
```

**Drill-Down Buttons** - Each song in connections view has a 🔗 button to see ITS connections.

### CSV Export for DJs
```python
export_likes_to_csv(likes_dict)  # Generates CSV: "Song,Likes" format
st.download_button(...)          # Download button appears when likes exist
```
- Exports all liked songs with like counts
- Sorted by popularity (most liked first)
- CSV format for easy import to DJ software

### New Session State Variables
```python
st.session_state.navigation_history    # Stack for breadcrumb trail
st.session_state.last_search_query     # Preserved search when drilling
```

---

**Last Updated:** 2026-02-04
**Version:** 5.0 (Feedback System & Admin Mode)
**Status:** Production-ready, deployed on Streamlit Cloud with Supabase backend

## Sprint History
- **Sprint 1 (COMPLETED):** Performance optimizations (85% improvement)
- **Sprint 2 (COMPLETED):** Real data integration (8 Runden, 8,956 songs)
  - Validated data format compatibility
  - Fixed autocomplete session state bug
  - Verified performance at scale (0.038s search time)
  - Confirmed format flexibility (both "Ausgangssong von:" and direct names work)
- **Sprint 3 (COMPLETED):** Security hardening & QA audit
  - Fixed XSS vulnerability in HTML rendering
  - Added error handling to file operations
  - Input validation (max 200 chars)
  - Button debouncing (500ms)
  - Loading spinner during data load
  - Widget key sanitization
- **Sprint 4 (COMPLETED):** DJ workflow improvements
  - Breadcrumb navigation for infinite drilling
  - Preserved search context when navigating back
  - CSV export for liked songs (playlist generation)
  - Drill-down buttons on connections screen
- **Sprint 5 (COMPLETED):** Song normalization & Best Of
  - `normalize_song_name()` for deduplication (accents, quotes, dashes, spaces)
  - Variant tracking - groups same songs with different spellings
  - Variant badge display ("X Varianten" with tooltip showing all spellings)
  - Best Of tab with top 50 songs by occurrence count
  - Medal emojis for top 3 rankings (🥇🥈🥉)
  - Tabbed interface (Search / Best Of)
  - Pagination system for all views (5/10/15 items per page)
  - Updated `build_song_index()` to track normalized names and variants
- **Sprint 6 (COMPLETED):** Cloud Deployment MVP
  - Dual-mode architecture: Excel (local) ↔ Supabase (cloud)
  - `db.py` - Database functions using Supabase REST API
  - `schema.sql` - PostgreSQL schema with pg_trgm fuzzy search
  - `push_to_supabase.py` - CLI tool to migrate Excel data to cloud
  - Auto-detection of Streamlit Cloud environment
  - Feature flag system (`USE_DATABASE`, `STREAMLIT_CLOUD`)
  - Database functions: search, connections, likes, contributors, top songs
  - `runtime.txt` for Python version specification
  - `USER_GUIDE.md` - German user guide for testers
  - Updated README with cloud deployment instructions
  - Secrets configuration via `st.secrets` for cloud deployment
- **Sprint 7 (COMPLETED):** Feedback System & Admin Mode
  - Feedback tab (💬) for users to submit bugs and feature requests
  - Three feedback types: Bug, Feature, Other
  - Feedback storage in `data/feedback.json`
  - Admin mode via URL parameter `?admin=true`
  - Admin tab (🔐) shows all feedback with CSV export
  - Fixed tab indentation bug (content was outside tab block)
  - Fixed hardcoded `is_admin = False` that disabled admin permanently
