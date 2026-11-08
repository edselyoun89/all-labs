# All labs

Единый репозиторий учебных лабораторных работ. Репозиторий рассчитан на перенос между Windows, macOS и Linux: после клонирования нужно установить только инструменты, которые требуются выбранной лабораторной работе.

Репозиторий: <https://github.com/edselyoun89/all-labs>

## Содержание

| Каталог | Что внутри | Статус запуска |
|---|---|---|
| [`OIM/`](./OIM/) | Обработка изображений и мультимедиа: методички, MATLAB-код, Python-альтернатива, данные и результаты | ЛР1-4 имеют MATLAB-код и Python-альтернативу; ЛР5-8 представлены методическими материалами и исходными данными |
| [`PRV/`](./PRV/) | Параллельное программирование: ЛР1-2 — вариант 22; исходные работы варианта 24 | ЛР1-7, отчёты Word/PDF и памятки для защиты |
| [`RSP/`](./RSP/) | Разработка серверных приложений, вариант 18 | ЛР1-2 - проектная документация, ЛР3 - Python API, ЛР4 - Docker |

В репозитории есть исходники, отчёты, графики, таблицы результатов, изображения, PDF-методички и документы с заданиями. Локальные кэши, `.env`, логи и каталоги `__pycache__` в Git не включаются.

## 1. Как правильно клонировать репозиторий

### Windows, macOS и Linux

Установите Git, затем выполните:

```bash
git clone https://github.com/edselyoun89/all-labs.git
cd all-labs
git pull --ff-only origin main
```

Проверить, что используется правильная ветка и удалённый репозиторий:

```bash
git branch --show-current
git remote -v
git status
```

Ожидается ветка `main`, remote `origin` с адресом `https://github.com/edselyoun89/all-labs.git` и чистое состояние рабочей копии.

Не запускайте команды Git из `OIM`, `PRV` или `RSP`: это каталоги лабораторных. Git-репозиторий находится в корне `all-labs`.

### Если нужен только просмотр

Для чтения отчётов и методичек достаточно клонирования. PDF и DOC/DOCX открываются обычным просмотрщиком PDF и Word/LibreOffice. Для диаграмм Mermaid можно открыть файлы `.mmd` на GitHub или вставить их в Mermaid Live Editor.

## 2. Общая настройка Python

Для Python-лабораторных рекомендуется отдельное виртуальное окружение в корне проекта. Оно не смешивает зависимости этого репозитория с глобальными пакетами.

### Windows PowerShell

