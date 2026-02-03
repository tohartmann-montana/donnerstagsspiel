"""
Database connection and query functions for Donnerstagsspiel
Uses direct REST API calls to Supabase (no supabase package required).

Usage:
    Set environment variables:
        SUPABASE_URL - Your Supabase project URL
        SUPABASE_ANON_KEY or SUPABASE_SERVICE_KEY - Your Supabase API key

    Or for Streamlit Cloud, use st.secrets:
        [supabase]
        url = "https://xxx.supabase.co"
        key = "your_key"
"""
import os
import requests
import streamlit as st
from typing import Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

def get_supabase_credentials():
    """
    Get Supabase credentials from environment or Streamlit secrets.
    Returns (url, key) tuple or (None, None) if not configured.
    """
    # Try Streamlit secrets first (for Streamlit Cloud deployment)
    try:
        url = st.secrets.get("supabase", {}).get("url") or st.secrets.get("SUPABASE_URL")
        key = (st.secrets.get("supabase", {}).get("key") or
               st.secrets.get("supabase", {}).get("anon_key") or
               st.secrets.get("SUPABASE_ANON_KEY") or
               st.secrets.get("SUPABASE_SERVICE_KEY"))
        if url and key:
            return url, key
    except Exception:
        pass

    # Fall back to environment variables
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_ANON_KEY") or
           os.environ.get("SUPABASE_SERVICE_KEY"))

    return url, key


# Cache credentials
_CREDENTIALS = None

def _get_credentials():
    global _CREDENTIALS
    if _CREDENTIALS is None:
        _CREDENTIALS = get_supabase_credentials()
    return _CREDENTIALS


def supabase_request(method: str, endpoint: str, data=None, params=None):
    """
    Make a request to Supabase REST API.

    Args:
        method: HTTP method (GET, POST, DELETE)
        endpoint: API endpoint (e.g., "/rest/v1/songs" or "/rest/v1/rpc/search_songs")
        data: JSON data for POST requests
        params: Query parameters for GET requests

    Returns:
        Response data (list or dict) or None on error
    """
    url, key = _get_credentials()

    if not url or not key:
        return None

    full_url = f"{url}{endpoint}"
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    try:
        if method == "GET":
            response = requests.get(full_url, headers=headers, params=params, timeout=30)
        elif method == "POST":
            response = requests.post(full_url, headers=headers, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(full_url, headers=headers, params=params, timeout=30)
        else:
            return None

        if response.status_code >= 400:
            st.error(f"API Error {response.status_code}: {response.text[:200]}")
            return None

        return response.json() if response.text else []

    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")
        return None


def is_database_available() -> bool:
    """Check if database connection is available and configured."""
    url, key = _get_credentials()
    if not url or not key:
        return False

    # Test connection
    result = supabase_request("GET", "/rest/v1/runden", params={"select": "id", "limit": "1"})
    return result is not None


def get_database_diagnostics() -> dict:
    """
    Get detailed diagnostics about database connection.
    Returns dict with status, error messages, and connection details.
    """
    diagnostics = {
        'available': False,
        'error': None,
        'url_configured': False,
        'key_configured': False,
        'url_preview': None,
        'connection_test': None,
        'song_count': 0,
        'secrets_source': None,
        'secrets_keys': []
    }

    # Debug: Check what's in st.secrets
    try:
        # List all available secret keys
        diagnostics['secrets_keys'] = list(st.secrets.keys()) if hasattr(st.secrets, 'keys') else ['(no keys method)']

        # Check which source provided credentials
        if "supabase" in st.secrets:
            diagnostics['secrets_source'] = 'st.secrets.supabase'
        elif "SUPABASE_URL" in st.secrets:
            diagnostics['secrets_source'] = 'st.secrets (top-level)'
        else:
            diagnostics['secrets_source'] = 'os.environ'
    except Exception as e:
        diagnostics['secrets_source'] = f'error: {e}'

    # Check credentials
    url, key = _get_credentials()
    diagnostics['url_configured'] = bool(url)
    diagnostics['key_configured'] = bool(key)

    if url:
        # Show partial URL for debugging (hide project ID partially)
        diagnostics['url_preview'] = url[:30] + "..." if len(url) > 30 else url

    if not url:
        diagnostics['error'] = "SUPABASE_URL not configured in secrets"
        return diagnostics

    if not key:
        diagnostics['error'] = "SUPABASE_ANON_KEY not configured in secrets"
        return diagnostics

    # Test actual connection
    try:
        response = requests.get(
            f"{url}/rest/v1/runden",
            params={"select": "id", "limit": "1"},
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            timeout=10
        )

        if response.status_code == 200:
            diagnostics['connection_test'] = "OK"
            diagnostics['available'] = True

            # Get song count
            count_response = requests.get(
                f"{url}/rest/v1/songs",
                params={"select": "id"},
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Prefer": "count=exact"
                },
                timeout=10
            )
            if count_response.status_code in (200, 206):  # 206 = Partial Content (paginated)
                count = count_response.headers.get('content-range', '').split('/')[-1]
                diagnostics['song_count'] = int(count) if count.isdigit() else 0
        else:
            diagnostics['error'] = f"HTTP {response.status_code}: {response.text[:100]}"
            diagnostics['connection_test'] = "FAILED"

    except requests.exceptions.Timeout:
        diagnostics['error'] = "Connection timeout (10s)"
        diagnostics['connection_test'] = "TIMEOUT"
    except requests.exceptions.RequestException as e:
        diagnostics['error'] = f"Request error: {str(e)[:100]}"
        diagnostics['connection_test'] = "ERROR"
    except Exception as e:
        diagnostics['error'] = f"Unexpected error: {str(e)[:100]}"
        diagnostics['connection_test'] = "ERROR"

    return diagnostics


# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_all_data_from_db():
    """
    Load all song data from Supabase.
    Returns data in a format compatible with the existing app structure.
    """
    result = supabase_request("GET", "/rest/v1/song_search_view", params={"select": "*"})

    if result is None:
        return None

    return {
        'songs': result,
        'total_songs': len(result),
        'source': 'supabase'
    }


@st.cache_data(ttl=300)
def get_all_songs_from_db() -> list:
    """Get all unique song names for autocomplete."""
    result = supabase_request("GET", "/rest/v1/songs", params={"select": "song_name"})

    if result is None:
        return []

    songs = sorted(set(row['song_name'] for row in result))
    return songs


@st.cache_data(ttl=300)
def get_all_contributors_from_db() -> list:
    """Get all unique contributor names."""
    # Get contributors from songs table
    result = supabase_request("GET", "/rest/v1/songs",
                              params={"select": "contributor", "contributor": "not.is.null"})

    if result is None:
        return []

    contributors = set(row['contributor'] for row in result if row.get('contributor'))

    # Also get seed contributors from clusters
    result2 = supabase_request("GET", "/rest/v1/clusters",
                               params={"select": "seed_contributor", "seed_contributor": "not.is.null"})

    if result2:
        seed_contributors = set(row['seed_contributor'] for row in result2 if row.get('seed_contributor'))
        contributors = contributors | seed_contributors

    return sorted(contributors)


# =============================================================================
# SEARCH FUNCTIONS
# =============================================================================

def search_songs_db(query: str, fuzzy_threshold: int = 70) -> list:
    """
    Search songs using PostgreSQL pg_trgm fuzzy matching.

    Args:
        query: Search query string
        fuzzy_threshold: Minimum match score (0-100), default 70

    Returns:
        List of matching song records with similarity scores
    """
    if not query or len(query) < 2:
        return []

    # Convert threshold from 0-100 to 0-1 scale for pg_trgm
    threshold = fuzzy_threshold / 100.0

    result = supabase_request("POST", "/rest/v1/rpc/search_songs", data={
        "query_text": query,
        "threshold": threshold,
        "max_results": 100
    })

    if result is None:
        return []

    # Group results by cluster for display
    clusters = {}
    for row in result:
        cluster_id = row['cluster_id']
        if cluster_id not in clusters:
            clusters[cluster_id] = {
                'cluster_id': cluster_id,
                'round_display': row['round_display'],
                'seed_track': row['seed_track'],
                'seed_contributor': row['seed_contributor'],
                'matched_songs': [],
                'match_scores': {},
                'all_songs': []
            }
        clusters[cluster_id]['matched_songs'].append(row['song_name'])
        clusters[cluster_id]['match_scores'][row['song_name']] = int(row['similarity_score'] * 100)

    # Fetch full cluster data for each matched cluster
    for cluster_id, cluster_data in clusters.items():
        full_cluster = get_cluster_songs(cluster_id)
        if full_cluster:
            cluster_data['all_songs'] = full_cluster['songs']
            cluster_data['contributors'] = full_cluster['contributors']

    return list(clusters.values())


def get_cluster_songs(cluster_id: int) -> dict:
    """Get all songs in a cluster."""
    result = supabase_request("GET", "/rest/v1/songs", params={
        "select": "*",
        "cluster_id": f"eq.{cluster_id}",
        "order": "row_index"
    })

    if result is None:
        return None

    songs = [row['song_name'] for row in result]
    contributors = {row['song_name']: row.get('contributor') for row in result}

    return {
        'songs': songs,
        'contributors': contributors
    }


