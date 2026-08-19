## VSCode

Статус: працює

Репозиторій відкритий у VSCode.

Команда:

git status

Результат:

Git бачить репозиторій і гілку environment/setup.

## AI-помічник

Інструмент: Codex Agent

Тест:

AI створив environment-check.md і не змінив інші файли.

## Docker

Команда:

docker --version

Тест:

docker run --rm -p 8080:80 nginx:alpine

Результат:

Контейнер запустився без помилок.

## Localhost

Адреса:

http://localhost:8080

Результат:

У браузері відкрилася сторінка nginx.

## Tunnel

Інструмент:

ngrok 

Команда:

ngrok http 8080

Результат:

Публічне посилання відкривається з іншого пристрою.
