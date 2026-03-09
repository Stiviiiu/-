import os

TOKEN = os.environ.get("BOT_TOKEN", "8608911191:AAFrPUCctv3Tc4z3RSVim4XsoiQGX4KvQ8U")
ADMIN_IDS = [6458164021, 6393025468]

# Подключение к PostgreSQL (Supabase)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres.jjrgjqtlwfkejrbhpcsg:v9bGXwQjeK4G9X2M@aws-1-eu-west-1.pooler.supabase.com:5432/postgres")
