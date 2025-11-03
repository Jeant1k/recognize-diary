from abc import ABC, abstractmethod

class BaseOCR(ABC):
    """Абстрактный базовый класс для всех OCR процессоров."""

    @abstractmethod
    def recognize(self, image_path: str) -> str:
        """
        Распознает текст на изображении.
        :param image_path: Путь к файлу изображения.
        :return: Распознанный сырой текст.
        """
        pass
