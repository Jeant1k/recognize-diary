import os
import re
import base64
import requests
import time
from docx import Document
from docx.shared import Pt, Inches
from dotenv import load_dotenv
import openai

# --- КОНФИГУРАЦИЯ ---

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем конфигурацию из переменных окружения
CONFIG = {
    "API_KEY": os.getenv("YC_API_KEY"),
    "FOLDER_ID": os.getenv("YC_FOLDER_ID"),
    "IMAGE_DIR": "scans_for_test",
    "OUTPUT_DOCX_NAME": "diary.docx",
    "GPT_MODEL_URI": "gpt://{folder_id}/qwen3-235b-a22b-fp8/latest",
    "OPENAI_BASE_URL": "https://llm.api.cloud.yandex.net/v1",
    "DEBUG": os.getenv("DEBUG_MODE", "false").lower() in ('true', '1', 't', 'yes'),
    "DEBUG_DIR": "debug_output"
}

# --- ПРОМПТ ДЛЯ LLM ---
# Это самый важный компонент для сохранения аутентичности текста
SYSTEM_PROMPT = """
Ты — опытный ассистент-реставратор. Твоя задача — обработать сырой текст, полученный после автоматического распознавания (OCR) рукописного советского дневника. Текст имеет огромную ценность. Твоя работа требует предельной аккуратности и понимания контекста.

**Главная цель:** Максимально точно восстановить исходный авторский текст, исправляя только и исключительно артефакты и ошибки OCR, и отформатировать его в Markdown.

**Автор дневника — женщина.** Это важно для правильного выбора окончаний глаголов в прошедшем времени (например, "я ходила", а не "я ходил"), если OCR не распознал их корректно.

**Иерархия правил:**

**Уровень 1: Категорически Запрещено (Сохранение Авторского Стиля):**
1.  **Не перефразируй и не "улучшай" текст.** Сохраняй все авторские формулировки, порядок слов и стиль "потока сознания". Если написано "пошли мы гуляти", оставляй "пошли мы гуляти".
2.  **Не исправляй грамматику и орфографию автора.** Устаревшие нормы, диалектизмы, авторские сокращения или ошибки — это часть исторической ценности. Не трогай их.
3.  **Не додумывай смысл.** Если часть текста нечитаема или отсутствует, не пытайся её восстановить по смыслу. Оставляй как есть (например, "пр#шлось" или "непонятное слово").

**Уровень 2: Разрешенная Реставрация (Исправление Ошибок OCR):**
Это единственные изменения, которые ты можешь и должен вносить.
1.  **Соединяй разорванные слова:** OCR часто рвет слова на части (например, "сло во", "пере живание"). Аккуратно соединяй их в "слово", "переживание".
2.  **Исправляй очевидные опечатки OCR:** Если из контекста на 99% ясно, что OCR допустил ошибку, исправь её.
    *   Пример: "уднать правду" → "узнать правду".
    *   Пример: "в 80% меня попросили" → "в 80-х меня попросили".
3.  **Восстанавливай обрезанные слова:** OCR может не распознать конец слова из-за переноса строки.
    *   Пример: "перед подписанием союзного договоро-" → "перед подписанием союзного договора".
4.  **Учитывай пол автора:** Если глагол в прошедшем времени распознан неоднозначно (например, "я подвергался"), используй женский род ("я подвергалась").

**Уровень 3: Структурирование и Форматирование:**
1.  **Абзацы:** Группируй предложения в логические абзацы, как это принято в дневниках. Не создавай новый абзац для каждого предложения. Старайся следовать оригинальной структуре, если она угадывается.
2.  **Даты и подписи:** Даты (например, "21 июня 91 г.") — это часть текста, обычно в конце или начале записи. **Не делай их заголовками!** Оставляй их как обычный текст в конце или начале абзаца отдельной строкой.
3.  **Заголовки:** Используй заголовки Markdown (`##`) только для очень явных названий глав или разделов, если они есть. В 99% случаев в дневнике их не будет.
4.  **Цитаты:** Иностранные цитаты или выделенные фразы оформляй как цитаты Markdown (`> `).
5.  **Вывод — только Markdown.** Никаких комментариев от тебя.

---
**Пример выполнения задачи:**

**Входной сырой текст:**
"Надо было уднать правду. Прошло не так уж много времени с тех пор, и вот сейчас, в предрыноч- ные времена, когда столько идеалов поломалось в нас, я с ужасом вспоминаю мое искреннее негодование и отчаяние. И мы веруем! Мы привыкли веровать! я не о том, что подвергаю сомнению новые ценности. я о том, что я снова подвергался. 21июня91 г."

**Твой идеальный результат (вывод в Markdown):**
Прошло не так уж много времени с тех пор, и вот сейчас, в "предрыночные" времена, когда столько идеалов поломалось в нас, я с ужасом вспоминаю мое искреннее негодование и отчаяние. И мы веруем! Мы привыкли веровать!

Я не о том, что подвергаю сомнению новые ценности. Я о том, что я снова подвергалась.

Надо было узнать правду.

21 июня 91 г.
"""

