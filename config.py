import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# --- Основные пути ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
LOGS_DIR = BASE_DIR / "logs"

# Пути к директориям с данными
TEST_SCANS_DIR = DATA_DIR / "test_scans"
PRODUCTION_SCANS_DIR = DATA_DIR / "production_scans"
REHAND_MOCK_TEXTS_DIR = DATA_DIR / "rehand_mock_texts"

# Пути к директориям с результатами
TEST_OUTPUTS_DIR = RESULTS_DIR / "test_outputs"
PRODUCTION_OUTPUT_DIR = RESULTS_DIR / "production_output"

# Файл логов
LOG_FILE = LOGS_DIR / "app.log"

# --- Настройки API ---
YC_API_KEY = os.getenv("YC_API_KEY")
YC_FOLDER_ID = os.getenv("YC_FOLDER_ID")

if not YC_API_KEY or not YC_FOLDER_ID:
    raise ValueError("Необходимо установить YC_API_KEY и YC_FOLDER_ID в .env файле")

# --- Настройки для ТЕСТОВОГО РЕЖИМА ---

# Определения OCR инструментов
OCR_TOOLS = {
    "yandex_vision_simple": {"type": "yandex", "method": "markdown"},
    "yandex_vision_bbox": {"type": "yandex", "method": "bbox"},
    "rehand_mock": {"type": "rehand_mock"}
}

# Определения LLM моделей (URI для Yandex Cloud)
LLM_MODELS = {
    "yandex_gpt_pro": f"gpt://{YC_FOLDER_ID}/yandexgpt/latest",
    "qwen3_235b": f"gpt://{YC_FOLDER_ID}/qwen3-235b-a22b-fp8/latest",
    "gpt_oss_120b": f"gpt://{YC_FOLDER_ID}/gpt-oss-120b/latest",
}

# Шаблоны промптов (вставьте сюда свои варианты)
# Маркер {{OCR_TEXT}} будет заменен на распознанный текст
PROMPTS = {
    "prompt_1": """
Ты — ассистент, который помогает оцифровывать рукописный дневник. 
Твоя задача — исправить ошибки распознавания (OCR) и восстановить форматирование. 
Сохраняй авторский стиль, не меняй формулировки, не додумывай. Текст написан женщиной в СССР (1991-1998).
- Сохраняй абзацы.
- Используй Markdown для форматирования.
- Иностранные фразы оставляй как есть.
- Не исправляй "ошибки" стиля, это полет мысли автора.
Вот текст после OCR:

{{OCR_TEXT}}
""",
    "prompt_2": """
# Инструкция для модели
Роль: Редактор-реставратор.
Цель: Преобразовать сырой текст из OCR в чистый и отформатированный Markdown, максимально сохраняя оригинал.
Контекст: Это личный дневник женщины, 1990-е годы. Стиль — размышления, возможны нелитературные обороты, смешение языков (русский, немецкий).
Правила:
1.  **Точность:** Не переписывай фразы. Исправляй только явные ошибки OCR (например, "гловарищей" -> "товарищей").
2.  **Форматирование:** Восстанови абзацы. Новые мысли или отступы в оригинале должны стать новыми абзацами.
3.  **Без творчества:** Никаких добавлений от себя. Если слово неразборчиво, лучше оставить его как есть или пометить.
4.  **Сохранение рода:** Автор — женщина. Если OCR ошибся в роде ("подвергалось" вместо "подвергалась"), исправь на женский.
5.  **Языки:** Не переводи иностранные вставки (например, "Geld macht frei!").

Оригинальный текст с ошибками OCR:
{{OCR_TEXT}}
""",
    # Добавьте prompt_3 и prompt_4 по аналогии
    "prompt_3": "Вставьте сюда текст третьего промпта. {{OCR_TEXT}}",
    "prompt_4": "Вставьте сюда текст четвертого промпта. {{OCR_TEXT}}",
}

# --- Настройки для РАБОЧЕГО РЕЖИМА ---
# Выберите лучшую комбинацию после тестов
PRODUCTION_OCR_TOOL = "yandex_vision_bbox" # Например, "yandex_vision_bbox"
PRODUCTION_LLM_MODEL = "qwen3_235b"        # Например, "qwen3_235b"
PRODUCTION_PROMPT = "prompt_2"             # Например, "prompt_2"
