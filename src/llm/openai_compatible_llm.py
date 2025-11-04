import logging
import openai
from .base_llm import BaseLLM
import config

class OpenAICompatibleLLM(BaseLLM):
    """Реализация для работы с LLM через OpenAI-совместимый API Yandex Cloud."""

    def __init__(self, model_uri: str, base_url: str, temperature: float = 0.1):
        if not config.YC_API_KEY or not config.YC_FOLDER_ID:
            raise ValueError("YC_API_KEY и YC_FOLDER_ID должны быть установлены.")
            
        self.client = openai.OpenAI(
            api_key=config.YC_API_KEY,
            base_url=base_url,
            project=config.YC_FOLDER_ID
        )
        self.model_uri = model_uri
        self.temperature = temperature
        logging.info(f"Инициализирован OpenAI-совместимый клиент для модели: {model_uri}")

    def correct_and_format(self, ocr_text: str, prompt_template: str) -> str:
        logging.info("Отправка текста в LLM (OpenAI-совместимый) для коррекции...")
        try:
            if '{{OCR_TEXT}}' not in prompt_template:
                 raise ValueError("Промпт должен содержать маркер {{OCR_TEXT}}")
            
            parts = prompt_template.split('{{OCR_TEXT}}')
            system_prompt = parts[0].strip()
            user_content = (ocr_text + parts[1]).strip()

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]

            response = self.client.chat.completions.create(
                model=self.model_uri,
                messages=messages,
                temperature=self.temperature,
                max_tokens=8000  # Задаем достаточно большой лимит
            )
            
            corrected_text = response.choices[0].message.content
            logging.info("Текст успешно обработан LLM (OpenAI-совместимый).")
            return corrected_text

        except openai.APIError as e:
            logging.error(f"Ошибка API при работе с OpenAI-совместимой моделью: {e}")
            return f"[ОШИБКА LLM/API: {e}]"
        except Exception as e:
            logging.error(f"Непредвиденная ошибка в OpenAICompatibleLLM: {e}", exc_info=True)
            return f"[ОШИБКА LLM: {e}]"
