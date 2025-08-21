import asyncpg
import asyncio
import json
from datetime import datetime

# Настройки подключения (измените пароль на свой)
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "8998"  # Замените на ваш пароль
DB_NAME = "support_bot"

async def backup_database():
    """Создание бэкапа базы данных в JSON файл"""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        
        print("📦 Создание бэкапа базы данных...")
        
        # Получаем всех пользователей
        users = await conn.fetch("SELECT * FROM users ORDER BY user_id")
        users_data = [dict(user) for user in users]
        
        # Получаем все сообщения
        messages = await conn.fetch("SELECT * FROM messages ORDER BY id")
        messages_data = []
        for msg in messages:
            msg_dict = dict(msg)
            # Конвертируем datetime в строку
            if msg_dict['created_at']:
                msg_dict['created_at'] = msg_dict['created_at'].isoformat()
            messages_data.append(msg_dict)
        
        await conn.close()
        
        # Создаем бэкап
        backup_data = {
            "backup_date": datetime.now().isoformat(),
            "users": users_data,
            "messages": messages_data
        }
        
        # Сохраняем в файл
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Бэкап создан: {filename}")
        print(f"📊 Сохранено: {len(users_data)} пользователей, {len(messages_data)} сообщений")
        
        return filename
        
    except Exception as e:
        print(f"❌ Ошибка создания бэкапа: {e}")
        return None

async def restore_database(backup_file):
    """Восстановление базы данных из JSON файла"""
    try:
        # Читаем бэкап
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        
        print(f"🔄 Восстановление из {backup_file}...")
        
        # Восстанавливаем пользователей
        for user in backup_data['users']:
            await conn.execute("""
                INSERT INTO users (user_id, nickname, created_at) 
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO NOTHING
            """, user['user_id'], user['nickname'], user['created_at'])
        
        # Восстанавливаем сообщения
        for msg in backup_data['messages']:
            await conn.execute("""
                INSERT INTO messages (user_id, text, file_id, message_type, type, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO NOTHING
            """, msg['user_id'], msg['text'], msg['file_id'], 
                msg['message_type'], msg['type'], msg['created_at'])
        
        await conn.close()
        
        print(f"✅ Восстановление завершено")
        print(f"📊 Обработано: {len(backup_data['users'])} пользователей, {len(backup_data['messages'])} сообщений")
        
    except Exception as e:
        print(f"❌ Ошибка восстановления: {e}")

async def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) > 2:
            await restore_database(sys.argv[2])
        else:
            print("❌ Укажите файл бэкапа: python backup_db.py restore backup_file.json")
    else:
        await backup_database()

if __name__ == "__main__":
    asyncio.run(main())
