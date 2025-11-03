import base64
import json
import logging
import requests
from .base_ocr import BaseOCR
from .. import config

class YandexVisionOCR(BaseOCR):
    """Реализация OCR через Yandex Vision API."""

    def __init__(self, processing_method: str = 'markdown'):
        self.url = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"
        self.api_key = config.YC_API_KEY
        if not self.api_key:
            raise ValueError("API-ключ Yandex не найден.")
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.api_key}"
        }
        self.processing_method = processing_method

    def _process_with_bbox(self, response_data: dict) -> str:
        """Собирает текст на основе Bounding Boxes для сохранения абзацев."""
        try:
            full_text_annotation = response_data['result']['textAnnotation']
            lines = []
            for block in full_text_annotation.get('blocks', []):
                lines.extend(block.get('lines', []))

            if not lines:
                return full_text_annotation.get('fullText', '')

            # Сортируем строки по вертикали, затем по горизонтали
            lines.sort(key=lambda line: (int(line['boundingBox']['vertices'][0]['y']), int(line['boundingBox']['vertices'][0]['x'])))

            result_text = ""
            prev_line_bottom = 0
            for i, line in enumerate(lines):
                line_text = line['text']
                top_y = int(line['boundingBox']['vertices'][0]['y'])
                bottom_y = int(line['boundingBox']['vertices'][2]['y'])
                line_height = bottom_y - top_y

                if i > 0:
                    gap = top_y - prev_line_bottom
                    # Если вертикальный разрыв больше 80% высоты предыдущей строки, считаем это новым абзацем
                    if gap > (line_height * 0.8):
                        result_text += "\n\n"
                    else:
                        result_text += " "
                
                result_text += line_text
                prev_line_bottom = bottom_y
            
            return result_text.strip()
        except (KeyError, IndexError) as e:
            logging.error(f"Ошибка при обработке Bbox: {e}")
            return response_data.get('result', {}).get('textAnnotation', {}).get('fullText', '')

    def recognize(self, image_path: str) -> str:
        logging.info(f"Распознавание файла {image_path} с помощью Yandex Vision (метод: {self.processing_method})...")
        try:
            with open(image_path, "rb") as f:
                image_data = f.read()
            
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            body = {
                "mimeType": "JPEG",
                "languageCodes": ["ru", "en", "de"],
                "model": "handwritten-ocr",
                "content": encoded_image
            }

            response = requests.post(self.url, headers=self.headers, data=json.dumps(body))
            response.raise_for_status()
            
            response_data = response.json()

            if 'error' in response_data:
                logging.error(f"Ошибка от API Yandex Vision: {response_data['error']}")
                return ""

            if self.processing_method == 'bbox':
                return self._process_with_bbox(response_data)
            
            # По умолчанию (метод 'simple') используем готовый markdown
            return response_data.get('result', {}).get('textAnnotation', {}).get('markdown', '')

        except requests.exceptions.RequestException as e:
            logging.error(f"Сетевая ошибка при обращении к Yandex Vision: {e}")
        except Exception as e:
            logging.error(f"Непредвиденная ошибка в YandexVisionOCR: {e}")
        return ""
