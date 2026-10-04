# Лабораторная работа №7 — парсинг сайтов

Приложение извлекает заголовок, headings, абзацы и ссылки HTML по параметрам `--keyword`, `--tag` и `--limit`. Результат сохраняется в JSON, CSV и HTML. Опционально он публикуется в общий документ LR_6.

## Запуск

```powershell
python main.py https://example.com --tag all --limit 50
python main.py https://example.com --keyword example --tag paragraphs
python main.py https://example.com --shared-host 127.0.0.1 --shared-port 12346 --username Admin
```

Для публикации сначала запустите сервер LR_6:

```powershell
python ..\Lab_06_variant_24\main.py server --port 12346
```

## Проверка

```powershell
python integration_test.py
```
