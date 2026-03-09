import asyncpg
from datetime import datetime
from typing import Optional, Dict, Any

db_pool: Optional[asyncpg.Pool] = None

async def init_db_pool(dsn: str):
    global db_pool
    db_pool = await asyncpg.create_pool(dsn)

async def close_db_pool():
    global db_pool
    if db_pool:
        await db_pool.close()

async def get_user(user_id: int, username: str = None) -> Dict[str, Any]:
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        if row:
            if username is not None and row['username'] != username:
                await conn.execute("UPDATE users SET username = $1 WHERE user_id = $2", username, user_id)
                row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            return dict(row)
        else:
            await conn.execute("""
                INSERT INTO users (user_id, username, balance, last_card, last_bonus, cards)
                VALUES ($1, $2, 0, 0, 0, '{}')
            """, user_id, username or "")
            return {
                "user_id": user_id,
                "username": username or "",
                "balance": 0,
                "last_card": 0,
                "last_bonus": 0,
                "cards": []
            }

async def update_user(user_id: int, data: Dict[str, Any]):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            UPDATE users
            SET balance = $1, last_card = $2, last_bonus = $3, cards = $4
            WHERE user_id = $5
        """, data.get('balance', 0), data.get('last_card', 0), data.get('last_bonus', 0), data.get('cards', []), user_id)

async def check_cooldown(last_time: int, cooldown_hours: int = 1) -> tuple[bool, int]:
    if last_time == 0:
        return True, 0
    elapsed = datetime.now().timestamp() - last_time
    cooldown_sec = cooldown_hours * 3600
    if elapsed >= cooldown_sec:
        return True, 0
    remaining = cooldown_sec - elapsed
    return False, int(remaining)

RARITY_POINTS = {
    "необычная": 50,
    "редкая": 100,
    "эпическая": 200,
    "мифическая": 500,
    "ультра": 1000
}

RARITY_EMOJI = {
    "необычная": "🟢",
    "редкая": "🔵",
    "эпическая": "🟣",
    "мифическая": "🟡",
    "ультра": "🔴"
}
