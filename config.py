import os

TOKEN = os.environ.get("BOT_TOKEN", "8608911191:AAEVmFXN_uOdy3AQzMQJP1N_5UzQftgIVjg")
ADMIN_IDS = [int(x) for x in os.environ.get("ADMIN_IDS", "6458164021").split(",")]

# Подключение к PostgreSQL (Supabase)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.jjrgjqtlwfkejrbhpcsg:v9bGXwQjeK4G9X2M@aws-1-eu-west-1.pooler.supabase.com:5432/postgres")
