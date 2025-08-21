import requests

BOT_TOKEN = "8234250977:AAFSjY7Ci-xajOeB-JqRgWB2vTVtQaW9UCc"

print("Очистка конфликтов бота...")

# Удаляем webhook
response = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
print("Webhook cleared:", response.json())

# Очищаем pending updates
response = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset=-1")
print("Updates cleared:", response.json())

print("Готово! Теперь запускайте бота.")
