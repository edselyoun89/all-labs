# Лабораторная работа №6 — документы общего доступа

Совместный сетевой редактор документа с ролями и комментариями.

## Запуск

Сервер:

```powershell
python main.py server --port 12346
```

Клиенты в отдельных терминалах:

```powershell
python main.py client --username Admin
python main.py client --username Editor
python main.py client --username Viewer
```

Первый подключившийся пользователь получает роль `admin`. Администратор может назначать роли `editor`, `commenter` и `viewer`.

## Проверка

```powershell
python integration_test.py
```