def get_song_connections_db(song_name: str) -> list:
    """
    Find all clusters containing the given song.

    Args:
        song_name: Name of the song to find connections for

    Returns:
        List of cluster info dicts with all connected songs
    """
    result = supabase_request("POST", "/rest/v1/rpc/get_song_clusters", data={
        "song_name_param": song_name
    })

    if result is None:
        return []

    connections = []
    for row in result:
        all_songs_data = row.get('all_songs', [])

        # Build all_songs list and contributors dict
        all_songs = [s['song_name'] for s in all_songs_data]
        contributors = {s['song_name']: s.get('contributor', '') for s in all_songs_data}

        connections.append({
            'round_display': row['round_display'],
            'seed_track': row['seed_track'],
            'seed_contributor': row.get('seed_contributor', ''),
            'all_songs': all_songs,
            'contributors': contributors
        })

    return connections


# =============================================================================
# TOP SONGS / BEST OF FUNCTIONS
# =============================================================================

@st.cache_data(ttl=300)
def get_top_songs_db(limit: int = 50) -> list:
    """
    Get top songs by occurrence count.

    Args:
        limit: Maximum number of songs to return

    Returns:
        List of dicts with name, count, variants
    """
    result = supabase_request("POST", "/rest/v1/rpc/get_top_songs", data={
        "max_results": limit
    })

    if result is None:
        return []

    top_songs = []
    for row in result:
        top_songs.append({
            'name': row['display_name'],
            'normalized': row['song_name_normalized'],
            'count': row['occurrence_count'],
            'variants': row.get('variants', [row['display_name']])
        })

    return top_songs


# =============================================================================
# LIKES FUNCTIONS
# =============================================================================

def get_likes_db() -> dict:
    """
    Get all likes from database.

    Returns:
        Dict mapping song_name -> like_count
    """
    result = supabase_request("POST", "/rest/v1/rpc/get_all_likes", data={})

    if result is None:
        return {}

    return {row['song_name']: row['like_count'] for row in result}


def add_like_db(song_name: str) -> int:
    """
    Add a like to a song (or increment existing).

    Args:
        song_name: Name of the song to like

    Returns:
        New like count for the song
    """
    result = supabase_request("POST", "/rest/v1/rpc/increment_like", data={
        "song_name_param": song_name
    })

    if result is None:
        return 0

    return result if isinstance(result, int) else 1


# =============================================================================
# CONTRIBUTOR FUNCTIONS
# =============================================================================

def get_contributor_songs_db(contributor_name: str) -> list:
    """
    Get all songs by a specific contributor.

    Args:
        contributor_name: Name of the contributor/DJ

    Returns:
        List of dicts with song info
    """
    # Get songs where this person is the contributor
    result = supabase_request("GET", "/rest/v1/song_search_view", params={
        "select": "*",
        "contributor": f"eq.{contributor_name}"
    })

    songs = []
    if result:
        for row in result:
            songs.append({
                'song': row['song_name'],
                'round': row['round_display'],
                'type': '🎵',
                'type_label': 'Song'
            })

    # Also get seed tracks where they are the seed_contributor
    result2 = supabase_request("GET", "/rest/v1/song_search_view", params={
        "select": "*",
        "seed_contributor": f"eq.{contributor_name}",
        "is_seed_track": "eq.true"
    })

    if result2:
        for row in result2:
            # Avoid duplicates
            if not any(s['song'] == row['song_name'] for s in songs):
                songs.append({
                    'song': row['song_name'],
                    'round': row['round_display'],
                    'type': '⭐',
                    'type_label': 'Ausgangssong'
                })

    return songs


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def clear_cache():
    """Clear all cached data (useful after data updates)."""
    load_all_data_from_db.clear()
    get_all_songs_from_db.clear()
    get_all_contributors_from_db.clear()
    get_top_songs_db.clear()


def get_database_stats() -> dict:
    """Get statistics about the database."""
    stats = {}

    # Count runden
    result = supabase_request("GET", "/rest/v1/runden", params={"select": "id"})
    stats['runden'] = len(result) if result else 0

    # Count clusters
    result = supabase_request("GET", "/rest/v1/clusters", params={"select": "id"})
    stats['clusters'] = len(result) if result else 0

    # Count songs
    result = supabase_request("GET", "/rest/v1/songs", params={"select": "id"})
    stats['songs'] = len(result) if result else 0

    # Count likes
    result = supabase_request("GET", "/rest/v1/likes", params={"select": "id"})
    stats['likes'] = len(result) if result else 0

    return stats
