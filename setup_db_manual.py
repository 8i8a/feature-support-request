import asyncpg
import asyncio
import os

# Настройки подключения
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "8998"  # Замените на ваш пароль
DB_NAME = "support_bot"

async def setup_database():
    print("Настройка базы данных...")
    
    try:
        # Подключаемся к системной базе postgres для создания новой базы
        print("Подключение к PostgreSQL...")
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database="postgres"
        )
        
        # Проверяем, существует ли база данных
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", DB_NAME
        )
        
        if not exists:
            print(f"Создание базы данных {DB_NAME}...")
            await conn.execute(f"CREATE DATABASE {DB_NAME}")
            print("База данных создана!")
        else:
            print("База данных уже существует")
        
        await conn.close()
        
        # Подключаемся к созданной базе данных
        print("Создание таблиц...")
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        
        # Создаем таблицы
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                nickname VARCHAR(50) UNIQUE NOT NULL,
                is_blocked BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                text TEXT,
                file_id TEXT,
                message_type VARCHAR(20) NOT NULL DEFAULT 'text' CHECK (message_type IN ('text', 'voice', 'video_note')),
                type VARCHAR(20) NOT NULL CHECK (type IN ('support', 'request')),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Создаем таблицу жалоб
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id SERIAL PRIMARY KEY,
                message_id INTEGER,
                original_user_id BIGINT,
                complainer_user_id BIGINT REFERENCES users(user_id),
                text TEXT,
                file_id TEXT,
                message_type VARCHAR(20) NOT NULL DEFAULT 'text' CHECK (message_type IN ('text', 'voice', 'video_note')),
                created_at TIMESTAMP DEFAULT NOW(),
                complaint_date TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Добавляем недостающие столбцы в существующие таблицы
        try:
            await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN DEFAULT FALSE")
            print("✅ Столбец is_blocked добавлен в таблицу users")
        except Exception as e:
            print(f"ℹ️ Столбец is_blocked уже существует: {e}")
        
        # Создаем индексы
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_original_user_id ON complaints(original_user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_complaints_complainer_user_id ON complaints(complainer_user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_blocked ON users(is_blocked)")
        
        await conn.close()
        print("✅ Таблицы созданы/обновлены успешно!")
        
        # Проверяем подключение
        print("Проверка подключения...")
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        if result == 1:
            print("✅ База данных настроена и работает!")
        else:
            print("❌ Ошибка проверки базы данных")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        print("\nВозможные причины:")
        print("1. PostgreSQL не запущен")
        print("2. Неверный пароль (измените DB_PASSWORD в этом файле)")
        print("3. PostgreSQL не установлен")
        return False
    
    return True

async def main():
    success = await setup_database()
    if success:
        print("\n🎉 Готово! Теперь можно запускать бота")
    else:
        print("\n❌ Настройка не завершена. Исправьте ошибки и попробуйте снова")

if __name__ == "__main__":
    asyncio.run(main())