def check_config():
    """Проверяет наличие необходимых ключей в конфигурации."""
    if not CONFIG["API_KEY"] or not CONFIG["FOLDER_ID"]:
        print("!!! ОШИБКА: Не найдены YC_API_KEY или YC_FOLDER_ID.")
        print("!!! Пожалуйста, создайте файл .env и заполните его по инструкции.")
        return False
    if not os.path.isdir(CONFIG["IMAGE_DIR"]):
        print(f"!!! ОШИБКА: Папка '{CONFIG['IMAGE_DIR']}' не найдена.")
        print("!!! Пожалуйста, создайте ее и поместите туда файлы сканов.")
        return False
    return True

def natural_sort_key(s: str) -> list:
    """Ключ для "естественной" сортировки строк типа '10.jpg' > '2.jpg'."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def encode_image_to_base64(filepath: str) -> str:
    """Кодирует файл изображения в строку Base64."""
    with open(filepath, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_raw_text_from_ocr(base64_content: str) -> str | None:
    """Отправляет изображение в Yandex Vision OCR и возвращает сырой текст."""
    url = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {CONFIG['API_KEY']}",
        "x-folder-id": CONFIG["FOLDER_ID"],
    }
    body = {
        "mimeType": "JPEG",
        "languageCodes": ["ru", "en", "de"],
        "model": "handwritten",
        "content": base64_content
    }

    try:
        response = requests.post(url, headers=headers, json=body, timeout=180)
        response.raise_for_status()
        result = response.json()
        full_text = result.get('result', {}).get('textAnnotation', {}).get('fullText', '')
        return full_text
    except requests.exceptions.HTTPError as e:
        print(f"  [Ошибка OCR] HTTP-ошибка: {e.response.status_code}. Ответ: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [Ошибка OCR] Не удалось подключиться к серверу OCR: {e}")
        return None

def format_text_with_gpt(raw_text: str) -> str | None:
    """
    Отправляет сырой текст в LLM через OpenAI-совместимый API Yandex.Cloud
    для форматирования.
    """
    print(f"    - Инициализация клиента OpenAI для эндпоинта Yandex.Cloud...")
    try:
        client = openai.OpenAI(
            api_key=CONFIG["API_KEY"],
            base_url=CONFIG["OPENAI_BASE_URL"],
            project=CONFIG["FOLDER_ID"]
        )

        model_uri = CONFIG["GPT_MODEL_URI"].format(folder_id=CONFIG["FOLDER_ID"])
        print(f"    - Отправка запроса к модели: {model_uri}")
        
        response = client.chat.completions.create(
            model=model_uri,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.0,
            max_tokens=8000,
            stream=False
        )
        
        formatted_text = response.choices[0].message.content
        return formatted_text

    except openai.APIError as e:
        print(f"  [Ошибка GPT/API] Сервер вернул ошибку: {e.__class__.__name__} - {e}")
        return None
    except Exception as e:
        print(f"  [Ошибка GPT/Клиент] Произошла непредвиденная ошибка: {e.__class__.__name__} - {e}")
        return None

def add_markdown_to_document(doc: Document, markdown_text: str):
    """Парсит Markdown и добавляет форматированный текст в Word документ."""
    for line in markdown_text.split('\n'):
        line_stripped = line.strip()
        if not line_stripped:
            doc.add_paragraph()
            continue
        
        if line.startswith('## '):
            doc.add_heading(line.lstrip('## ').strip(), level=2)
        elif line.startswith('# '):
            doc.add_heading(line.lstrip('# ').strip(), level=1)
        elif line.startswith('> '):
            p = doc.add_paragraph(style='Intense Quote')
            p.add_run(line.lstrip('> ').strip())
        else:
            doc.add_paragraph(line)

def main():
    if not check_config():
        return
    
    if CONFIG["DEBUG"]:
        os.makedirs(CONFIG["DEBUG_DIR"], exist_ok=True)
        print("-" * 40)
        print(f"*** РЕЖИМ ОТЛАДКИ ВКЛЮЧЕН. Сырые OCR тексты будут сохранены в папку '{CONFIG['DEBUG_DIR']}'. ***")
        print("-" * 40)

    image_files = [f for f in os.listdir(CONFIG["IMAGE_DIR"]) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    image_files.sort(key=natural_sort_key)
        
    if not image_files:
        print(f"!!! ОШИБКА: В папке '{CONFIG['IMAGE_DIR']}' не найдено файлов изображений (jpg, jpeg, png).")
        return

    print(f"Найдено {len(image_files)} страниц. Начинаю обработку...")
    model_display_name = CONFIG['GPT_MODEL_URI'].split('/')[-2]
    print(f"Модель для форматирования: {model_display_name}")

    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)

    total_files = len(image_files)
    start_time = time.time()

    for i, filename in enumerate(image_files, 1):
        page_number_match = re.search(r'(\d+)', os.path.splitext(filename)[0])
        page_label = page_number_match.group(1) if page_number_match else filename

        print(f"\n[{i}/{total_files}] Обработка страницы: {filename}")
        doc.add_heading(f'Страница {page_label}', level=1)
        filepath = os.path.join(CONFIG["IMAGE_DIR"], filename)
        
        print("  -> Шаг 1: Распознавание рукописного текста (OCR)...")
        base64_content = encode_image_to_base64(filepath)
        raw_text = get_raw_text_from_ocr(base64_content)

        if CONFIG["DEBUG"] and raw_text and raw_text.strip():
            debug_filename = f"raw_{page_label}.txt"
            debug_filepath = os.path.join(CONFIG["DEBUG_DIR"], debug_filename)
            try:
                with open(debug_filepath, 'w', encoding='utf-8') as f:
                    f.write(raw_text)
                print(f"    - [DEBUG] Сырой текст сохранен в: {debug_filepath}")
            except IOError as e:
                print(f"    - [DEBUG ОШИБКА] Не удалось сохранить сырой текст: {e}")
        
        if not raw_text or not raw_text.strip():
            print("  [Предупреждение] Текст на странице не найден или пуст.")
            p = doc.add_paragraph()
            p.add_run("[На этой странице текст не найден]").italic = True
            if i < total_files: doc.add_page_break()
            continue

        print(f"  -> Шаг 2: Реставрация и форматирование текста ({len(raw_text)} симв.)...")
        formatted_text = format_text_with_gpt(raw_text)

        if formatted_text:
            print("  -> Шаг 3: Добавление в Word документ...")
            add_markdown_to_document(doc, formatted_text)
        else:
            print("  [ПРЕДУПРЕЖДЕНИЕ] Не удалось отформатировать текст. Вставляю сырой результат OCR.")
            doc.add_heading("Сырой текст с OCR (форматирование не удалось)", level=3)
            p = doc.add_paragraph()
            p.add_run(raw_text).italic = True
        
        if i < total_files:
            doc.add_page_break()

    print("-" * 40)
    print("💾 Сохранение итогового файла...")
    try:
        doc.save(CONFIG["OUTPUT_DOCX_NAME"])
        end_time = time.time()
        total_time = end_time - start_time
        print("-" * 40)
        print("🎉 Обработка завершена!")
        print(f"Итоговый файл сохранен как: {CONFIG['OUTPUT_DOCX_NAME']}")
        print(f"Затраченное время: {total_time:.2f} секунд ({total_time/60:.2f} минут).")
    except Exception as e:
        print(f"!!! ОШИБКА при сохранении файла: {e}")
        print(f"!!! Возможно, файл {CONFIG['OUTPUT_DOCX_NAME']} открыт в другой программе. Закройте его и попробуйте снова.")


if __name__ == '__main__':
    main()
