# Donnerstagsspieler

A Streamlit-based web app to search for songs and discover matching tracks from your curated playlists.

## How It Works

- **Seed Tracks** (pink cells in row 1): The initial/reference track for each cluster
- **Columns**: Each column represents a group of songs that match the seed track
- **Search**: Enter any song name, and the app shows the seed track first, followed by all related songs

## Setup

### 1. Install Python

Make sure Python 3.8+ is installed. Check with:
```bash
python --version
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Prepare Your Data

#### Option A: Use Mock Data (for testing)
The app will automatically create a mock Excel file on first run with 3 sample worksheets.

#### Option B: Use Your Real Data
1. Place your Excel file in the `data/` folder
2. Make sure it follows this structure:
   - Column A: Contributor names (optional)
   - Row 1 (columns B, C, D...): Seed tracks (formatted with pink background)
   - Rows 2+: Related songs in each column

## Running the App

```bash
streamlit run main.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

1. **Select your Excel file** from the dropdown
2. **Search** for a song by typing any part of the track name or artist (typos are OK!)
3. **Adjust the sensitivity slider** (optional):
   - Lower (50-60%): Very forgiving, catches most typos
   - Medium (70-80%): Balanced matching (default: 70%)
   - Higher (90-100%): Strict, only exact or very close matches
4. **View results**: The seed track appears first (highlighted), followed by all matching songs with match scores

## Examples

### Exact match
Search for: `"opus"`
```
Seed Track: Peter Schilling - Major Tom
Matching Songs:
  1. Peter Schilling - Major Tom
  2. Pointer Sisters - I'm so excited
  3. Live is Life - Opus  ← Match: 100%
  4. Falco - Rock Me Amadeus
```

### Fuzzy match (typos OK!)
Search for: `"pocker face"` (misspelled)
```
Seed Track: The way I are - Timbaland ft Keri Hilson
Matching Songs:
  1. The way I are - Timbaland ft Keri Hilson
  2. Pink & Redman - Get The Party Started
  3. Sugababes - Push The Button
  4. Lady Gaga - Poker Face  ← Match: 85%
```

### Partial match
Search for: `"gaga"`
```
Finds: Lady Gaga - Poker Face  ← Match: 100%
```

## File Structure

```
donnerstagsspiel/
├── data/                      # Excel files go here
│   └── song_matcher_mock.xlsx # Auto-generated mock data
├── main.py                    # Main Streamlit app
├── create_mock_data.py        # Script to generate mock Excel
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Troubleshooting

**Python not found?**
- Install Python from [python.org](https://www.python.org/downloads/)
- Or use the Microsoft Store (Windows)

**Excel file not loading?**
- Check that the file is in the `data/` folder
- Ensure it has the correct structure (seed tracks in row 1, columns B+)

**Search not working?**
- Make sure song names are strings (not formulas)
- Try lowering the sensitivity slider to 60% or 50%
- Try searching with partial text (e.g., "gaga" instead of "Lady Gaga - Poker Face")
- Check for extra spaces or special characters in your Excel file

**Too many results?**
- Increase the sensitivity slider to 85% or higher
- Use more specific search terms (e.g., "lady gaga poker" instead of just "lady")

---

## Cloud Deployment (Streamlit Cloud)

### Prerequisites
- [Supabase](https://supabase.com) account (free tier works)
- [GitHub](https://github.com) account
- [Streamlit Cloud](https://share.streamlit.io) account

### Step 1: Set Up Supabase Database

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to SQL Editor and run the contents of `schema.sql`
3. Note your **Project URL** and **anon key** from Settings → API

### Step 2: Push Data to Supabase

On your local machine:

```bash
# Create .env file with your credentials
cp .env.example .env
# Edit .env and add your Supabase URL and SERVICE_KEY

# Push your Excel data to Supabase
python push_to_supabase.py --migrate-likes
```

### Step 3: Deploy to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → Select your repo → Set `main.py` as the main file
4. Click **Deploy**

### Step 4: Configure Secrets

In your Streamlit Cloud app settings → **Secrets**, add:

```toml
[supabase]
url = "https://your-project-id.supabase.co"
anon_key = "eyJ..."

USE_DATABASE = "true"
```

### Step 5: Share with Testers

Copy the Streamlit Cloud URL and share it with your test group!

---

## Data Modes

The app supports two modes:

| Mode | When Used | Data Source |
|------|-----------|-------------|
| **Excel Mode** | Local development | `data/*.xlsx` files |
| **Database Mode** | Cloud deployment | Supabase PostgreSQL |

- **Local**: Uses Excel files by default
- **Cloud**: Automatically uses database (Excel files not deployed)

To force database mode locally, set `USE_DATABASE=true` in your `.env` file.

---

## For Testers

See [USER_GUIDE.md](USER_GUIDE.md) for how to use the app.