```powershell
py -3 -m venv .venv
Set-ExecutionPolicy -Scope Process Bypass
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Если команда `py` отсутствует, используйте `python -m venv .venv` после установки Python 3.10 или новее.

### macOS и Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

После активации во всех командах ниже используется `python`. Если виртуальное окружение не активировано, заменяйте `python` на `python3` на macOS/Linux или на `py -3` в Windows.

Проверка выбранного интерпретатора:

```bash
python --version
python -c "import sys; print(sys.executable)"
```

## 3. Зависимости

### Базовые Python-пакеты для OIM ЛР1-4

```bash
python -m pip install numpy Pillow scipy scikit-image matplotlib
```

### Пакеты для PRV

```bash
python -m pip install numpy mpi4py numba matplotlib
```

ЛР2, ЛР3 и ЛР5-7 используют стандартную библиотеку Python, но для построения графиков в ЛР2-4 нужен `matplotlib`. Повторная установка уже установленного пакета безопасна.

### Проверка Tkinter для PRV ЛР5-6

ЛР5 и ЛР6 используют графический интерфейс Tkinter. Проверьте его до запуска GUI:

```bash
python -c "import tkinter; print('Tkinter: OK')"
```

На Windows обычно достаточно Python с официального установщика. На Linux установите пакет Tkinter средствами дистрибутива, например `sudo apt install python3-tk`. На macOS используйте Python с Tk-поддержкой; если проверка не проходит, переустановите Python с официального установщика python.org или установите соответствующий пакет Tk для используемого менеджера пакетов.

## 4. MPI на разных системах

MPI нужен для `PRV/Lab_01_variant_22`, сохранённой `PRV/Lab_01_variant_24` и `PRV/Lab_04_variant_24`.

### Windows

Установите Microsoft MPI Runtime и Microsoft MPI SDK. После установки обычно доступен файл:

```text
C:\Program Files\Microsoft MPI\Bin\mpiexec.exe
```

Проверка:

```powershell
mpiexec.exe -help
```

Если `mpiexec.exe` не находится через `PATH`, задайте путь для текущего сеанса PowerShell:

```powershell
$env:MPIEXEC = 'C:\Program Files\Microsoft MPI\Bin\mpiexec.exe'
```

### macOS

Установите Homebrew, если его ещё нет, затем Open MPI:

```bash
brew install open-mpi
export MPIEXEC="$(command -v mpiexec)"
mpiexec --version
```

После этого переустановите `mpi4py` внутри активного `.venv`, если он устанавливался до появления MPI:

```bash
python -m pip install --force-reinstall mpi4py
```

### Linux

Для Debian/Ubuntu:

```bash
sudo apt update
sudo apt install openmpi-bin libopenmpi-dev
export MPIEXEC="$(command -v mpiexec)"
mpiexec --version
```

В других дистрибутивах установите пакет Open MPI средствами своего пакетного менеджера. В средах без графического интерфейса MPI-лабораторные запускаются, но GUI-лабораторные PRV ЛР5-6 потребуют отдельного рабочего стола или виртуального дисплея.

## 5. OIM - обработка изображений и мультимедиа

### Что есть в каталоге

- `OIM/completed labs/Lab_01` - матрицы и автоматическая настройка контраста.
- `OIM/completed labs/Lab_02` - фрагменты изображения, гистограммы, эквализация и спецификация.
- `OIM/completed labs/Lab_03` - точечные преобразования и пространственная фильтрация.
- `OIM/completed labs/Lab_04` - карты границ, пороговая обработка и преобразование Хафа.
- `OIM/Лабораторная работа #1...#4` - исходные MATLAB-методички, изображения и MATLAB-файлы.
- `OIM/Лабораторная работа #5...#8` - методички и исходные материалы по ImageMagick/FFmpeg, CorelDraw и Blender.
- `OIM/completed labs/run_all.m` - запуск MATLAB-частей первых четырёх работ.
- `OIM/completed labs/run_all_python.py` - запуск Python-альтернативы первых четырёх работ без MATLAB.

### Вариант без MATLAB

После установки Python-пакетов выполните из корня репозитория:

```bash
cd "OIM/completed labs"
python run_all_python.py
```

Результаты появятся в каталогах `Lab_01/results_python` ... `Lab_04/results_python`.

Скрипт использует NumPy, Pillow, SciPy и scikit-image. В старой локальной версии README встречалась ссылка на `tmp/oim/deps`; этот путь относится к кэшу конкретного компьютера и после клонирования отсутствует. На новом компьютере используйте виртуальное окружение и установку пакетов выше.

### Вариант с MATLAB

Нужны MATLAB и Image Processing Toolbox. Из каталога `OIM/completed labs` запустите MATLAB и выполните:

```matlab
run('run_all.m')
```

Или, в MATLAB достаточно новых версий, из терминала:

```bash
matlab -batch "run('run_all.m')"
```

MATLAB-скрипты создают результаты в `Lab_01/results_matlab` ... `Lab_04/results_matlab`. Python-результаты и MATLAB-результаты являются альтернативными запусками: численные и визуальные детали могут отличаться, особенно в ЛР4, где Python использует аналоги Canny, zero-crossing, Otsu и probabilistic Hough transform.

### OIM ЛР5-8

В репозитории сохранены задания и исходные материалы, но отдельного запускаемого `run_all` для этих работ нет:

