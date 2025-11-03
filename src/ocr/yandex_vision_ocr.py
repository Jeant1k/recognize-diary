import base64
import json
import logging
import requests
from .base_ocr import BaseOCR
import config

class YandexVisionOCR(BaseOCR):
    """Реализация OCR через Yandex Vision API."""

    def __init__(self, processing_method: str = 'markdown'):
        self.url = "https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText"
        
        if not config.YC_API_KEY or not config.YC_FOLDER_ID:
            raise ValueError("API-ключ (YC_API_KEY) и ID каталога (YC_FOLDER_ID) не найдены.")
            
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {config.YC_API_KEY}",
            "x-folder-id": config.YC_FOLDER_ID,
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
            if lines:
                avg_line_height = sum(
                    int(line['boundingBox']['vertices'][2]['y']) - int(line['boundingBox']['vertices'][0]['y']) 
                    for line in lines
                ) / len(lines)

            for i, line in enumerate(lines):
                line_text = line['text']
                top_y = int(line['boundingBox']['vertices'][0]['y'])
                
                if i > 0:
                    gap = top_y - prev_line_bottom
                    if gap > avg_line_height:
                        result_text += "\n\n"
                    else:
                        result_text += " "
                
                result_text += line_text
                prev_line_bottom = int(line['boundingBox']['vertices'][2]['y'])
            
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
                "model": "handwritten",
                "content": encoded_image
            }

            response = requests.post(self.url, headers=self.headers, json=body, timeout=180)
            response.raise_for_status()
            
            response_data = response.json()

            if 'error' in response_data:
                logging.error(f"Ошибка от API Yandex Vision: {response_data['error']['message']}")
                return ""
            
            if 'result' not in response_data:
                logging.error(f"В ответе API Yandex Vision отсутствует ключ 'result'. Ответ: {response_data}")
                return ""

            if self.processing_method == 'bbox':
                return self._process_with_bbox(response_data)
            
            return response_data.get('result', {}).get('textAnnotation', {}).get('fullText', '')

        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP-ошибка при обращении к Yandex Vision: {e.response.status_code}. Ответ сервера: {e.response.text}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Сетевая ошибка при обращении к Yandex Vision: {e}")
        except Exception as e:
            logging.error(f"Непредвиденная ошибка в YandexVisionOCR: {e}", exc_info=True)

        return ""
