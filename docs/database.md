# Database

## Загальний опис

Проєкт використовує PostgreSQL у хмарному сервісі Neon.

Python-застосунок підключається до бази даних через SQLAlchemy у асинхронному режимі та драйвер `asyncpg`.

База даних потрібна для зберігання користувачів Telegram, категорій витрат і фінансових операцій.

Для першої версії проєкту використовуються три основні таблиці:

* `users`;
* `categories`;
* `transactions`.

## Таблиця `users`

Таблиця `users` зберігає інформацію про користувачів Telegram, які взаємодіють з ботом.

Основні поля:

* `id` — внутрішній унікальний ідентифікатор користувача у базі даних;
* `telegram_id` — унікальний ID користувача у Telegram;
* `username` — Telegram username користувача, якщо він доступний;
* `created_at` — дата і час створення запису.

Приклад структури:

```text
users
-----
id
telegram_id
username
created_at
```

Поле `telegram_id` повинно бути унікальним, тому що один Telegram-користувач повинен відповідати одному запису у таблиці `users`.

Один користувач може мати багато фінансових операцій.

## Таблиця `categories`

Таблиця `categories` зберігає категорії витрат.

Наприклад:

* їжа;
* транспорт;
* кава;
* покупки;
* розваги;
* інше.

Основні поля:

* `id` — унікальний ідентифікатор категорії;
* `name` — назва категорії;
* `created_at` — дата і час створення категорії.

Приклад структури:

```text
categories
----------
id
name
created_at
```

Поле `name` бажано зробити унікальним, щоб уникнути дублювання однакових категорій.

Одна категорія може використовуватися у багатьох транзакціях.

## Таблиця `transactions`

Таблиця `transactions` зберігає фінансові операції користувачів.

Для команди:

```text
/expense 120 кава
```

може бути створена транзакція із сумою `120` та описом `кава`.

Основні поля:

* `id` — унікальний ідентифікатор транзакції;
* `user_id` — ID користувача, якому належить транзакція;
* `category_id` — ID категорії транзакції;
* `amount` — сума операції;
* `description` — текстовий опис;
* `created_at` — дата і час створення операції.

Приклад структури:

```text
transactions
------------
id
user_id
category_id
amount
description
created_at
```

Для грошових значень бажано використовувати тип `NUMERIC` або `DECIMAL`, а не `float`, щоб уникнути похибок при роботі з фінансовими значеннями.

## Зв'язки між таблицями

Між таблицями існують такі основні зв'язки:

```text
users 1 -------- * transactions

categories 1 --- * transactions
```

Це означає:

* один користувач може мати багато транзакцій;
* кожна транзакція належить одному користувачу;
* одна категорія може використовуватися у багатьох транзакціях;
* одна транзакція може бути пов'язана з однією категорією.

## Foreign Keys

У таблиці `transactions` використовуються зовнішні ключі.

`user_id` посилається на:

```text
users.id
```

Тобто:

```text
transactions.user_id -> users.id
```

`category_id` посилається на:

```text
categories.id
```

Тобто:

```text
transactions.category_id -> categories.id
```

Ці зв'язки допомагають підтримувати цілісність даних.

## Спрощена схема бази даних

```text
+------------------+
|      users       |
+------------------+
| id               |
| telegram_id      |
| username         |
| created_at       |
+------------------+
         |
         | 1
         |
         | *
+------------------+
|   transactions   |
+------------------+
| id               |
| user_id          |
| category_id      |
| amount           |
| description      |
| created_at       |
+------------------+
         *
         |
         | 1
         |
+------------------+
|    categories    |
+------------------+
| id               |
| name             |
| created_at       |
+------------------+
```

## Приклад DBML для dbdiagram

Схему можна також описати у dbdiagram за допомогою DBML:

```text
Table users {
  id integer [primary key]
  telegram_id bigint [unique, not null]
  username varchar
  created_at timestamp
}

Table categories {
  id integer [primary key]
  name varchar [unique, not null]
  created_at timestamp
}

Table transactions {
  id integer [primary key]
  user_id integer [not null]
  category_id integer
  amount decimal [not null]
  description varchar
  created_at timestamp
}

Ref: transactions.user_id > users.id
Ref: transactions.category_id > categories.id
```

dbdiagram використовується лише для візуалізації та документування структури.

Він не є самою базою даних.

Реальна PostgreSQL-база знаходиться у Neon.

## Підключення до бази даних

Connection string зберігається у змінній:

```text
DATABASE_URL
```

Реальне значення `DATABASE_URL` знаходиться тільки у локальному `.env` і не повинно потрапляти до Git.

Для перевірки підключення застосунок виконує простий SQL-запит:

```sql
SELECT 1;
```

Якщо запит виконується успішно, це означає, що backend може встановити з'єднання з Neon PostgreSQL.
