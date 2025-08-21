#!/usr/bin/env python3
"""
Скрипт для управления черным списком пользователей
"""

import asyncio
import asyncpg
import sys

# Настройки базы данных
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "password"  # Измените на свой пароль
DB_NAME = "support_bot"

async def get_connection():
    """Подключение к базе данных"""
    return await asyncpg.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME
    )

async def list_users():
    """Показать всех пользователей с их статусом"""
    conn = await get_connection()
    try:
        users = await conn.fetch("""
            SELECT u.user_id, u.nickname, u.is_blocked,
                   COUNT(c.id) as complaints_count
            FROM users u
            LEFT JOIN complaints c ON u.user_id = c.original_user_id
            GROUP BY u.user_id, u.nickname, u.is_blocked
            ORDER BY complaints_count DESC, u.user_id
        """)
        
        print("=" * 60)
        print("👥 СПИСОК ПОЛЬЗОВАТЕЛЕЙ")
        print("=" * 60)
        
        for user in users:
            user_id = user['user_id']
            nickname = user['nickname']
            is_blocked = user['is_blocked']
            complaints = user['complaints_count']
            
            if is_blocked:
                status = "🚫 ЗАБЛОКИРОВАН"
                if complaints >= 5:
                    status += " (автоблок)"
            else:
                status = "✅ активен"
            
            danger = ""
            if complaints >= 5:
                danger = " ⚠️ КРИТИЧНО"
            elif complaints >= 3:
                danger = " 🔴 высокий риск" 
            elif complaints >= 2:
                danger = " 🟡 средний риск"
            
            print(f"{user_id:>12} | {nickname:<20} | {status:<15} | {complaints} жалоб{danger}")
        
        print("=" * 60)
        
    finally:
        await conn.close()

async def block_user(user_id: int):
    """Заблокировать пользователя"""
    conn = await get_connection()
    try:
        # Проверяем что пользователь существует
        user = await conn.fetchrow("SELECT nickname, is_blocked FROM users WHERE user_id = $1", user_id)
        if not user:
            print(f"❌ Пользователь {user_id} не найден")
            return
        
        if user['is_blocked']:
            print(f"⚠️ Пользователь {user['nickname']} (ID: {user_id}) уже заблокирован")
            return
        
        # Блокируем
        await conn.execute("UPDATE users SET is_blocked = TRUE WHERE user_id = $1", user_id)
        print(f"🚫 Пользователь {user['nickname']} (ID: {user_id}) заблокирован")
        
    finally:
        await conn.close()

async def unblock_user(user_id: int):
    """Разблокировать пользователя"""
    conn = await get_connection()
    try:
        # Проверяем что пользователь существует
        user = await conn.fetchrow("SELECT nickname, is_blocked FROM users WHERE user_id = $1", user_id)
        if not user:
            print(f"❌ Пользователь {user_id} не найден")
            return
        
        if not user['is_blocked']:
            print(f"⚠️ Пользователь {user['nickname']} (ID: {user_id}) не заблокирован")
            return
        
        # Разблокируем
        await conn.execute("UPDATE users SET is_blocked = FALSE WHERE user_id = $1", user_id)
        print(f"✅ Пользователь {user['nickname']} (ID: {user_id}) разблокирован")
        
    finally:
        await conn.close()

async def show_help():
    """Показать справку"""
    print("""
🛡️  УПРАВЛЕНИЕ ЧЕРНЫМ СПИСКОМ

Команды:
  python manage_blacklist.py list                    - показать всех пользователей
  python manage_blacklist.py block <user_id>         - заблокировать пользователя
  python manage_blacklist.py unblock <user_id>       - разблокировать пользователя
  python manage_blacklist.py help                    - показать эту справку

Примеры:
  python manage_blacklist.py list
  python manage_blacklist.py block 12345678
  python manage_blacklist.py unblock 12345678

ℹ️  Заблокированные пользователи не смогут пользоваться ботом

🤖 Автоматическая блокировка:
   • При достижении 5 жалоб пользователь блокируется автоматически
   • Помечается как "(автоблок)" в списке пользователей
   • Администратор может разблокировать командой unblock
    """)

async def main():
    if len(sys.argv) < 2:
        await show_help()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "list":
            await list_users()
        elif command == "block":
            if len(sys.argv) != 3:
                print("❌ Использование: python manage_blacklist.py block <user_id>")
                return
            user_id = int(sys.argv[2])
            await block_user(user_id)
        elif command == "unblock":
            if len(sys.argv) != 3:
                print("❌ Использование: python manage_blacklist.py unblock <user_id>")
                return
            user_id = int(sys.argv[2])
            await unblock_user(user_id)
        elif command == "help":
            await show_help()
        else:
            print(f"❌ Неизвестная команда: {command}")
            await show_help()
            
    except ValueError:
        print("❌ user_id должен быть числом")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())
