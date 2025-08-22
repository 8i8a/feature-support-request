#!/bin/bash

# Скрипт для установки и настройки GitHub Actions Self-hosted Runner
# Использование: ./setup-github-runner.sh [OWNER] [REPO] [TOKEN]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 GitHub Actions Self-hosted Runner Setup${NC}"
echo "============================================="

# Проверяем параметры
if [ $# -lt 3 ]; then
    echo -e "${RED}❌ Недостаточно параметров${NC}"
    echo "Использование: $0 <OWNER> <REPO> <TOKEN>"
    echo ""
    echo "Где:"
    echo "  OWNER  - владелец репозитория (например: username или organization)"
    echo "  REPO   - название репозитория"
    echo "  TOKEN  - токен для регистрации runner'а"
    echo ""
    echo "Получить токен можно в настройках репозитория:"
    echo "Settings → Actions → Runners → New self-hosted runner"
    exit 1
fi

OWNER=$1
REPO=$2
TOKEN=$3
RUNNER_NAME="${HOSTNAME}-runner"
WORK_DIR="/opt/github-runner"

echo -e "${YELLOW}📋 Конфигурация:${NC}"
echo "  Repository: ${OWNER}/${REPO}"
echo "  Runner Name: ${RUNNER_NAME}"
echo "  Work Directory: ${WORK_DIR}"
echo ""

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Запустите скрипт от имени root (sudo)${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Установка зависимостей...${NC}"

# Обновляем систему
apt-get update -y

# Устанавливаем необходимые пакеты
apt-get install -y \
    curl \
    wget \
    tar \
    jq \
    git \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    postgresql-client \
    systemctl

echo -e "${GREEN}✅ Зависимости установлены${NC}"

# Создаем пользователя для runner'а
echo -e "${BLUE}👤 Создание пользователя runner...${NC}"
if ! id "runner" &>/dev/null; then
    useradd -m -s /bin/bash runner
    echo -e "${GREEN}✅ Пользователь runner создан${NC}"
else
    echo -e "${YELLOW}⚠️  Пользователь runner уже существует${NC}"
fi

# Создаем рабочую директорию
echo -e "${BLUE}📁 Создание рабочей директории...${NC}"
mkdir -p $WORK_DIR
chown runner:runner $WORK_DIR

# Получаем последнюю версию runner'а
echo -e "${BLUE}🔍 Поиск последней версии GitHub Runner...${NC}"
RUNNER_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name | sed 's/v//')
echo "Найдена версия: ${RUNNER_VERSION}"

# Скачиваем и распаковываем runner
echo -e "${BLUE}📥 Скачивание GitHub Runner...${NC}"
cd $WORK_DIR
wget -q https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
tar xzf actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
rm actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
chown -R runner:runner $WORK_DIR

echo -e "${GREEN}✅ Runner скачан и распакован${NC}"

# Настраиваем runner от имени пользователя runner
echo -e "${BLUE}⚙️  Настройка GitHub Runner...${NC}"
sudo -u runner bash << EOF
cd $WORK_DIR
./config.sh --url https://github.com/${OWNER}/${REPO} --token ${TOKEN} --name ${RUNNER_NAME} --work _work --labels linux,x64,self-hosted,dev --unattended
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Runner настроен успешно${NC}"
else
    echo -e "${RED}❌ Ошибка при настройке runner'а${NC}"
    exit 1
fi

# Создаем systemd service
echo -e "${BLUE}🔧 Создание systemd service...${NC}"
cat > /etc/systemd/system/github-runner.service << EOF
[Unit]
Description=GitHub Actions Runner
After=network.target

[Service]
Type=simple
User=runner
Group=runner
WorkingDirectory=${WORK_DIR}
ExecStart=${WORK_DIR}/run.sh
Restart=on-failure
RestartSec=5
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=4m

# Переменные окружения
Environment=DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1
Environment=RUNNER_ALLOW_RUNASROOT=1

[Install]
WantedBy=multi-user.target
EOF

# Включаем и запускаем service
systemctl daemon-reload
systemctl enable github-runner.service
systemctl start github-runner.service

echo -e "${GREEN}✅ Systemd service создан и запущен${NC}"

# Проверяем статус
echo -e "${BLUE}🔍 Проверка статуса runner'а...${NC}"
sleep 3

if systemctl is-active --quiet github-runner.service; then
    echo -e "${GREEN}✅ GitHub Runner успешно запущен!${NC}"
    systemctl status github-runner.service --no-pager -l
else
    echo -e "${RED}❌ GitHub Runner не запустился${NC}"
    echo "Проверьте логи: journalctl -u github-runner.service"
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 Установка завершена успешно!${NC}"
echo ""
echo -e "${YELLOW}📋 Полезные команды:${NC}"
echo "  Статус:           systemctl status github-runner"
echo "  Запуск:           systemctl start github-runner"
echo "  Остановка:        systemctl stop github-runner"
echo "  Перезапуск:       systemctl restart github-runner"
echo "  Логи:             journalctl -u github-runner -f"
echo "  Удаление runner:  sudo -u runner ${WORK_DIR}/config.sh remove --token [TOKEN]"
echo ""
echo -e "${BLUE}🔗 Проверьте runner в настройках репозитория:${NC}"
echo "  https://github.com/${OWNER}/${REPO}/settings/actions/runners"
echo ""
