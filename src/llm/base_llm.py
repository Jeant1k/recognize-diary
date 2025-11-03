from abc import ABC, abstractmethod

class BaseLLM(ABC):
    """Абстрактный базовый класс для всех LLM."""

    @abstractmethod
    def correct_and_format(self, ocr_text: str, prompt_template: str) -> str:
        """
        Корректирует и форматирует текст, полученный от OCR.
        :param ocr_text: Сырой текст от OCR.
        :param prompt_template: Шаблон промпта с маркером {{OCR_TEXT}}.
        :return: Исправленный и отформатированный текст в Markdown.
        """
        pass
