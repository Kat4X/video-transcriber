# Video Transcriber - Руководство пользователя

## Содержание

- [Требования](#требования)
- [Установка](#установка)
- [CLI - Командная строка](#cli---командная-строка)
- [Web-интерфейс](#web-интерфейс)
- [Конфигурация](#конфигурация)
- [Примеры использования](#примеры-использования)
- [Устранение проблем](#устранение-проблем)

## Требования

### Системные требования

- **Python**: 3.9 или выше
- **FFmpeg**: для извлечения аудио из видео
- **RAM**: минимум 10GB для модели large-v3 (рекомендуется 16GB)
- **Диск**: ~10GB для модели Whisper large-v3

### Установка FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
```bash
# Через Chocolatey
choco install ffmpeg

# Или скачать с https://ffmpeg.org/download.html
```

## Установка

### Из исходников

```bash
# Клонировать репозиторий
git clone https://github.com/yourusername/video-transcriber.git
cd video-transcriber

# Создать виртуальное окружение (рекомендуется)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows

# Установить пакет
pip install -e .

# Для разработки (с тестами)
pip install -e ".[dev]"
```

### Проверка установки

```bash
# Проверить CLI
transcribe --help

# Проверить FFmpeg
ffmpeg -version
```

## CLI - Командная строка

### Базовые команды

#### Транскрипция локального файла

```bash
# Базовое использование - создаст video.md рядом с видео
transcribe video.mp4

# С субтитрами SRT
transcribe video.mp4 --srt

# С таймкодами в markdown
transcribe video.mp4 --timestamps

# Комбинация опций
transcribe video.mp4 --srt --timestamps
```

#### Транскрипция YouTube

```bash
# По полной ссылке
transcribe https://www.youtube.com/watch?v=dQw4w9WgXcQ

# По короткой ссылке
transcribe https://youtu.be/dQw4w9WgXcQ

# С субтитрами
transcribe https://youtu.be/xxx --srt
```

#### Запуск веб-сервера

```bash
# На localhost:8000 (по умолчанию)
transcribe serve

# На другом порту
transcribe serve --port 8080

# На всех интерфейсах (доступ из сети)
transcribe serve --host 0.0.0.0 --port 8080
```

### Все опции CLI

| Опция | Короткая | Описание | По умолчанию |
|-------|----------|----------|--------------|
| `--output` | `-o` | Папка для результата | Рядом с видео |
| `--srt` | | Генерировать SRT субтитры | Нет |
| `--timestamps` | `-t` | Добавить таймкоды в markdown | Нет |
| `--lang` | `-l` | Язык (auto, ru, en) | auto |
| `--model` | `-m` | Модель Whisper | large-v3 |
| `--format` | `-f` | Форматировать через LLM | Нет |

### Примеры команд

```bash
# Русское видео с указанием языка (быстрее чем автодетект)
transcribe lecture.mp4 --lang ru

# Использовать меньшую модель (быстрее, меньше RAM)
transcribe video.mp4 --model medium

# Сохранить в другую папку
transcribe video.mp4 --output ~/transcriptions/

# Полный набор опций
transcribe video.mp4 \
    --srt \
    --timestamps \
    --lang ru \
    --model large-v3 \
    --output ./results/
```

## Web-интерфейс

### Запуск

```bash
transcribe serve
```

Откройте в браузере: http://localhost:8000

### Возможности

1. **Drag & Drop** - перетащите видеофайл в окно браузера
2. **YouTube URL** - вставьте ссылку и нажмите "Transcribe"
3. **Настройки** - выбор модели, языка, таймкодов
4. **Прогресс** - отображение в реальном времени
5. **Результат** - просмотр, копирование, скачивание
6. **История** - список всех транскрипций

### API Endpoints

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/` | Главная страница |
| POST | `/api/transcriptions` | Создать транскрипцию |
| GET | `/api/transcriptions` | Список транскрипций |
| GET | `/api/transcriptions/{id}` | Получить транскрипцию |
| GET | `/api/transcriptions/{id}/events` | SSE прогресс |
| GET | `/api/transcriptions/{id}/download` | Скачать файл |
| DELETE | `/api/transcriptions/{id}` | Удалить |

### Пример API запроса

```bash
# Транскрипция YouTube видео
curl -X POST http://localhost:8000/api/transcriptions \
    -F "youtube_url=https://youtu.be/xxx" \
    -F "language=auto" \
    -F "model=large-v3"

# Загрузка файла
curl -X POST http://localhost:8000/api/transcriptions \
    -F "file=@video.mp4" \
    -F "language=ru"

# Получить результат
curl http://localhost:8000/api/transcriptions/{id}

# Скачать markdown
curl -O http://localhost:8000/api/transcriptions/{id}/download?format=md
```

## Конфигурация

### Переменные окружения

Создайте файл `.env` в корне проекта или экспортируйте переменные:

```bash
# Whisper
TRANSCRIBER_WHISPER_MODEL=large-v3    # tiny, base, small, medium, large-v3
TRANSCRIBER_WHISPER_DEVICE=auto       # auto, cpu, cuda
TRANSCRIBER_WHISPER_COMPUTE_TYPE=auto # auto, int8, float16, float32

# Хранилище
TRANSCRIBER_DATA_DIR=~/.video-transcriber

# Сервер
TRANSCRIBER_HOST=127.0.0.1
TRANSCRIBER_PORT=8000

# LLM форматирование (опционально)
TRANSCRIBER_ANTHROPIC_API_KEY=sk-ant-...

# Лимиты
TRANSCRIBER_MAX_FILE_SIZE_GB=4.0
```

### Модели Whisper

| Модель | Размер | RAM | Скорость | Качество |
|--------|--------|-----|----------|----------|
| tiny | ~1GB | ~1GB | Очень быстро | Низкое |
| base | ~1GB | ~1GB | Быстро | Низкое |
| small | ~2GB | ~2GB | Умеренно | Среднее |
| medium | ~5GB | ~5GB | Медленно | Хорошее |
| large-v3 | ~10GB | ~10GB | Очень медленно | Отличное |

**Рекомендации:**
- Для быстрых тестов: `small`
- Для баланса качество/скорость: `medium`
- Для максимального качества: `large-v3`

### Структура данных

```
~/.video-transcriber/
├── transcriptions.db   # SQLite база данных
├── uploads/            # Загруженные файлы (временно)
└── temp/               # Временные файлы (аудио)
```

## Примеры использования

### Сценарий 1: Транскрипция лекции

```bash
# Русская лекция, нужны таймкоды для навигации
transcribe lecture.mp4 --lang ru --timestamps --srt

# Результат:
# lecture.md  - текст с таймкодами
# lecture.srt - субтитры для видеоплеера
```

### Сценарий 2: Конспект YouTube видео

```bash
# Скачать и транскрибировать
transcribe https://youtu.be/xxx --output ~/notes/

# С форматированием через Claude (нужен API ключ)
transcribe https://youtu.be/xxx --format
```

### Сценарий 3: Пакетная обработка

```bash
# Транскрибировать все видео в папке
for f in *.mp4; do
    transcribe "$f" --model medium
done
```

### Сценарий 4: Web-сервис для команды

```bash
# Запустить на сервере
TRANSCRIBER_HOST=0.0.0.0 transcribe serve --port 8080

# Теперь доступен по http://server-ip:8080
```

## Устранение проблем

### FFmpeg не найден

```
RuntimeError: FFmpeg is not installed or not in PATH
```

**Решение:** Установите FFmpeg (см. раздел Требования)

### Не хватает памяти

```
RuntimeError: CUDA out of memory / Killed
```

**Решение:** Используйте меньшую модель:
```bash
transcribe video.mp4 --model medium
# или
transcribe video.mp4 --model small
```

### Медленная транскрипция на CPU

На CPU модель large-v3 работает в 10-30 раз медленнее реального времени.

**Решение:**
- Используйте GPU если доступен
- Используйте меньшую модель: `--model medium` или `--model small`

### YouTube видео не скачивается

```
ERROR: Video unavailable
```

**Решение:**
- Проверьте URL
- Обновите yt-dlp: `pip install -U yt-dlp`
- Видео может быть приватным или заблокированным

### Ошибки кодировки

```
UnicodeDecodeError
```

**Решение:** Убедитесь что система поддерживает UTF-8:
```bash
export LANG=en_US.UTF-8
```

## Поддержка

- GitHub Issues: https://github.com/yourusername/video-transcriber/issues
- Документация API: http://localhost:8000/docs (при запущенном сервере)
