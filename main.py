import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import asyncpg
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Конфигурация БД
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "8998")
DB_NAME = os.getenv("DB_NAME", "support_bot")

# Логируем конфигурацию при запуске
logger.info(f"📊 Database config: {DB_HOST}:{DB_PORT}, DB: {DB_NAME}, User: {DB_USER}")

async def get_connection():
    """Подключение к БД"""
    try:
        conn = await asyncpg.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME
        )
        logger.info("🔗 Database connection successful")
        return conn
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

# Модели данных
class SetNickname(BaseModel):
    user_id: int
    nickname: str

class UserProfile(BaseModel):
    user_id: int

class Message(BaseModel):
    user_id: int
    text: Optional[str] = None
    file_id: Optional[str] = None
    message_type: str = "text"  # "text", "voice" или "video_note"

# API эндпоинты
@app.get("/")
async def index():
    return {"status": "API работает"}

@app.post("/set_nickname")
async def set_nickname(data: SetNickname):
    """Установка никнейма"""
    logger.info(f"🔍 API: Attempting to set nickname '{data.nickname}' for user {data.user_id}")
    
    try:
        conn = await get_connection()
        logger.info("🔗 Database connection established")
        
        # Проверяем, есть ли уже такой никнейм у другого пользователя
        existing_user = await conn.fetchrow(
            "SELECT user_id FROM users WHERE nickname = $1", 
            data.nickname
        )
        logger.info(f"🔍 Existing user check: {existing_user}")
        
        # Если никнейм занят другим пользователем - ошибка
        if existing_user and existing_user['user_id'] != data.user_id:
            await conn.close()
            logger.warning(f"❌ Nickname '{data.nickname}' already taken by user {existing_user['user_id']}")
            return {"status": "error", "message": "Nickname already taken"}
        
        # Если это тот же пользователь - просто обновляем (или ничего не делаем)
        if existing_user and existing_user['user_id'] == data.user_id:
            await conn.close()
            logger.info(f"✅ User already has this nickname: {data.user_id} -> {data.nickname}")
            return {"status": "success"}

        # Создание/обновление пользователя
        logger.info(f"💾 Creating/updating user {data.user_id} with nickname '{data.nickname}'")
        await conn.execute("""
            INSERT INTO users (user_id, nickname) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET nickname = EXCLUDED.nickname
        """, data.user_id, data.nickname)
        
        # Проверяем, что данные действительно сохранились
        saved_user = await conn.fetchrow("SELECT nickname FROM users WHERE user_id = $1", data.user_id)
        logger.info(f"🔍 Verification check: {saved_user}")
        
        await conn.close()
        
        if saved_user and saved_user['nickname'] == data.nickname:
            logger.info(f"✅ User saved successfully: {data.user_id} -> {data.nickname}")
            return {"status": "success"}
        else:
            logger.error(f"❌ Failed to save user: {data.user_id}, saved: {saved_user}")
            return {"status": "error", "message": "Failed to save nickname"}
            
    except Exception as e:
        logger.error(f"❌ Exception in set_nickname: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"status": "error", "message": f"Database error: {str(e)}"}

@app.post("/profile")
async def get_profile(data: UserProfile):
    """Получение профиля"""
    try:
        conn = await get_connection()
        user = await conn.fetchrow(
            "SELECT user_id, nickname, is_blocked FROM users WHERE user_id = $1", 
            data.user_id
        )
        
        # Получаем рейтинг из таблицы ratings
        try:
            rating_row = await conn.fetchrow(
                "SELECT rating FROM ratings WHERE user_id = $1", 
                data.user_id
            )
            rating = rating_row["rating"] if rating_row else 0
        except:
            rating = 0
        
        # Получаем количество жалоб на пользователя
        complaints_count = await conn.fetchval(
            "SELECT COUNT(*) FROM complaints WHERE original_user_id = $1", 
            data.user_id
        ) or 0
        
        await conn.close()
        
        if user:
            return {
                "status": "ok",
                "user_id": user["user_id"],
                "nickname": user["nickname"],
                "rating": rating,
                "complaints_count": complaints_count,
                "is_blocked": user["is_blocked"]
            }
        else:
            return {"status": "not_found"}
    except Exception as e:
        logger.error(f"Error in get_profile: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error"}

@app.post("/send_support")
async def send_support(data: Message):
    """Отправка поддержки"""
    try:
        conn = await get_connection()
        result = await conn.execute(
            "INSERT INTO messages (user_id, text, file_id, message_type, type) VALUES ($1, $2, $3, $4, 'support')",
            data.user_id, data.text, data.file_id, data.message_type
        )
        await conn.close()
        logger.info(f"✅ Support message saved: user_id={data.user_id}, type={data.message_type}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error"}

@app.post("/send_request")
async def send_request(data: Message):
    """Запрос помощи"""
    try:
        conn = await get_connection()
        result = await conn.execute(
            "INSERT INTO messages (user_id, text, file_id, message_type, type) VALUES ($1, $2, $3, $4, 'request')",
            data.user_id, data.text, data.file_id, data.message_type
        )
        await conn.close()
        logger.info(f"✅ Help request saved: user_id={data.user_id}, type={data.message_type}")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error"}

@app.post("/get_support")
async def get_support(data: UserProfile):
    """Получение поддержки"""
    try:
        conn = await get_connection()
        message = await conn.fetchrow("""
            SELECT m.text, u.nickname 
            FROM messages m
            JOIN users u ON m.user_id = u.user_id
            WHERE m.type = 'support' AND m.user_id != $1
            ORDER BY RANDOM() LIMIT 1
        """, data.user_id)
        await conn.close()
        
        if message:
            return {
                "status": "text",
                "message": message["text"],
                "nickname": message["nickname"]
            }
        else:
            return {"status": "no_messages"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error"}

@app.post("/get_help_request")
async def get_help_request(data: UserProfile):
    """Получение случайного запроса помощи"""
    try:
        conn = await get_connection()
        request = await conn.fetchrow("""
            SELECT m.id, m.text, m.file_id, m.message_type, u.nickname, m.user_id 
            FROM messages m
            JOIN users u ON m.user_id = u.user_id
            WHERE m.type = 'request' AND m.user_id != $1
            ORDER BY RANDOM() LIMIT 1
        """, data.user_id)
        await conn.close()
        
        if request:
            return {
                "status": "ok",
                "request": {
                    "id": request["id"],
                    "text": request["text"],
                    "file_id": request["file_id"],
                    "message_type": request["message_type"],
                    "nickname": request["nickname"],
                    "user_id": request["user_id"]
                }
            }
        else:
            return {"status": "no_requests"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error"}

@app.post("/delete_help_request")
async def delete_help_request(data: dict):
    """Удаление запроса помощи после ответа"""
    try:
        request_id = data.get("request_id")
        user_id = data.get("user_id")  # ID автора запроса
        
        conn = await get_connection()
        
        # Удаляем запрос помощи
        result = await conn.execute(
            "DELETE FROM messages WHERE id = $1 AND user_id = $2 AND type = 'request'",
            request_id, user_id
        )
        await conn.close()
        
        logger.info(f"✅ Help request deleted: id={request_id}, user_id={user_id}")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error deleting help request: {e}")
        return {"status": "error"}

@app.post("/submit_complaint")
async def submit_complaint(data: dict):
    """Подача жалобы на сообщение"""
    try:
        request_id = data.get("request_id")
        complainer_user_id = data.get("complainer_user_id")
        
        conn = await get_connection()
        
        # Получаем данные сообщения, на которое жалуются
        message_data = await conn.fetchrow("""
            SELECT id, user_id, text, file_id, message_type, created_at
            FROM messages 
            WHERE id = $1 AND type = 'request'
        """, request_id)
        
        if not message_data:
            await conn.close()
            return {"status": "message_not_found"}
        
        # Переносим сообщение в таблицу жалоб
        await conn.execute("""
            INSERT INTO complaints (message_id, original_user_id, complainer_user_id, text, file_id, message_type, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, 
            message_data["id"], 
            message_data["user_id"], 
            complainer_user_id,
            message_data["text"], 
            message_data["file_id"], 
            message_data["message_type"], 
            message_data["created_at"]
        )
        
        # Удаляем оригинальное сообщение из таблицы messages
        await conn.execute("DELETE FROM messages WHERE id = $1", request_id)
        
        # Проверяем количество жалоб на пользователя
        original_user_id = message_data["user_id"]
        complaints_count = await conn.fetchval(
            "SELECT COUNT(*) FROM complaints WHERE original_user_id = $1", 
            original_user_id
        ) or 0
        
        # Автоматическая блокировка при 5 или более жалобах
        auto_blocked = False
        if complaints_count >= 5:
            # Проверяем, не заблокирован ли уже пользователь
            is_already_blocked = await conn.fetchval(
                "SELECT is_blocked FROM users WHERE user_id = $1", 
                original_user_id
            )
            
            if not is_already_blocked:
                # Блокируем пользователя
                await conn.execute(
                    "UPDATE users SET is_blocked = TRUE WHERE user_id = $1", 
                    original_user_id
                )
                auto_blocked = True
                logger.warning(f"🚫 AUTO-BLOCKED user {original_user_id} after {complaints_count} complaints")
        
        await conn.close()
        
        logger.info(f"✅ Complaint submitted: message_id={request_id}, by_user={complainer_user_id}, complaints_total={complaints_count}")
        
        result = {"status": "success", "complaints_count": complaints_count}
        if auto_blocked:
            result["auto_blocked"] = True
            result["message"] = f"Пользователь автоматически заблокирован после {complaints_count} жалоб"
        
        return result
        
    except Exception as e:
        logger.error(f"Error submitting complaint: {e}")
        return {"status": "error"}

@app.post("/increment_rating")
async def increment_rating(data: UserProfile):
    """Увеличение рейтинга пользователя на +1"""
    try:
        conn = await get_connection()
        
        # Увеличиваем рейтинг на 1, создаем запись если ее нет
        await conn.execute("""
            INSERT INTO ratings (user_id, rating) VALUES ($1, 1)
            ON CONFLICT (user_id) DO UPDATE SET rating = ratings.rating + 1
        """, data.user_id)
        
        # Получаем новый рейтинг
        new_rating = await conn.fetchval(
            "SELECT rating FROM ratings WHERE user_id = $1", 
            data.user_id
        )
        
        await conn.close()
        
        logger.info(f"✅ Rating incremented for user {data.user_id}, new rating: {new_rating}")
        return {"status": "success", "new_rating": new_rating}
        
    except Exception as e:
        logger.error(f"Error incrementing rating: {e}")
        return {"status": "error"}

@app.get("/health")
async def health():
    """Проверка здоровья"""
    try:
        conn = await get_connection()
        await conn.fetchval("SELECT 1")
        await conn.close()
        return {"status": "healthy"}
    except Exception as e:
        return JSONResponse({"status": "unhealthy"}, status_code=503)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)