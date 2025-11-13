import re
import difflib
from pathlib import Path

# --- КОНСТАНТЫ ---
# Определяем пути к файлам и директориям на основе структуры вашего проекта
BASE_DIR = Path(__file__).resolve().parent
IDEAL_FILE_PATH = BASE_DIR / ".." / "results" / "ideal_result" / "ideal.md"
TEST_OUTPUTS_DIR = BASE_DIR / ".." / "results" / "test_outputs"
RESULT_MARKER = "--- ОБРАБОТАННЫЙ ТЕКСТ LLM ---"

def extract_processed_text(filepath: Path) -> str | None:
    """
    Извлекает текст из файла результата, который находится после определенного маркера.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parts = content.split(RESULT_MARKER)
        if len(parts) > 1:
            return parts[1].strip()
        else:
            print(f"ПРЕДУПРЕЖДЕНИЕ: Маркер '{RESULT_MARKER}' не найден в файле {filepath.name}")
            return None
    except Exception as e:
        print(f"ОШИБКА: Не удалось прочитать файл {filepath.name}: {e}")
        return None

def normalize_text(text: str) -> str:
    """
    Приводит текст к единому виду для более точного сравнения.
    """
    # Удаляем возможные Markdown-блоки кода, которые иногда добавляют модели
    text = re.sub(r'```(?:markdown)?\s*(.*?)\s*```', r'\1', text, flags=re.DOTALL)
    # Заменяем множественные пробелы и переносы строк на один пробел
    text = re.sub(r'\s+', ' ', text)
    # Удаляем пробелы в начале и конце
    return text.strip()

def rank_results():
    """
    Основная функция для чтения, сравнения и ранжирования результатов.
    """
    if not IDEAL_FILE_PATH.exists():
        print(f"ОШИБКА: Эталонный файл не найден по пути: {IDEAL_FILE_PATH}")
        return

    if not TEST_OUTPUTS_DIR.exists():
        print(f"ОШИБКА: Директория с результатами тестов не найдена: {TEST_OUTPUTS_DIR}")
        return

    # 1. Загружаем и нормализуем эталонный текст
    with open(IDEAL_FILE_PATH, 'r', encoding='utf-8') as f:
        ideal_text_raw = f.read()
    
    # Для эталона используем более мягкую нормализацию, чтобы сохранить абзацы
    # так как они важны. Но удаляем ````.
    ideal_text_raw = re.sub(r'```(?:markdown)?\s*(.*?)\s*```', r'\1', ideal_text_raw, flags=re.DOTALL).strip()
    
    print(f"Эталонный файл '{IDEAL_FILE_PATH.name}' успешно загружен.")
    print("-" * 30)

    # 2. Собираем и оцениваем все файлы с результатами
    rankings = []
    result_files = list(TEST_OUTPUTS_DIR.glob("*.md"))

    if not result_files:
        print("ОШИБКА: В директории test_outputs не найдено .md файлов для анализа.")
        return

    for filepath in result_files:
        generated_text_raw = extract_processed_text(filepath)
        
        if generated_text_raw:
            # Для сравнения используем "жесткую" нормализацию без переносов строк,
            # чтобы мелкие различия в форматировании не влияли на оценку содержания.
            ideal_text_normalized = normalize_text(ideal_text_raw)
            generated_text_normalized = normalize_text(generated_text_raw)

            # 3. Вычисляем коэффициент схожести
            similarity_ratio = difflib.SequenceMatcher(
                None, ideal_text_normalized, generated_text_normalized
            ).ratio()
            
            rankings.append((similarity_ratio, filepath.name, generated_text_raw))

    # 4. Сортируем результаты по убыванию коэффициента схожести
    rankings.sort(key=lambda item: item[0], reverse=True)

    # 5. Выводим отсортированный список
    print("--- РЕЙТИНГ РЕЗУЛЬТАТОВ (от лучшего к худшему) ---\n")
    for i, (score, filename, _) in enumerate(rankings):
        print(f"{i+1:2}. Схожесть: {score:.2%} - Файл: {filename}")
    
    print("\n" + "="*50 + "\n")
    
    # 6. Выводим топ-3 результата для визуального сравнения
    print("--- СРАВНЕНИЕ ТОП-3 РЕЗУЛЬТАТОВ С ЭТАЛОНОМ ---\n")
    
    for i in range(min(3, len(rankings))):
        score, filename, text = rankings[i]
        print(f"--- {i+1}-е МЕСТО: {filename} (Схожесть: {score:.2%}) ---\n")
        print("--- ЭТАЛОН ---\n")
        print(ideal_text_raw)
        print("\n--- РЕЗУЛЬТАТ МОДЕЛИ ---\n")
        print(text)
        print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    rank_results()

