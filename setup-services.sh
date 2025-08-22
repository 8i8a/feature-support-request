#!/bin/bash

# Скрипт для создания systemd сервисов для positive-support-test
# Использование: sudo ./setup-services.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Setting up systemd services for positive-support-test${NC}"
echo "============================================================"

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Запустите скрипт от имени root (sudo)${NC}"
    exit 1
fi

# Получаем пути
PROJECT_DIR=$(pwd)
USER=$(logname 2>/dev/null || echo $SUDO_USER)

if [ -z "$USER" ]; then
    echo -e "${RED}❌ Не удалось определить пользователя${NC}"
    exit 1
fi

echo -e "${YELLOW}📋 Конфигурация:${NC}"
echo "  Project Directory: $PROJECT_DIR"
echo "  User: $USER"
echo ""

# Проверяем наличие файлов
if [ ! -f "$PROJECT_DIR/main.py" ]; then
    echo -e "${RED}❌ main.py не найден в $PROJECT_DIR${NC}"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/bot.py" ]; then
    echo -e "${RED}❌ bot.py не найден в $PROJECT_DIR${NC}"
    exit 1
fi

# Создаем сервис для API
echo -e "${BLUE}🔧 Создание сервиса positive-support-api...${NC}"
cat > /etc/systemd/system/positive-support-api.service << EOF
[Unit]
Description=Positive Support API
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/main.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5
KillMode=mixed
TimeoutStopSec=5

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=positive-support-api

# Безопасность
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
EOF

# Создаем сервис для бота
echo -e "${BLUE}🔧 Создание сервиса positive-support-bot...${NC}"
cat > /etc/systemd/system/positive-support-bot.service << EOF
[Unit]
Description=Positive Support Telegram Bot
After=network.target positive-support-api.service
Requires=positive-support-api.service

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=/usr/bin:/usr/local/bin
Environment=PYTHONPATH=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PROJECT_DIR/bot.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5
KillMode=mixed
TimeoutStopSec=5

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=positive-support-bot

# Безопасность
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$PROJECT_DIR

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd
echo -e "${BLUE}🔄 Перезагрузка systemd...${NC}"
systemctl daemon-reload

# Включаем сервисы
echo -e "${BLUE}✅ Включение сервисов...${NC}"
systemctl enable positive-support-api.service
systemctl enable positive-support-bot.service

echo -e "${GREEN}✅ Сервисы созданы и включены!${NC}"

echo ""
echo -e "${YELLOW}📋 Полезные команды:${NC}"
echo ""
echo "Управление API:"
echo "  systemctl start positive-support-api     # Запуск"
echo "  systemctl stop positive-support-api      # Остановка"
echo "  systemctl restart positive-support-api   # Перезапуск"
echo "  systemctl status positive-support-api    # Статус"
echo "  journalctl -u positive-support-api -f    # Логи"
echo ""
echo "Управление ботом:"
echo "  systemctl start positive-support-bot     # Запуск"
echo "  systemctl stop positive-support-bot      # Остановка"
echo "  systemctl restart positive-support-bot   # Перезапуск"
echo "  systemctl status positive-support-bot    # Статус"
echo "  journalctl -u positive-support-bot -f    # Логи"
echo ""
echo "Управление обоими сервисами:"
echo "  ./manage-services.sh start    # Запуск всех"
echo "  ./manage-services.sh stop     # Остановка всех"
echo "  ./manage-services.sh restart  # Перезапуск всех"
echo "  ./manage-services.sh status   # Статус всех"
echo ""

# Создаем скрипт для управления сервисами
echo -e "${BLUE}🔧 Создание скрипта управления сервисами...${NC}"
cat > $PROJECT_DIR/manage-services.sh << 'EOF'
#!/bin/bash

# Скрипт для управления сервисами positive-support-test

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

API_SERVICE="positive-support-api"
BOT_SERVICE="positive-support-bot"

case "${1:-status}" in
    "start")
        echo -e "${BLUE}🚀 Запуск сервисов...${NC}"
        sudo systemctl start $API_SERVICE
        sleep 3
        sudo systemctl start $BOT_SERVICE
        echo -e "${GREEN}✅ Сервисы запущены${NC}"
        ;;
    "stop")
        echo -e "${BLUE}🛑 Остановка сервисов...${NC}"
        sudo systemctl stop $BOT_SERVICE
        sudo systemctl stop $API_SERVICE
        echo -e "${GREEN}✅ Сервисы остановлены${NC}"
        ;;
    "restart")
        echo -e "${BLUE}🔄 Перезапуск сервисов...${NC}"
        sudo systemctl stop $BOT_SERVICE
        sudo systemctl restart $API_SERVICE
        sleep 3
        sudo systemctl start $BOT_SERVICE
        echo -e "${GREEN}✅ Сервисы перезапущены${NC}"
        ;;
    "status")
        echo -e "${BLUE}📊 Статус сервисов${NC}"
        echo "==================="
        echo ""
        echo -e "${YELLOW}API Service:${NC}"
        sudo systemctl status $API_SERVICE --no-pager -l || true
        echo ""
        echo -e "${YELLOW}Bot Service:${NC}"
        sudo systemctl status $BOT_SERVICE --no-pager -l || true
        ;;
    "logs")
        echo -e "${BLUE}📄 Логи сервисов${NC}"
        echo "================="
        echo ""
        echo -e "${YELLOW}API Logs (последние 20 строк):${NC}"
        sudo journalctl -u $API_SERVICE -n 20 --no-pager
        echo ""
        echo -e "${YELLOW}Bot Logs (последние 20 строк):${NC}"
        sudo journalctl -u $BOT_SERVICE -n 20 --no-pager
        ;;
    "enable")
        echo -e "${BLUE}✅ Включение автозапуска сервисов...${NC}"
        sudo systemctl enable $API_SERVICE
        sudo systemctl enable $BOT_SERVICE
        echo -e "${GREEN}✅ Автозапуск включен${NC}"
        ;;
    "disable")
        echo -e "${BLUE}❌ Отключение автозапуска сервисов...${NC}"
        sudo systemctl disable $API_SERVICE
        sudo systemctl disable $BOT_SERVICE
        echo -e "${GREEN}✅ Автозапуск отключен${NC}"
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start     - Запустить все сервисы"
        echo "  stop      - Остановить все сервисы"
        echo "  restart   - Перезапустить все сервисы"
        echo "  status    - Показать статус сервисов (default)"
        echo "  logs      - Показать логи сервисов"
        echo "  enable    - Включить автозапуск"
        echo "  disable   - Отключить автозапуск"
        echo "  help      - Показать эту справку"
        ;;
    *)
        echo -e "${RED}❌ Неизвестная команда: $1${NC}"
        echo "Используйте '$0 help' для справки"
        exit 1
        ;;
esac
EOF

# Делаем скрипт исполняемым
chmod +x $PROJECT_DIR/manage-services.sh
chown $USER:$USER $PROJECT_DIR/manage-services.sh

echo -e "${GREEN}✅ Скрипт управления создан: $PROJECT_DIR/manage-services.sh${NC}"
echo ""
echo -e "${BLUE}🎉 Установка завершена!${NC}"
echo ""
echo -e "${YELLOW}Следующие шаги:${NC}"
echo "1. Проверьте конфигурацию в main.py и bot.py"
echo "2. Убедитесь что PostgreSQL запущен и доступен"
echo "3. Запустите сервисы: ./manage-services.sh start"
echo "4. Проверьте статус: ./manage-services.sh status"