| Работа | Требуемый инструмент по методичке | Что проверить на новом компьютере |
|---|---|---|
| ЛР5 | ImageMagick, RAW-файл `sunset.cr2` | `magick -version` |
| ЛР6 | SVG, ImageMagick и FFmpeg | `magick -version`, `ffmpeg -version` |
| ЛР7 | CorelDraw | наличие CorelDraw или согласованного аналога |
| ЛР8 | Blender, моделирование и симуляция | `blender --version` |

Это материалы для ручного выполнения по методичке, а не готовые кроссплатформенные программы. Для ЛР5-6 команды ImageMagick/FFmpeg зависят от конкретного входного файла и сохраняются в отчёте самой работы. Для ЛР7-8 результаты требуют GUI-приложений; на macOS и Linux совместимость CorelDraw нужно проверять отдельно, а Blender является кроссплатформенным.

## 6. PRV — лабораторные работы и защита

Первые две работы переделаны под **вариант 22**. Подробная навигация находится в [PRV/README.md](PRV/README.md), разбор всех семи тем — в [анализе лабораторных](PRV/analysis/Анализ_лабораторных.md). В каждой папке `Lab_*` есть `Защита_лабораторной.txt`: что сказать, как запустить, что показать, как объяснить алгоритм, результаты и ограничения, ответы на вопросы преподавателя.

Перед запуском активируйте `.venv`, установите зависимости и переходите в каталог выбранной работы. Локальная среда `.venv312` в Git не включена; в клоне используйте свою подготовленную среду.

### ЛР1, вариант 22 — метод Якоби, MPI + OpenMP

СЛАУ размера N=2000, ровно 100 итераций, p=1,2,4,8, по три повтора. Два OpenMP-потока на процесс, проверенный backend `omp`, сравнение решения и невязки, исследование масштабируемости.

```bash
cd PRV/Lab_01_variant_22
mpiexec -n 4 python main.py --n 2000 --iterations 100 --repeats 3
python run_experiments.py
```

[Отчёт Word](PRV/Lab_01_variant_22/report.docx), [PDF](PRV/Lab_01_variant_22/report.pdf), [памятка для защиты](PRV/Lab_01_variant_22/Защита_лабораторной.txt). Титульные поля студента и преподавателя оставлены для заполнения. Измерения и графики находятся в той же папке.

### ЛР2, вариант 22 — очередь с приоритетами

Пять производителей, десять потребителей, HIGH/MEDIUM/LOW, собственная очередь с `Condition`, измерения ожидания, обработки и полного отклика.

```bash
cd PRV/Lab_02_variant_22
python -m unittest -v test_priority_queue.py
python main.py --benchmark
python plot_graphs.py
```

[Отчёт Word](PRV/Lab_02_variant_22/report.docx), [PDF](PRV/Lab_02_variant_22/report.pdf), [памятка для защиты](PRV/Lab_02_variant_22/Защита_лабораторной.txt). Первые две папки варианта 24 ниже сохранены как исходные версии.

### Сохранённая ЛР1, вариант 24 — определитель матрицы

MPI распределяет строки, Numba `prange` распараллеливает исключение метода Гаусса. В исходной реализации подтверждена ошибка полного выбора ведущего элемента; границы корректности описаны в памятке и общем анализе.

```bash
cd PRV/Lab_01_variant_24
mpiexec -n 4 python main.py --n 1000 --repeats 3
python run_experiments.py
python plot_graphs.py
```

Допустимое число процессов для этой реализации: `1`, `2`, `4` или `8`. `run_experiments.py` использует переменную `MPIEXEC`, если она задана, и создаёт `results.csv`, `scalability.csv` и графики. Для Windows перед запуском задайте `$env:MPIEXEC`, для macOS/Linux - `export MPIEXEC=...`.

### Сохранённая ЛР2, вариант 24 — потоки и отложенный таймер

Реализованы `threading.Timer`, планировщик задач, отмена последней задачи, логирование и измерение точности выполнения.

```bash
cd PRV/Lab_02_variant_24
python main.py --single
python main.py
python plot_graphs.py
```

Полный benchmark создаёт задачи с задержками от 1 до 10 секунд и несколько серий фоновой нагрузки. Результаты находятся в `results/results.csv`, `results/summary.csv`, `results/logs.log` и PNG-графиках. Файл `logs.log` является локальным результатом и исключён из Git.

