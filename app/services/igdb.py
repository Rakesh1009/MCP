import time
import httpx
from typing import Any, Dict, List, Optional
import logging
from core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
IGDB_GAMES_URL = "https://api.igdb.com/v4/games"

class IGDBAuthError(RuntimeError):
    pass

class IGDBClient:
    """
    Async IGDB client using httpx.
    """

    def __init__(self, timeout: float = 10.0) -> None:
        self.client_id = settings.TWITCH_CLIENT_ID
        self.client_secret = settings.TWITCH_CLIENT_SECRET
        self.timeout = timeout
        
        self._access_token: Optional[str] = None
        self._token_expiry_ts: float = 0.0
        
        if not self.client_id or not self.client_secret:
            logger.warning("IGDB credentials not set. IGDB functionality will be disabled.")

    def _token_valid(self) -> bool:
        return bool(self._access_token) and time.time() < self._token_expiry_ts

    async def _fetch_app_token(self) -> None:
        if not self.client_id or not self.client_secret:
            raise IGDBAuthError("Missing Twitch credentials")

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(TWITCH_TOKEN_URL, data=data, timeout=self.timeout)
            
            if resp.status_code != 200:
                raise IGDBAuthError(f"Twitch auth failed: {resp.status_code} {resp.text}")
            
            payload = resp.json()
            access_token = payload.get("access_token")
            expires_in = payload.get("expires_in", 0)

            if not access_token:
                raise IGDBAuthError("Twitch token response missing access_token")

            self._access_token = access_token
            # Buffer by 60s
            self._token_expiry_ts = time.time() + max(int(expires_in) - 60, 30)

    async def _ensure_token(self) -> str:
        if not self._token_valid():
            await self._fetch_app_token()
        if not self._access_token:
             raise IGDBAuthError("Could not retrieve access token")
        return self._access_token

    async def search_games(
        self,
        search_text: str,
        genre: str = None,
        platform: str = None,
        sort_by: str = "relevance",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        
        search_text = (search_text or "").strip()
        # If no query and no filters, return empty to avoid fetching random games
        if not search_text and not genre and not platform and sort_by == "relevance":
            return []
            
        if not self.client_id or not self.client_secret:
            logger.warning("Skipping IGDB search (credentials missing)")
            return []

        try:
            token = await self._ensure_token()
        except Exception as e:
            logger.error(f"Error getting token: {e}")
            return []

        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        where_clauses = []
        if genre:
            # Case-insensitive fuzzy match for genre name
            where_clauses.append(f'genres.name ~ *"{genre}"*')
        
        if platform:
            where_clauses.append(f'platforms.name ~ *"{platform}"*')

        # Baseline filter to avoid junk
        where_clauses.append("total_rating_count > 5") # Only rated games

        where_block = ""
        if where_clauses:
            where_block = "where " + " & ".join(where_clauses) + ";\n"

        # Sorting logic
        sort_line = ""
        if sort_by == "rating":
            sort_line = "sort total_rating desc;\n"
        elif sort_by == "new":
            sort_line = "sort first_release_date desc;\n"
        
        # Search logic: 'search' param cannot be used with 'sort' easily in some endpoints?
        # Actually IGDB allows 'search "foo"; sort ...;' BUT:
        # If sorting by something other than relevance, we usually are in 'browse' mode (no search text).
        # If search text is present, IGDB defaults to relevance sort.
        # We can try to combine, but usually if user says "Best RPG", search text is empty ("") and genre="RPG", sort="rating".
        
        search_line = ""
        if search_text:
            search_line = f'search "{search_text}";\n'

        body = (
            "fields "
            "name, summary, storyline, "
            "genres.name, platforms.name, "
            "involved_companies.company.name, "
            "rating, total_rating, first_release_date, "
            "websites.url, websites.category;"
            f"\n{search_line}"
            f"{where_block}"
            f"{sort_line}"
            f"limit {int(limit)};"
        )

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    IGDB_GAMES_URL,
                    content=body.encode("utf-8"), # httpx uses 'content' for bytes
                    headers=headers,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            logger.error(f"IGDB search failed: {e}")
            return []

    @staticmethod
    def clean_games_data(games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Clean the raw IGDB response into a simplified list of dicts 
        that is easier for the LLM to process as JSON.
        """
        if not games:
            return []

        cleaned_list = []
        for g in games:
            # Extract simple platform names
            platforms = [p.get("name") for p in g.get("platforms", []) if isinstance(p, dict)]
            
            # Extract company names (developer/publisher)
            companies = []
            for ic in g.get("involved_companies", []):
                if isinstance(ic, dict) and "company" in ic:
                    c_name = ic["company"].get("name")
                    if c_name:
                        companies.append(c_name)

            # Extract websites (e.g. Steam, Official)
            # category 1 = official, 13 = steam, 17 = itch, etc.
            # We'll just grab URLs to pass context
            urls = [w.get("url") for w in g.get("websites", []) if isinstance(w, dict)]

            entry = {
                "id": g.get("id"),
                "name": g.get("name"),
                "summary": g.get("summary") or g.get("storyline") or "No description.",
                "rating": round(g.get("total_rating") or g.get("rating") or 0.0, 1),
                "platforms": platforms,
                "developers_publishers": companies,
                "release_date": g.get("first_release_date"), # Unix timestamp, maybe format?
                # "urls": urls[:3] # Optional, might clutter context
            }
            cleaned_list.append(entry)

        return cleaned_list
