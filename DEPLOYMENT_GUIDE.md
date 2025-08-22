# 🚀 Руководство по развертыванию и CI/CD

Это руководство описывает настройку автоматизированного развертывания для проекта **positive-support-test** с использованием GitHub Actions и self-hosted runner.

## 📋 Содержание

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Предварительные требования](#предварительные-требования)
3. [Настройка сервера](#настройка-сервера)
4. [Установка GitHub Runner](#установка-github-runner)
5. [Настройка GitHub Secrets](#настройка-github-secrets)
6. [Запуск деплоя](#запуск-деплоя)
7. [Управление сервисами](#управление-сервисами)
8. [Мониторинг и отладка](#мониторинг-и-отладка)
9. [Устранение неполадок](#устранение-неполадок)

## 🏗️ Обзор архитектуры

### Компоненты системы:
- **API Service** (`main.py`) - FastAPI сервер на порту 8000
- **Telegram Bot** (`bot.py`) - Telegram бот, использующий API
- **PostgreSQL** - База данных
- **GitHub Actions** - CI/CD пайплайн
- **Self-hosted Runner** - Агент для выполнения деплоя

### Workflow деплоя:
1. Push в ветку `dev` → Trigger GitHub Actions
2. GitHub Actions → Self-hosted Runner на сервере
3. Runner выполняет шаги деплоя:
   - Остановка сервисов
   - Обновление кода
   - Установка зависимостей
   - Проверка БД
   - Запуск сервисов
   - Health check

## 📋 Предварительные требования

### Сервер:
- **OS:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **CPU:** 2+ cores
- **RAM:** 4GB+
- **Storage:** 20GB+
- **Network:** Доступ к интернету, открытые порты для webhook'ов

### Программное обеспечение:
- Python 3.9+
- PostgreSQL 12+
- Git
- curl, wget
- systemctl (systemd)

### GitHub:
- Репозиторий с правами администратора
- Возможность создавать Secrets
- Возможность добавлять self-hosted runners

## 🖥️ Настройка сервера

### 1. Подготовка системы

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка базовых пакетов
sudo apt install -y python3 python3-pip python3-venv git curl wget \
    build-essential postgresql-client systemctl

# Проверка версий
python3 --version  # Должен быть 3.9+
git --version
```

### 2. Настройка PostgreSQL

```bash
# Установка PostgreSQL (если не установлен)
sudo apt install -y postgresql postgresql-contrib

# Запуск и автозапуск
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Создание базы данных и пользователя
sudo -u postgres psql << EOF
CREATE DATABASE support_bot;
CREATE USER bot_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE support_bot TO bot_user;
\q
EOF
```

### 3. Клонирование репозитория

```bash
# Клонирование проекта
cd /opt
sudo git clone https://github.com/YOUR_USERNAME/positive-support-test.git
sudo chown -R $USER:$USER positive-support-test
cd positive-support-test

# Установка зависимостей
pip3 install -r requirements.txt
```

### 4. Настройка переменных окружения

```bash
# Копируем пример конфигурации
cp env.example .env

# Редактируем конфигурацию
nano .env
```

Обновите значения в `.env`:
```bash
# Database
DB_HOST=localhost
DB_PASSWORD=secure_password
DB_USER=bot_user

# Bot
BOT_TOKEN=YOUR_BOT_TOKEN

# Environment
ENVIRONMENT=dev
```

## 🤖 Установка GitHub Runner

### 1. Автоматическая установка

```bash
# Запуск скрипта установки
sudo ./setup-github-runner.sh YOUR_USERNAME REPO_NAME RUNNER_TOKEN
```

### 2. Получение токена для runner

1. Откройте репозиторий на GitHub
2. Перейдите в `Settings` → `Actions` → `Runners`
3. Нажмите `New self-hosted runner`
4. Выберите `Linux` и скопируйте токен из команды `./config.sh`

### 3. Ручная установка (если нужно)

```bash
# Создание пользователя
sudo useradd -m -s /bin/bash runner

# Создание директории
sudo mkdir -p /opt/github-runner
sudo chown runner:runner /opt/github-runner

# Скачивание runner'а
cd /opt/github-runner
RUNNER_VERSION=$(curl -s https://api.github.com/repos/actions/runner/releases/latest | jq -r .tag_name | sed 's/v//')
sudo -u runner wget https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz
sudo -u runner tar xzf actions-runner-linux-x64-${RUNNER_VERSION}.tar.gz

# Настройка
sudo -u runner ./config.sh --url https://github.com/YOUR_USERNAME/REPO_NAME \
    --token YOUR_TOKEN --name $(hostname)-runner --labels linux,x64,self-hosted,dev \
    --work _work --unattended

# Создание systemd service
sudo ./svc.sh install
sudo ./svc.sh start
```

### 4. Проверка установки

```bash
# Проверка статуса
sudo systemctl status github-runner

# Проверка в GitHub
# Перейдите в Settings → Actions → Runners
# Должен появиться ваш runner со статусом "Idle"
```

## 🔐 Настройка GitHub Secrets

Перейдите в настройки репозитория: `Settings` → `Secrets and variables` → `Actions`

### Обязательные secrets:

| Название | Описание | Пример |
|----------|----------|---------|
| `DEPLOY_HOST` | IP адрес или домен сервера | `192.168.1.100` |
| `DEPLOY_USER` | Пользователь для SSH | `ubuntu` |
| `DEPLOY_KEY` | Приватный SSH ключ | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DB_PASSWORD` | Пароль базы данных | `secure_password` |
| `BOT_TOKEN` | Токен Telegram бота | `123456:ABC-DEF...` |

### Опциональные secrets:

| Название | Описание | По умолчанию |
|----------|----------|--------------|
| `DB_HOST` | Хост базы данных | `localhost` |
| `DB_USER` | Пользователь БД | `postgres` |
| `DB_NAME` | Название БД | `support_bot` |
| `BACKEND_URL` | URL API | `http://localhost:8000` |

### Создание SSH ключа (если нужно):

```bash
# На локальной машине
ssh-keygen -t rsa -b 4096 -C "deploy@positive-support"

# Копирование публичного ключа на сервер
ssh-copy-id -i ~/.ssh/id_rsa.pub user@server

# Содержимое приватного ключа нужно добавить в DEPLOY_KEY secret
cat ~/.ssh/id_rsa
```

## ⚙️ Настройка systemd сервисов

### 1. Автоматическая настройка

```bash
# Запуск скрипта настройки
sudo ./setup-services.sh
```

### 2. Ручная настройка (если нужно)

```bash
# Создание сервиса для API
sudo tee /etc/systemd/system/positive-support-api.service > /dev/null << EOF
[Unit]
Description=Positive Support API
After=network.target postgresql.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/positive-support-test
ExecStart=/usr/bin/python3 main.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Создание сервиса для бота
sudo tee /etc/systemd/system/positive-support-bot.service > /dev/null << EOF
[Unit]
Description=Positive Support Bot
After=network.target positive-support-api.service
Requires=positive-support-api.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/positive-support-test
ExecStart=/usr/bin/python3 bot.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Включение сервисов
sudo systemctl daemon-reload
sudo systemctl enable positive-support-api
sudo systemctl enable positive-support-bot
```

## 🚀 Запуск деплоя

### 1. Автоматический деплой

Просто сделайте push в ветку `dev`:

```bash
git add .
git commit -m "Deploy to dev"
git push origin dev
```

GitHub Actions автоматически:
1. Запустит workflow на self-hosted runner
2. Остановит старые сервисы
3. Обновит код
4. Установит зависимости
5. Запустит новые сервисы
6. Проверит их работоспособность

### 2. Ручной деплой

```bash
# Основной скрипт деплоя
./deploy.sh

# Или с указанием окружения
./deploy.sh dev

# Другие команды
./deploy.sh stop     # Остановить сервисы
./deploy.sh status   # Показать статус
./deploy.sh restart  # Перезапустить
```

### 3. Управление через systemd

```bash
# Использование скрипта управления
./manage-services.sh start    # Запуск
./manage-services.sh stop     # Остановка
./manage-services.sh restart  # Перезапуск
./manage-services.sh status   # Статус
./manage-services.sh logs     # Логи
```

## 📊 Мониторинг и отладка

### 1. Проверка статуса сервисов

```bash
# Статус через systemd
sudo systemctl status positive-support-api
sudo systemctl status positive-support-bot

# Статус через скрипт
./manage-services.sh status

# Проверка процессов
ps aux | grep python
```

### 2. Просмотр логов

```bash
# Логи systemd
sudo journalctl -u positive-support-api -f
sudo journalctl -u positive-support-bot -f

# Логи приложения (если настроены)
tail -f logs/api.log
tail -f logs/bot.log

# Логи GitHub Runner
sudo journalctl -u github-runner -f
```

### 3. Health check

```bash
# Проверка API
curl http://localhost:8000/health

# Проверка базы данных
python3 check_db.py

# Полная проверка через скрипт
./deploy.sh status
```

### 4. Мониторинг GitHub Actions

1. Перейдите в репозиторий → `Actions`
2. Выберите последний workflow run
3. Просмотрите логи каждого шага
4. При ошибках - проверьте детали в разделе "Annotations"

## 🛠️ Устранение неполадок

### Проблема: Runner не подключается

**Симптомы:** Runner не появляется в GitHub или показывает статус "Offline"

**Решение:**
```bash
# Проверка статуса
sudo systemctl status github-runner

# Перезапуск
sudo systemctl restart github-runner

# Проверка логов
sudo journalctl -u github-runner -f

# Пересоздание runner'а
cd /opt/github-runner
sudo -u runner ./config.sh remove --token OLD_TOKEN
sudo -u runner ./config.sh --url https://github.com/USER/REPO --token NEW_TOKEN
```

### Проблема: API не запускается

**Симптомы:** Ошибка при запуске main.py, health check не проходит

**Решение:**
```bash
# Проверка зависимостей
pip3 install -r requirements.txt

# Проверка базы данных
python3 check_db.py

# Проверка портов
sudo netstat -tlnp | grep 8000

# Запуск в режиме отладки
python3 main.py

# Проверка переменных окружения
env | grep -E "(DB_|BOT_|BACKEND_)"
```

### Проблема: Бот не отвечает

**Симптомы:** Бот не реагирует на команды

**Решение:**
```bash
# Проверка токена
python3 -c "
import os
from aiogram import Bot
bot = Bot(token='YOUR_TOKEN')
print('Token is valid')
"

# Проверка подключения к API
curl http://localhost:8000/health

# Проверка логов бота
sudo journalctl -u positive-support-bot -f

# Перезапуск бота
sudo systemctl restart positive-support-bot
```

### Проблема: Workflow падает с ошибкой

**Симптомы:** GitHub Actions показывает failed status

**Решение:**

1. **Проверьте логи workflow** в GitHub Actions
2. **Проверьте runner на сервере:**
   ```bash
   sudo systemctl status github-runner
   sudo journalctl -u github-runner -f
   ```
3. **Проверьте доступность сервера:**
   ```bash
   # На локальной машине
   ssh user@server "echo 'Connection OK'"
   ```
4. **Проверьте secrets в GitHub:**
   - Убедитесь что все необходимые secrets настроены
   - Проверьте что SSH ключ правильный

### Проблема: База данных недоступна

**Симптомы:** Ошибки подключения к PostgreSQL

**Решение:**
```bash
# Проверка статуса PostgreSQL
sudo systemctl status postgresql

# Запуск PostgreSQL
sudo systemctl start postgresql

# Проверка подключения
psql -h localhost -U bot_user -d support_bot -c "SELECT 1;"

# Проверка настроек в pg_hba.conf
sudo nano /etc/postgresql/*/main/pg_hba.conf
```

### Отладочные команды

```bash
# Полная диагностика системы
echo "=== System Info ==="
uname -a
python3 --version
which python3

echo "=== Services Status ==="
sudo systemctl status postgresql
sudo systemctl status github-runner
sudo systemctl status positive-support-api
sudo systemctl status positive-support-bot

echo "=== Network ==="
sudo netstat -tlnp | grep -E "(5432|8000)"

echo "=== Processes ==="
ps aux | grep -E "(python|postgres|runner)"

echo "=== Disk Space ==="
df -h

echo "=== Memory ==="
free -h
```

## 📚 Дополнительные материалы

### Полезные ссылки:
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [aiogram Documentation](https://docs.aiogram.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Рекомендуемые улучшения:
1. **Настройка SSL/TLS** для HTTPS
2. **Настройка Nginx** как reverse proxy
3. **Добавление мониторинга** (Prometheus, Grafana)
4. **Настройка резервного копирования** базы данных
5. **Добавление тестов** в CI/CD pipeline
6. **Настройка уведомлений** о статусе деплоя

### Контакты для поддержки:
- GitHub Issues: [Ссылка на issues](https://github.com/YOUR_USERNAME/positive-support-test/issues)
- Документация: [README.md](README.md)

---

*Это руководство обновляется по мере развития проекта. Последнее обновление: $(date)*
