@echo off
echo Запуск бота поддержки...
echo.

echo Проверка Python...
python --version
if errorlevel 1 (
    echo ОШИБКА: Python не установлен!
    pause
    exit /b 1
)

echo.
echo Установка зависимостей...
pip install -r requirements.txt

echo.
echo Очистка конфликтов бота...
python clear_bot.py

echo.
echo Запуск API сервера...
start cmd /k "python main.py"

echo.
echo Ожидание запуска сервера...
timeout /t 3

echo.
echo Запуск бота...
python bot.py

pause
