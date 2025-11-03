import logging
from .base_llm import BaseLLM
from yandex_cloud_ml_sdk import YCloudML
from yandex_cloud_ml_sdk.auth import APIKeyAuth
import config

class YandexCloudLLM(BaseLLM):
    """Реализация для работы с LLM из Yandex Cloud."""

    def __init__(self, model_uri: str, temperature: float = 0.1):
        if not config.YC_FOLDER_ID or not config.YC_API_KEY:
            raise ValueError("YC_FOLDER_ID и YC_API_KEY должны быть установлены.")
            
        sdk = YCloudML(
            folder_id=config.YC_FOLDER_ID,
            auth=APIKeyAuth(config.YC_API_KEY)
        )
        self.model = sdk.models.completions(model_uri).configure(temperature=temperature)
        logging.info(f"Инициализирована модель LLM: {model_uri}")

    def correct_and_format(self, ocr_text: str, prompt_template: str) -> str:
        logging.info("Отправка текста в LLM для коррекции...")
        try:
            # Разделяем системный промпт и пользовательский контент
            if '{{OCR_TEXT}}' not in prompt_template:
                 raise ValueError("Промпт должен содержать маркер {{OCR_TEXT}}")
            
            parts = prompt_template.split('{{OCR_TEXT}}')
            system_prompt = parts[0]
            # Если после маркера есть еще текст, добавляем его к ocr_text
            user_content = ocr_text + parts[1]

            messages = [
                {"role": "system", "text": system_prompt.strip()},
                {"role": "user", "text": user_content.strip()}
            ]

            result = self.model.run(messages)
            
            corrected_text = result.alternatives[0].text
            logging.info("Текст успешно обработан LLM.")
            return corrected_text

        except Exception as e:
            logging.error(f"Ошибка при работе с Yandex Cloud LLM: {e}")
            return f"[ОШИБКА LLM: {e}]"
