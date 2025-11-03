import argparse
import logging
import itertools
from pathlib import Path

import config
from src.utils.logging_setup import setup_logging
from src.ocr.yandex_vision_ocr import YandexVisionOCR
from src.ocr.rehand_mock_ocr import RehandMockOCR
from src.llm.yandex_cloud_llm import YandexCloudLLM
from src.document_generator.word import create_word_document


def get_ocr_processor(tool_name: str):
    """Фабрика для создания OCR процессоров."""
    tool_config = config.OCR_TOOLS.get(tool_name)
    if not tool_config:
        raise ValueError(f"Неизвестный инструмент OCR: {tool_name}")
    
    if tool_config["type"] == "yandex":
        return YandexVisionOCR(processing_method=tool_config["method"])
    if tool_config["type"] == "rehand_mock":
        return RehandMockOCR()
    
    raise NotImplementedError(f"Тип OCR процессора не реализован: {tool_config['type']}")

def run_test_mode():
    """Запускает перебор всех комбинаций OCR, LLM и промптов на тестовых данных."""
    logging.info("--- Запуск в тестовом режиме ---")
    
    test_scans = sorted(list(config.TEST_SCANS_DIR.glob('*.jpg')), key=lambda p: int(p.stem))
    if not test_scans:
        logging.warning("Тестовые сканы не найдены. Проверьте директорию data/test_scans/")
        return

    config.TEST_OUTPUTS_DIR.mkdir(exist_ok=True)
    
    # Создаем все комбинации для перебора
    combinations = list(itertools.product(
        config.OCR_TOOLS.keys(),
        config.LLM_MODELS.keys(),
        config.PROMPTS.keys()
    ))
    
    logging.info(f"Всего сканов для теста: {len(test_scans)}")
    logging.info(f"Всего комбинаций для проверки: {len(combinations)}")
    
    for image_path in test_scans:
        page_num = image_path.stem
        logging.info(f"--- Обработка страницы {page_num} ---")
        
        # Для чистоты эксперимента, если rehand есть в комбинациях,
        # проверим наличие мок-файла заранее
        rehand_text_path = config.REHAND_MOCK_TEXTS_DIR / f"{page_num}.txt"
        if "rehand_mock" in config.OCR_TOOLS and not rehand_text_path.exists():
             logging.warning(f"Мок-файл {rehand_text_path} не найден, комбинации с rehand_mock будут пропущены для этой страницы.")
             
        for ocr_name, llm_name, prompt_name in combinations:
            
            if ocr_name == "rehand_mock" and not rehand_text_path.exists():
                continue

            current_combination = f"OCR: {ocr_name}, LLM: {llm_name}, Prompt: {prompt_name}"
            logging.info(f"Тестирование комбинации: {current_combination}")
            
            try:
                # 1. Распознавание текста (OCR)
                ocr_processor = get_ocr_processor(ocr_name)
                raw_text = ocr_processor.recognize(str(image_path))
                if not raw_text or raw_text.startswith("[ОШИБКА"):
                    logging.error(f"Не удалось распознать текст для {page_num}. Пропуск комбинации.")
                    continue

                # 2. Коррекция и форматирование (LLM)
                llm_processor = YandexCloudLLM(model_uri=config.LLM_MODELS[llm_name])
                prompt_template = config.PROMPTS[prompt_name]
                formatted_text = llm_processor.correct_and_format(raw_text, prompt_template)
                
                # 3. Сохранение результата
                output_filename = f"page_{page_num}__{ocr_name}__{llm_name}__{prompt_name}.md"
                output_path = config.TEST_OUTPUTS_DIR / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Результат для страницы {page_num}\n")
                    f.write(f"# Комбинация: {current_combination}\n\n")
                    f.write("--- СЫРОЙ ТЕКСТ OCR ---\n")
                    f.write(raw_text + "\n\n")
                    f.write("--- ОБРАБОТАННЫЙ ТЕКСТ LLM ---\n")
                    f.write(formatted_text)
                
                logging.info(f"Результат сохранен в {output_path}")

            except Exception as e:
                logging.error(f"Критическая ошибка при обработке комбинации {current_combination} для файла {image_path}: {e}", exc_info=True)


def run_production_mode():
    """Запускает обработку всех сканов с заранее выбранной лучшей конфигурацией."""
    logging.info("--- Запуск в рабочем режиме ---")
    
    prod_scans = sorted(list(config.PRODUCTION_SCANS_DIR.glob('*.jpg')), key=lambda p: int(p.stem))
    if not prod_scans:
        logging.error("Рабочие сканы не найдены! Проверьте директорию data/production_scans/")
        return
        
    logging.info(f"Найдено {len(prod_scans)} страниц для обработки.")
    logging.info(f"Используемая конфигурация: OCR={config.PRODUCTION_OCR_TOOL}, LLM={config.PRODUCTION_LLM_MODEL}, Prompt={config.PRODUCTION_PROMPT}")

    # Инициализируем процессоры один раз
    try:
        ocr_processor = get_ocr_processor(config.PRODUCTION_OCR_TOOL)
        llm_processor = YandexCloudLLM(model_uri=config.LLM_MODELS[config.PRODUCTION_LLM_MODEL])
        prompt_template = config.PROMPTS[config.PRODUCTION_PROMPT]
    except (ValueError, NotImplementedError) as e:
        logging.critical(f"Ошибка инициализации процессоров: {e}")
        return

    all_pages_markdown = []
    
    for i, image_path in enumerate(prod_scans):
        page_num = image_path.stem
        logging.info(f"Обработка страницы {i+1}/{len(prod_scans)} (файл: {image_path.name})...")
        
        try:
            raw_text = ocr_processor.recognize(str(image_path))
            if not raw_text or raw_text.startswith("[ОШИБКА"):
                logging.error(f"Не удалось распознать текст для {page_num}. Страница будет пропущена.")
                all_pages_markdown.append(f"#[ОШИБКА: Не удалось обработать страницу {page_num}]")
                continue

            formatted_text = llm_processor.correct_and_format(raw_text, prompt_template)
            all_pages_markdown.append(formatted_text)
            
        except Exception as e:
            logging.error(f"Критическая ошибка при обработке файла {image_path}: {e}", exc_info=True)
            all_pages_markdown.append(f"#[ОШИБКА: Не удалось обработать страницу {page_num} из-за внутренней ошибки]")

    # Собираем все в один Word файл
    output_docx_path = config.PRODUCTION_OUTPUT_DIR / "diary.docx"
    create_word_document(all_pages_markdown, output_docx_path)
    
    logging.info("--- Работа завершена ---")


if __name__ == "__main__":
    # Настройка парсера аргументов командной строки
    parser = argparse.ArgumentParser(description="Оцифровка рукописного дневника.")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["test", "production"],
        default="test",
        help="Режим работы: 'test' для перебора комбинаций, 'production' для финальной сборки."
    )
    args = parser.parse_args()

    # Настройка логирования
    setup_logging()

    # Запуск соответствующего режима
    if args.mode == "test":
        run_test_mode()
    elif args.mode == "production":
        run_production_mode()
