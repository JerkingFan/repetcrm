# RepetCRM

Монорепозиторий: **лендинг**, **CRM-приложение** (Next.js + FastAPI) с локальной AI-генерацией домашних заданий через Ollama.

## Структура

```
repetcrm/
├── landing/           # Статический лендинг
├── frontend/          # Next.js App Router (порт 3000)
├── backend/           # FastAPI (порт 8000)
├── docker-compose.yml
└── scripts/           # Скрипты запуска
```

## Быстрый старт (локально)

### 1. Локальная AI (для генерации ДЗ)

**Вариант A — Ollama (рекомендуется, ~2 ГБ):**

```powershell
.\scripts\setup-ollama.ps1
```

Или вручную: `ollama serve` → `ollama pull qwen2.5:3b`

**Вариант B — встроенная Math-модель без Ollama (~3 ГБ, transformers):**

```powershell
.\scripts\download-local-model.ps1
```

Модель: `Qwen/Qwen2.5-Math-1.5B-Instruct` (CUDA, если есть видеокарта; иначе CPU).

**Вариант C — без нейросети:** если Ollama не запущена, бэкенд соберёт ДЗ по шаблону из чек-листа (всегда работает).

### 2. Бэкенд

```powershell
.\scripts\start-backend.ps1
```

API: http://localhost:8000 — документация: http://localhost:8000/docs

### 3. Фронтенд

```powershell
.\scripts\start-frontend.ps1
```

Если в dev-режиме ошибка `__webpack_modules__[moduleId] is not a function`:
```powershell
cd frontend
npm run clean
npm run dev
```
Также проверьте, что нет лишнего `F:\package-lock.json` — он сбивает корень проекта Next.js.

CRM: http://localhost:3000

### 4. Лендинг

- Через Next.js: http://localhost:3000/landing/index.html
- Или статически из папки `landing/`

## Деплой на сервер

Полная инструкция: **[deploy/DEPLOY.md](deploy/DEPLOY.md)**

- SQL-схемы: `deploy/sql/` (PostgreSQL и SQLite)
- Production Docker: `docker-compose.prod.yml` + `.env.production.example`
- Архив для загрузки: `.\scripts\pack-for-server.ps1` → `repetcrm-deploy.zip`

```bash
cp .env.production.example .env.production
# отредактируйте SECRET_KEY, OPENROUTER_API_KEY, NEXT_PUBLIC_API_URL, CORS_ORIGINS
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

## Docker (разработка)

```bash
docker compose up --build -d
```

Модель `qwen2.5:3b` подтягивается автоматически сервисом `ollama-pull`.

| Сервис   | URL                    |
|----------|------------------------|
| Frontend | http://localhost:3000  |
| Backend  | http://localhost:8000  |
| Ollama   | http://localhost:11434 |

## Функционал CRM

- Регистрация / вход (JWT)
- Ученики: CRUD, карточки, история ДЗ
- Занятия: дата, оплата, чек-лист тем
- AI-домашки: Qwen2.5-Math (локально) / Ollama / шаблон → HTML → PDF
- Дашборд: ученики, уроки за месяц, оплаты, дебиторка

## API (основное)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/auth/register`, `/auth/login` | Аутентификация |
| GET/POST | `/students` | Ученики |
| GET/POST | `/lessons` | Занятия |
| POST | `/lessons/{id}/checklist` | Чек-лист |
| POST | `/lessons/{id}/generate-homework` | AI-генерация |
| PUT | `/homework/{id}` | Редактирование ДЗ |
| GET | `/homework/{id}/pdf` | Скачать PDF |

## Переменные окружения

См. `backend/.env.example` и `frontend/.env.local.example`.

## Технологии

- **Frontend:** Next.js 15, Tailwind, Heroicons
- **Backend:** FastAPI, SQLAlchemy, SQLite
- **AI:** Ollama (qwen2.5:7b)
- **PDF:** WeasyPrint
