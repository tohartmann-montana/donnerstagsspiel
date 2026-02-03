-- =============================================================================
-- Donnerstagsspiel Database Schema for Supabase
-- =============================================================================
-- Run this SQL in Supabase SQL Editor to set up the database
-- =============================================================================

-- Enable pg_trgm extension for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================================================
-- TABLES
-- =============================================================================

-- Table 1: Runden (Worksheets)
CREATE TABLE runden (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table 2: Clusters (Columns within worksheets = weeks)
CREATE TABLE clusters (
    id SERIAL PRIMARY KEY,
    runde_id INTEGER NOT NULL REFERENCES runden(id) ON DELETE CASCADE,
    week_number INTEGER NOT NULL,
    seed_track VARCHAR(500) NOT NULL,
    seed_contributor VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(runde_id, week_number)
);

-- Table 3: Songs (All songs including seed tracks)
CREATE TABLE songs (
    id SERIAL PRIMARY KEY,
    cluster_id INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    song_name VARCHAR(500) NOT NULL,
    song_name_normalized VARCHAR(500) NOT NULL,
    contributor VARCHAR(200),
    is_seed_track BOOLEAN DEFAULT FALSE,
    row_index INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table 4: Likes
CREATE TABLE likes (
    id SERIAL PRIMARY KEY,
    song_name VARCHAR(500) NOT NULL UNIQUE,
    like_count INTEGER DEFAULT 1,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Standard indexes
CREATE INDEX idx_songs_cluster ON songs(cluster_id);
CREATE INDEX idx_songs_normalized ON songs(song_name_normalized);
CREATE INDEX idx_clusters_runde ON clusters(runde_id);
CREATE INDEX idx_likes_song ON likes(song_name);

-- Trigram index for fuzzy search (pg_trgm)
CREATE INDEX idx_songs_trgm ON songs USING gin(song_name_normalized gin_trgm_ops);

-- =============================================================================
-- MATERIALIZED VIEW for fast search queries
-- =============================================================================

CREATE MATERIALIZED VIEW song_search_view AS
SELECT
    s.id AS song_id,
    s.song_name,
    s.song_name_normalized,
    s.contributor,
    s.is_seed_track,
    s.row_index,
    c.id AS cluster_id,
    c.seed_track,
    c.seed_contributor,
    c.week_number,
    r.id AS runde_id,
    r.name AS runde_name,
    CONCAT(r.name, ', Woche ', c.week_number) AS round_display
FROM songs s
JOIN clusters c ON s.cluster_id = c.id
JOIN runden r ON c.runde_id = r.id;

-- Indexes on the materialized view
CREATE INDEX idx_view_normalized ON song_search_view(song_name_normalized);
CREATE INDEX idx_view_trgm ON song_search_view USING gin(song_name_normalized gin_trgm_ops);
CREATE INDEX idx_view_cluster ON song_search_view(cluster_id);

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function: Refresh materialized view (call after data updates)
CREATE OR REPLACE FUNCTION refresh_search_view()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY song_search_view;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Fuzzy search using pg_trgm
CREATE OR REPLACE FUNCTION search_songs(
    query_text TEXT,
    threshold FLOAT DEFAULT 0.3,
    max_results INTEGER DEFAULT 100
)
RETURNS TABLE (
    song_id INTEGER,
    song_name TEXT,
    song_name_normalized TEXT,
    contributor TEXT,
    is_seed_track BOOLEAN,
    cluster_id INTEGER,
    seed_track TEXT,
    seed_contributor TEXT,
    round_display TEXT,
    runde_name TEXT,
    week_number INTEGER,
    similarity_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        v.song_id::INTEGER,
        v.song_name::TEXT,
        v.song_name_normalized::TEXT,
        v.contributor::TEXT,
        v.is_seed_track,
        v.cluster_id::INTEGER,
        v.seed_track::TEXT,
        v.seed_contributor::TEXT,
        v.round_display::TEXT,
        v.runde_name::TEXT,
        v.week_number,
        similarity(v.song_name_normalized, lower(query_text))::FLOAT AS similarity_score
    FROM song_search_view v
    WHERE similarity(v.song_name_normalized, lower(query_text)) > threshold
       OR v.song_name_normalized ILIKE '%' || lower(query_text) || '%'
    ORDER BY similarity_score DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get all clusters containing a specific song
CREATE OR REPLACE FUNCTION get_song_clusters(song_name_param TEXT)
RETURNS TABLE (
    cluster_id INTEGER,
    round_display TEXT,
    runde_name TEXT,
    week_number INTEGER,
    seed_track TEXT,
    seed_contributor TEXT,
    all_songs JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        c.id::INTEGER AS cluster_id,
        CONCAT(r.name, ', Woche ', c.week_number)::TEXT AS round_display,
        r.name::TEXT AS runde_name,
        c.week_number,
        c.seed_track::TEXT,
        c.seed_contributor::TEXT,
        (
            SELECT jsonb_agg(
                jsonb_build_object(
                    'song_name', s2.song_name,
                    'contributor', s2.contributor,
                    'is_seed_track', s2.is_seed_track
                ) ORDER BY s2.row_index
            )
            FROM songs s2 WHERE s2.cluster_id = c.id
        ) AS all_songs
    FROM songs s
    JOIN clusters c ON s.cluster_id = c.id
    JOIN runden r ON c.runde_id = r.id
    WHERE lower(s.song_name) = lower(song_name_param)
       OR s.song_name_normalized = lower(song_name_param);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get top songs by occurrence count
CREATE OR REPLACE FUNCTION get_top_songs(max_results INTEGER DEFAULT 50)
RETURNS TABLE (
    song_name_normalized TEXT,
    display_name TEXT,
    occurrence_count BIGINT,
    variants JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.song_name_normalized::TEXT,
        MIN(s.song_name)::TEXT AS display_name,
        COUNT(*)::BIGINT AS occurrence_count,
        jsonb_agg(DISTINCT s.song_name) AS variants
    FROM songs s
    WHERE s.song_name LIKE '% - %'  -- Filter to "Artist - Song" format
    GROUP BY s.song_name_normalized
    ORDER BY occurrence_count DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Increment like count (upsert)
CREATE OR REPLACE FUNCTION increment_like(song_name_param TEXT)
RETURNS INTEGER AS $$
DECLARE
    new_count INTEGER;
BEGIN
    INSERT INTO likes (song_name, like_count, updated_at)
    VALUES (song_name_param, 1, NOW())
    ON CONFLICT (song_name)
    DO UPDATE SET
        like_count = likes.like_count + 1,
        updated_at = NOW()
    RETURNING like_count INTO new_count;

    RETURN new_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get all likes as key-value pairs
CREATE OR REPLACE FUNCTION get_all_likes()
RETURNS TABLE (
    song_name TEXT,
    like_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT l.song_name::TEXT, l.like_count::INTEGER
    FROM likes l
    ORDER BY l.like_count DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================================
-- ROW LEVEL SECURITY (optional, for future multi-user support)
-- =============================================================================

-- Enable RLS on tables (disabled by default for simplicity)
-- ALTER TABLE runden ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE clusters ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE songs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE likes ENABLE ROW LEVEL SECURITY;

-- Allow public read access (enable these if you enable RLS)
-- CREATE POLICY "Public read access" ON runden FOR SELECT USING (true);
-- CREATE POLICY "Public read access" ON clusters FOR SELECT USING (true);
-- CREATE POLICY "Public read access" ON songs FOR SELECT USING (true);
-- CREATE POLICY "Public read access" ON likes FOR SELECT USING (true);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE runden IS 'Worksheets/Rounds from Excel file';
COMMENT ON TABLE clusters IS 'Columns within worksheets (weeks)';
COMMENT ON TABLE songs IS 'All songs including seed tracks';
COMMENT ON TABLE likes IS 'User likes for songs';
COMMENT ON MATERIALIZED VIEW song_search_view IS 'Pre-joined view for fast search queries';
COMMENT ON FUNCTION search_songs IS 'Fuzzy search using pg_trgm similarity';
COMMENT ON FUNCTION get_song_clusters IS 'Get all clusters containing a song';
COMMENT ON FUNCTION get_top_songs IS 'Get most frequently occurring songs';
COMMENT ON FUNCTION increment_like IS 'Add or increment a like for a song';
