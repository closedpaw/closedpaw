# ClosedPaw

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000.svg?logo=next.js&logoColor=white)](https://nextjs.org/)

> **Zero-Trust AI Ассистент** — Безопасный, локальный ИИ с усиленной изоляцией

ClosedPaw — это AI-ассистент, ориентированный на приватность, который работает полностью на вашем локальном компьютере. В отличие от облачных решений, ваши данные никогда не покидают устройство. Построен на архитектуре security-first с использованием gVisor/Kata Containers для настоящей изоляции.

## 🚀 Быстрый старт

### Установка через npm (Рекомендуется)

```bash
npm install -g closedpaw
closedpaw install
```

### Установка одной командой (Альтернатива)

**Linux / macOS:**
```bash
curl -sSL https://raw.githubusercontent.com/logansin/closedpaw/main/installer/install.sh | bash
```

**Windows (PowerShell):**
```powershell
iwr -useb https://raw.githubusercontent.com/logansin/closedpaw/main/installer/install.ps1 | iex
```

### Ручная установка

```bash
# Клонировать репозиторий
git clone https://github.com/logansin/closedpaw.git
cd closedpaw

# Установить бэкенд
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Установить фронтенд
cd ../frontend
npm install

# Запустить сервисы
npm run dev  # Запускает бэкенд и фронтенд
```

## 🔒 Функции безопасности

- **Архитектура Zero-Trust** — Нет неявного доверия, все действия проверяются
- **Усиленная изоляция** — gVisor/Kata Containers (не просто Docker)
- **Защита от prompt injection** — Защита от атак типа CVE-2026-25253
- **Только локальная работа** — Ollama на 127.0.0.1, Web UI на localhost
- **Human-in-the-Loop** — Критические действия требуют подтверждения
- **Аудит логирования** — Все действия логируются для forensic анализа
- **Шифрованное хранилище** — API ключи шифруются при хранении

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────┐
│              ClosedPaw - Zero Trust                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Core      │  │   Agent     │  │   Human-in-the  │ │
│  │ Orchestrator│  │   Manager   │  │   Loop (HITL)   │ │
│  │  (FastAPI)  │  │ (gVisor/    │  │   Interface     │ │
│  │             │  │   Kata)     │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│           │              │                    │         │
│           ▼              ▼                    ▼         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Local     │  │   Cloud     │  │   Data Vault    │ │
│  │   LLM       │  │   LLM       │  │  (Encrypted)    │ │
│  │  Gateway    │  │   Proxy     │  │                 │ │
│  │  (Ollama)   │  │             │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 🛠️ Технологический стек

- **Бэкенд:** Python 3.11+, FastAPI, Pydantic AI
- **Фронтенд:** Next.js 15, React 19, Tailwind CSS
- **LLM:** Ollama (локально), OpenAI/Anthropic (опционально облако)
- **Изоляция:** gVisor, Kata Containers
- **Безопасность:** Cryptography, PyNaCl, Seccomp

## 📋 Требования

- Python 3.11+
- Node.js 20+
- Ollama
- gVisor или Kata Containers (для изоляции)

## 🤝 Участие в проекте

Мы приветствуем вклад! См. [CONTRIBUTING.md](CONTRIBUTING.md) для руководства.

## 📄 Лицензия

Этот проект лицензирован под MIT License — см. файл [LICENSE](LICENSE).

## 🙏 Благодарности

- Построен с учётом уроков анализа безопасности OpenClaw
- Вдохновлён необходимостью по-настоящему безопасных AI-ассистентов
- Проект с открытым исходным кодом, развиваемый сообществом

## ⚠️ Уведомление о безопасности

Этот проект ставит безопасность выше удобства. Некоторые функции могут требовать дополнительной настройки (например, установка gVisor/Kata) для обеспечения правильной изоляции. Никогда не отключайте функции безопасности ради удобства.

---

**Сделано с 🔒 командой ClosedPaw**