# AI SaaS Course

## Мета

Створити навчальний AI SaaS-проєкт та пройти основний цикл роботи з Git і GitHub.

## Цільовий користувач

Початківці, які хочуть навчитися створювати AI SaaS-застосунки та працювати з GitHub.

## Базові можливості

- робота з AI-функціями;
- створення SaaS-застосунку;
- робота з Git та GitHub;
- використання feature-гілок;
- створення Pull Request.

## Статус

Проєкт знаходиться на етапі розробки.

## Технології

- Git
- GitHub
- AI
- SaaS

## Навчальна ціль

Навчитися працювати з основним GitHub workflow.

## План розвитку

- додати AI-функції;
- створити користувацький інтерфейс;
- підключити SaaS-функціональність.

## Мінімальний Telegram-бот

Бот реалізований на aiogram 3.x у `app/main.py`. Він вітає користувача на
команду `/start` і показує коротку довідку на `/help`.

### Налаштування токена

1. Скопіюйте шаблон: `cp .env.example .env`.
2. Відкрийте локальний файл `.env` і вставте токен, отриманий від
   [@BotFather](https://t.me/BotFather), після знака `=`:

   ```env
   BOT_TOKEN=ваш_реальний_токен_від_BotFather
   ```

### Налаштування GEMINI API (LLM)

1. Скопіюйте шаблон: `cp .env.example .env`.
2. Додайте в локальний `.env` ключ `GEMINI_API_KEY`, отриманий у Google AI/Vertex:

```env
GEMINI_API_KEY=ваш_ключ_gemini
```

3. Не додавайте ключ в репозиторій — `.env` вже в `.gitignore`.

### Тестування AI-ендпойнта локально

Після запуску бекенду ви можете прогнати простий тест, що викликає AI-ендпойнт:

```bash
python3 scripts/test_llm_endpoint.py
```

Для CI або розробки краще використовувати мок-тісти (pytest) — в репозиторії є `tests/test_ai_endpoint.py` з прикладом мок-інструменту.

Не додавайте токен у код і не комітьте `.env`: він уже вказаний у `.gitignore`.

### Локальний запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/main.py
```

### AI Chat у React-адмінці

Чат доступний через `POST /api/ai/chat`. Передайте `message` і, для
продовження розмови, попередній `thread_id`. Відповідь містить `answer` та
`thread_id`. Історія діалогу зберігається у таблицях `chat_threads` і
`chat_messages`; перед першим запуском створіть таблиці:

```bash
python3 -m app.create_tables
uvicorn app.api:app --reload
cd frontend && npm install && npm run dev
```

Інструменти чату є тільки для читання: підсумок операцій, суми за категоріями
та найбільші витрати. Модель не отримує SQL, доступу до `.env` або можливості
змінювати операції.

Admin branch `saas/admin-management` provides a simple admin UI for creating and deleting transactions.

### Запуск у Docker з hot reload

Docker Compose передає `BOT_TOKEN` з локального `.env` у контейнер, але сам
файл не копіюється в образ. Compose Watch синхронізує зміни в `app/` та
автоматично перезапускає бота.

Після того як додасте `BOT_TOKEN` у `.env`, запустіть:

```bash
docker compose up --build --watch
```

Щоб зупинити бота, натисніть `Ctrl + C` у цьому терміналі.

## Debug / Troubleshooting

Якщо бот не запускається, перевірте:

1. Чи активне правильне Python-середовище.
2. Чи встановлені залежності:

```bash
python3 -m pip install -r requirements.txt

3. Чи є `BOT_TOKEN` у локальному `.env`.
4. Чи `.env` не потрапляє в Git.
5. Чи немає помилок у traceback.
