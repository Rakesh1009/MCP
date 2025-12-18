import asyncio
import os
import sys

# Add app to path
sys.path.append(os.path.join(os.getcwd(), "app"))

# Set env vars for config
# We'll rely on .env or existing environment, but manual set for safety if needed
# We'll just trust get_settings works if .env is in root

from services.igdb import IGDBClient

async def test_sorting():
    client = IGDBClient()
    print("--- Testing SORT (Rating Desc) ---")
    # Query: No search, just sort.
    # Note: We need a where clause usually to limit scope or just getAll
    # Let's try to get top 5 rated games generally
    
    # Manually constructing body to bypass search_games method for raw test
    token = await client._ensure_token()
    headers = {
        "Client-ID": client.client_id,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    
    # TEST 1: Browse Mode (Sort by rating)
    body = (
        "fields name, total_rating;\n"
        "where total_rating > 90 & total_rating_count > 100;\n" # Filter out niche stuff
        "sort total_rating desc;\n"
        "limit 5;"
    )
    
    import httpx
    async with httpx.AsyncClient() as c:
        resp = await c.post("https://api.igdb.com/v4/games", content=body, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Data: {resp.json()}")

async def test_filtering():
    client = IGDBClient()
    print("\n--- Testing FILTER (Genre = Shooter) ---")
    
    token = await client._ensure_token()
    headers = {
        "Client-ID": client.client_id,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    
    # TEST 2: Genre Filter (String Match)
    # Note: genres.name is properly queryable?
    body = (
        "fields name, genres.name, total_rating;\n"
        'where genres.name ~ *"Shooter" * & total_rating > 80;\n'
        "sort total_rating desc;\n"
        "limit 5;"
    )
    
    import httpx
    async with httpx.AsyncClient() as c:
        resp = await c.post("https://api.igdb.com/v4/games", content=body, headers=headers)
        print(f"Status: {resp.status_code}")
        print(f"Data: {resp.json()}")

if __name__ == "__main__":
    asyncio.run(test_sorting())
    asyncio.run(test_filtering())
