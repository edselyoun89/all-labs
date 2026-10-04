# Лабораторная работа №5 — вариант 24

GeoChat — многопользовательский TCP-чат с отправкой координат и поиском пользователей рядом.

## Запуск

В первом окне:

```powershell
python main.py server --host 127.0.0.1 --port 12345
```

В отдельных окнах:

```powershell
python main.py client --username Alice
python main.py client --username Bob
```

В GUI можно отправлять текст, координаты, открывать OpenStreetMap и искать пользователей в радиусе.

## Автоматическая проверка

```powershell
python integration_test.py
```

Тест проверяет подключение двух клиентов, обмен сообщениями, сохранение координат и поиск ближайших пользователей.