### ЛР3 - процессы и поиск в базе данных

Используется `multiprocessing.Pool`: программа создаёт базу из 10 000 записей и сравнивает последовательный поиск с параллельным.

```bash
cd PRV/Lab_03_variant_24
python main.py --single
python main.py
python plot_graphs.py
```

Полный запуск строит серии по числу запросов и процессов `1`, `2`, `4`, `8`; результаты записываются в `results/results.csv` и `results/process_scaling.csv`.

### ЛР4 - MPI и кратчайшие пути

Сравниваются три подхода: явные `Send/Recv`, коллективные операции `Bcast/Reduce` и декартова топология с обменом соседей. Используются Дейкстра и Флойд-Уоршелл.

```bash
cd PRV/Lab_04_variant_24
mpiexec -n 4 python main.py --n 128
python run_experiments.py
python plot_graphs.py
```

Основные данные сохраняются в `results/results.csv`, а служебные логи - в `results/logs.log`.

### ЛР5 - GeoChat

Многопользовательский TCP-чат с GUI на Tkinter: текстовые сообщения, координаты, карта OpenStreetMap и поиск ближайших пользователей.

В первом терминале:

```bash
cd PRV/Lab_05_variant_24
python main.py server --host 127.0.0.1 --port 12345
```

Во втором и третьем терминале:

```bash
cd PRV/Lab_05_variant_24
python main.py client --host 127.0.0.1 --port 12345 --username Alice
python main.py client --host 127.0.0.1 --port 12345 --username Bob
```

Автоматическая проверка без GUI:

```bash
python integration_test.py
```

Клиенту нужен доступ в интернет для открытия OpenStreetMap и поиска адресов. Если порт занят, выберите другой порт одинаково для сервера и клиентов.

### ЛР6 - документ общего доступа

Сетевой редактор документа с ролями `admin`, `editor`, `commenter` и `viewer`, комментариями, версиями и контролем прав.

В первом терминале:

```bash
cd PRV/Lab_06_variant_24
python main.py server --host 127.0.0.1 --port 12346
```

В отдельных терминалах:

```bash
cd PRV/Lab_06_variant_24
python main.py client --host 127.0.0.1 --port 12346 --username Admin
python main.py client --host 127.0.0.1 --port 12346 --username Editor
python main.py client --host 127.0.0.1 --port 12346 --username Viewer
```

Автоматическая проверка:

```bash
python integration_test.py
```

Первый подключившийся пользователь получает роль `admin` и может назначать роли другим пользователям.

### ЛР7 - парсинг сайтов

Парсер извлекает `title`, заголовки `h1-h4`, абзацы и ссылки, фильтрует их по ключевому слову и сохраняет JSON, CSV и HTML. Результат можно передать в сервер общего документа из ЛР6.

```bash
cd PRV/Lab_07_variant_24
python main.py https://example.com --tag all --limit 50
python main.py https://example.com --keyword example --tag paragraphs
python integration_test.py
```

Результаты появятся в `results/parsed_data.json`, `results/parsed_data.csv` и `results/parsed_data.html`.

Для публикации в ЛР6 сначала запустите сервер ЛР6 на порту `12346`, затем выполните:

```bash
python main.py https://example.com --shared-host 127.0.0.1 --shared-port 12346 --username Admin
```

Парсер поддерживает и локальный HTML-файл через URL вида `file:///absolute/path/page.html`. Для недоступных сайтов предусмотрено понятное сообщение об ошибке; интеграционный тест проверяет этот сценарий без обращения к внешнему сайту.

## 7. RSP - серверные приложения

### ЛР1 - архитектура и база данных

Каталог [`RSP/lab1/`](./RSP/lab1/) содержит Use Cases, C4 Container, ER-диаграмму Mermaid и PostgreSQL DDL `library_schema.sql`. Это проектная часть, готового сервера в ЛР1 нет.

