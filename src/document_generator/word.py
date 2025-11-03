import docx
import logging
from pathlib import Path

def create_word_document(markdown_texts: list[str], output_path: str | Path):
    """
    Создает Word документ из списка текстов в формате Markdown (по одному на страницу).
    Каждый элемент списка будет отделен в документе.
    """
    logging.info(f"Создание Word документа: {output_path}")
    doc = docx.Document()
    doc.add_heading('Дневник', level=0)

    for i, page_text in enumerate(markdown_texts):
        # Добавляем разделитель страниц, кроме как перед первой страницей
        if i > 0:
            doc.add_page_break()
        
        doc.add_heading(f'Страница {i+1}', level=1) # Условное название, можно изменить

        # Простая обработка Markdown: разделяем на абзацы по двойному переносу строки
        paragraphs = page_text.strip().split('\n\n')
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Очень простое распознавание заголовков
            if para.startswith('# '):
                doc.add_heading(para.lstrip('# ').strip(), level=2)
            elif para.startswith('## '):
                doc.add_heading(para.lstrip('## ').strip(), level=3)
            # Очень простое распознавание цитат
            elif para.startswith('> '):
                p = doc.add_paragraph(para.lstrip('> ').strip())
                p.style = 'Quote' # Встроенный стиль для цитат
            else:
                # Очищаем от одиночных переносов строк внутри абзаца
                cleaned_para = para.replace('\n', ' ').strip()
                doc.add_paragraph(cleaned_para)

    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
        logging.info(f"Документ успешно сохранен: {output_path}")
    except Exception as e:
        logging.error(f"Не удалось сохранить Word документ: {e}")
