import logging
from pathlib import Path
from .base_ocr import BaseOCR
from .. import config

class RehandMockOCR(BaseOCR):
    """Мок-реализация для rehand.ru, читающая текст из файла."""

    def __init__(self):
        self.mock_dir = config.REHAND_MOCK_TEXTS_DIR
        if not self.mock_dir.exists():
            logging.warning(f"Директория для мок-файлов rehand.ru не найдена: {self.mock_dir}")

    def recognize(self, image_path: str) -> str:
        logging.info(f"Имитация распознавания (rehand.ru) для файла {image_path}...")
        try:
            image_name = Path(image_path).stem
            mock_file_path = self.mock_dir / f"{image_name}.txt"
            
            if not mock_file_path.exists():
                logging.error(f"Мок-файл не найден: {mock_file_path}")
                return f"[ОШИБКА: Мок-файл {mock_file_path} не найден]"

            with open(mock_file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            logging.error(f"Ошибка в RehandMockOCR: {e}")
            return f"[ОШИБКА: Не удалось прочитать мок-файл для {image_path}]"
