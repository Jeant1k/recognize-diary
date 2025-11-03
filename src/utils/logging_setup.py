import logging
import sys

def setup_logging():
    """Настраивает логирование в файл и консоль."""
    log_file_path = config.LOG_FILE
    log_file_path.parent.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] - %(message)s",
        handlers=[
            logging.FileHandler(log_file_path, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Логирование настроено.")

from .. import config
