import asyncpg
import asyncio

# Настройки подключения (измените пароль на свой)
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASSWORD = "8998"  # Замените на ваш пароль
DB_NAME = "support_bot"

async def check_database():
    """Проверка содержимого базы данных"""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        
        print("🔍 Проверка базы данных...")
        print("=" * 50)
        
        # Проверяем пользователей
        users = await conn.fetch("SELECT user_id, nickname, is_blocked FROM users ORDER BY user_id")
        print(f"👥 Пользователи ({len(users)}):")
        for user in users:
            blocked_status = " 🚫 ЗАБЛОКИРОВАН" if user.get('is_blocked', False) else ""
            print(f"  • {user['nickname']} (ID: {user['user_id']}){blocked_status}")
        
        print()
        
        # Проверяем сообщения поддержки
        support_msgs = await conn.fetch("""
            SELECT m.id, m.text, m.message_type, u.nickname 
            FROM messages m 
            JOIN users u ON m.user_id = u.user_id 
            WHERE m.type = 'support' 
            ORDER BY m.id DESC
        """)
        print(f"💝 Сообщения поддержки ({len(support_msgs)}):")
        for msg in support_msgs:
            text = msg['text'][:50] + "..." if msg['text'] and len(msg['text']) > 50 else msg['text']
            if msg['message_type'] == 'voice':
                msg_type = "🎤"
                content = text or '[голосовое]'
            elif msg['message_type'] == 'video_note':
                msg_type = "🎥"
                content = text or '[видео кружок]'
            else:
                msg_type = "📝"
                content = text or '[текст]'
            print(f"  • {msg_type} {msg['nickname']}: {content}")
        
        print()
        
        # Проверяем запросы помощи
        help_requests = await conn.fetch("""
            SELECT m.id, m.text, m.message_type, u.nickname 
            FROM messages m 
            JOIN users u ON m.user_id = u.user_id 
            WHERE m.type = 'request' 
            ORDER BY m.id DESC
        """)
        print(f"🆘 Запросы помощи ({len(help_requests)}):")
        for req in help_requests:
            text = req['text'][:50] + "..." if req['text'] and len(req['text']) > 50 else req['text']
            if req['message_type'] == 'voice':
                msg_type = "🎤"
                content = text or '[голосовое]'
            elif req['message_type'] == 'video_note':
                msg_type = "🎥"
                content = text or '[видео кружок]'
            else:
                msg_type = "📝"
                content = text or '[текст]'
            print(f"  • {msg_type} {req['nickname']}: {content}")
        
        print()
        
        # Проверяем жалобы
        complaints = await conn.fetch("""
            SELECT c.id, c.message_id, c.original_user_id, c.complainer_user_id, c.text, c.message_type, c.complaint_date,
                   u1.nickname as original_nickname, u2.nickname as complainer_nickname
            FROM complaints c
            LEFT JOIN users u1 ON c.original_user_id = u1.user_id
            LEFT JOIN users u2 ON c.complainer_user_id = u2.user_id
            ORDER BY c.complaint_date DESC
        """)
        print(f"🚨 Жалобы ({len(complaints)}):")
        for complaint in complaints:
            text = complaint['text'][:50] + "..." if complaint['text'] and len(complaint['text']) > 50 else complaint['text']
            if complaint['message_type'] == 'voice':
                msg_type = "🎤"
                content = text or '[голосовое]'
            elif complaint['message_type'] == 'video_note':
                msg_type = "🎥"
                content = text or '[видео кружок]'
            else:
                msg_type = "📝"
                content = text or '[текст]'
            original_nick = complaint['original_nickname'] or f"ID:{complaint['original_user_id']}"
            complainer_nick = complaint['complainer_nickname'] or f"ID:{complaint['complainer_user_id']}"
            print(f"  • {msg_type} от {original_nick}, жалоба от {complainer_nick}: {content}")
        
        print()
        
        # Проверяем активные запросы (которые еще не получили ответ)
        print("🔍 Статус запросов помощи:")
        if help_requests:
            print(f"  • Всего создано: {len(help_requests)}")
            print("  • Все активные запросы показаны выше")
            print("  • ℹ️ Запросы удаляются после получения ответа или жалобы")
        else:
            print("  • Нет активных запросов помощи")
        
        print()
        # Статистика жалоб по пользователям
        if complaints:
            print()
            complaints_stats = await conn.fetch("""
                SELECT c.original_user_id, u.nickname, COUNT(*) as complaint_count
                FROM complaints c
                LEFT JOIN users u ON c.original_user_id = u.user_id
                GROUP BY c.original_user_id, u.nickname
                ORDER BY complaint_count DESC
            """)
            print("📊 Статистика жалоб по пользователям:")
            for stat in complaints_stats:
                nickname = stat['nickname'] or f"ID:{stat['original_user_id']}"
                count = stat['complaint_count']
                if count >= 5:
                    status = "🚫 критический"
                elif count >= 3:
                    status = "🔴 высокий"
                elif count >= 2:
                    status = "⚠️ средний"
                else:
                    status = "✅ низкий"
                print(f"  • {nickname}: {count} жалоб ({status})")
        
        print()
        print("=" * 50)
        print(f"📊 Итого: {len(users)} пользователей, {len(support_msgs)} поддержки, {len(help_requests)} активных запросов, {len(complaints)} жалоб")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def main():
    print("Проверка сохранности данных в базе...")
    await check_database()

if __name__ == "__main__":
    asyncio.run(main())