При наличии PostgreSQL схему можно применить вручную:

```bash
createdb library
psql -d library -f RSP/lab1/library_schema.sql
```

### ЛР2 - REST API и OpenAPI

Каталог [`RSP/lab2/`](./RSP/lab2/) содержит контракт REST API электронной библиотеки и `openapi.yaml`. Это спецификация, а не запускаемый сервер. Файл можно открыть в Swagger Editor или Redocly.

### ЛР3 - запускаемый health-check API

ЛР3 использует только стандартную библиотеку Python 3.10+.

```bash
cd RSP/lab3
cp .env.example .env
python -m unittest discover -s tests -v
python -m app.main
```

Во втором терминале проверьте API:

```bash
curl http://127.0.0.1:8080/api/v1/health
```

Ожидается JSON со статусом `pass`, названием приложения, версией и окружением. На Windows используйте `curl.exe`, если PowerShell подменяет `curl` на `Invoke-WebRequest`. Остановка сервера: `Ctrl+C`.

`.env` создаётся локально из `.env.example` и не должен коммититься. Значения переменных окружения имеют приоритет над `.env`.

### ЛР4 - Docker

Dockerfile собирается из каталога `RSP`, а не из корня `all-labs`:

```bash
cd RSP
docker build -t rsp-library-api:lab4 .
docker run --name rsp-library-container -d -p 8080:8080 rsp-library-api:lab4
curl http://127.0.0.1:8080/api/v1/health
docker ps
docker inspect --format='{{json .State.Health}}' rsp-library-container
docker logs rsp-library-container
```

После проверки:

```bash
docker stop rsp-library-container
docker rm rsp-library-container
```

Образ использует Python 3.12 Slim, слушает `0.0.0.0:8080`, запускается от непривилегированного пользователя и имеет Docker `HEALTHCHECK`. Для Docker Desktop команды одинаковы на Windows и macOS; на Linux нужен установленный и запущенный Docker Engine.

## 8. Типичные проблемы

### `python` или `python3` не найден

Установите Python 3.10+ и повторно создайте `.venv`. После активации проверьте `python --version` и `python -c "import sys; print(sys.executable)"`.

### `ModuleNotFoundError`

Активируйте `.venv`, затем установите зависимости из раздела 3. Не копируйте каталог `tmp` с другого компьютера: он содержит локальный кэш и не входит в репозиторий.

### `mpiexec` не найден

Установите MPI runtime и SDK, проверьте `mpiexec --version`, затем задайте `MPIEXEC` для скриптов `run_experiments.py`. Вызов должен использовать тот же Python, где установлен `mpi4py`.

### Не запускается GUI Tkinter

Проверьте `python -c "import tkinter; print('Tkinter: OK')"`. На Linux добавьте пакет `python3-tk`; на macOS используйте Python с Tk-поддержкой. Запуск GUI в SSH-сессии без графического окружения не сработает.

### Порт уже занят

Выберите свободный порт параметром `--port` и укажите тот же порт всем клиентам. Для ЛР7 при публикации в ЛР6 должны совпадать `--shared-host` и `--shared-port` с адресом сервера ЛР6.

### Скрипт запущен из неправильного каталога

Переходите в каталог лабораторной перед запуском. Особенно важно: `RSP/lab3` нужен для `python -m app.main`, `RSP` нужен для `docker build`, а `OIM/completed labs` нужен для `run_all.m` и `run_all_python.py`.

## 9. Что не следует коммитить

Не добавляйте в Git:

- `.env` и реальные ключи/пароли;
- виртуальные окружения `.venv`, `venv`;
- `__pycache__`, `.pyc`, кэши IDE и пакетов;
- локальные логи `*.log`;
- большой каталог `tmp` с кэшем зависимостей.

Перед отправкой изменений:

```bash
git status
git add README.md
git commit -m "docs: add cross-platform setup guide"
git push origin main
```

После клонирования на другом компьютере достаточно снова выполнить `git pull --ff-only origin main`, активировать локальное виртуальное окружение и установить зависимости для нужной лабораторной работы.
