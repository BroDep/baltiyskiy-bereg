# prepare_data.py
import json
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TicketDataProcessor:
    """Обработка тикетов и извлечение Q&A пар"""
    
    # Ключевые слова для определения ролей
    SUPPORT_KEYWORDS = ['техподдержка', 'support', 'helpdesk', 'admin', 'сисадмин']
    
    def parse_comment_html(self, html_content: str) -> List[Dict]:
        """Парсинг HTML комментариев в диалоги"""
        if not html_content:
            return []
        
        soup = BeautifulSoup(html_content, 'html.parser')
        comments = []
        
        for comment_div in soup.find_all('div', class_='comment'):
            # Извлекаем автора
            author_div = comment_div.find('div', class_='author')
            author = author_div.get_text(strip=True) if author_div else 'Unknown'
            
            # Извлекаем дату
            date_div = comment_div.find('div', class_='date')
            date = date_div.get_text(strip=True) if date_div else ''
            
            # Извлекаем текст
            text_div = comment_div.find('div', class_='text')
            text = text_div.get_text(strip=True) if text_div else ''
            
            # Определяем роль (поддержка или пользователь)
            is_support = any(kw in author.lower() for kw in self.SUPPORT_KEYWORDS)
            
            comments.append({
                'author': author,
                'date': date,
                'text': text,
                'is_support': is_support
            })
        
        return comments
    
    def extract_qa_pairs(self, comments: List[Dict]) -> List[Dict]:
        """Извлечение пар вопрос-ответ из комментариев"""
        qa_pairs = []
        current_question = None
        
        for comment in comments:
            if not comment['is_support'] and not current_question:
                # Это вопрос от пользователя
                current_question = {
                    'text': comment['text'],
                    'author': comment['author'],
                    'date': comment['date']
                }
            elif comment['is_support'] and current_question:
                # Это ответ поддержки на текущий вопрос
                qa_pairs.append({
                    'question': current_question['text'],
                    'answer': comment['text'],
                    'support_author': comment['author'],
                    'date': comment['date']
                })
                current_question = None
        
        return qa_pairs
    
    def process_ticket(self, ticket: Dict) -> List[Dict]:
        """Обработка одного тикета"""
        documents = []
        
        # Извлекаем диалоги из комментариев
        comments = self.parse_comment_html(ticket.get('Comment', ''))
        qa_pairs = self.extract_qa_pairs(comments)
        
        for i, qa in enumerate(qa_pairs):
            doc = {
                'id': f"{ticket.get('Id')}_qa_{i}",
                'ticket_id': ticket.get('Id'),
                'source': 'ticket',
                'title': qa['question'][:100],  # Обрезаем до 100 символов
                'text': f"Вопрос: {qa['question']}\nОтвет: {qa['answer']}",
                'question': qa['question'],
                'answer': qa['answer'],
                'service_id': ticket.get('ServiceId'),
                'service_name': ticket.get('ServiceName'),
                'task_type_id': ticket.get('TypeId'),
                'priority_id': ticket.get('PriorityId'),
                'created_date': ticket.get('CreatedDate'),
                'date': qa['date']
            }
            documents.append(doc)
        
        # Также добавляем сам тикет как документ (описание + название)
        if ticket.get('Name') or ticket.get('Description'):
            doc = {
                'id': f"{ticket.get('Id')}_ticket",
                'ticket_id': ticket.get('Id'),
                'source': 'ticket',
                'title': ticket.get('Name', 'Без названия'),
                'text': f"{ticket.get('Name', '')}\n{ticket.get('Description', '')}",
                'service_id': ticket.get('ServiceId'),
                'service_name': ticket.get('ServiceName'),
                'task_type_id': ticket.get('TypeId'),
                'priority_id': ticket.get('PriorityId'),
                'created_date': ticket.get('CreatedDate'),
            }
            documents.append(doc)
        
        return documents

class KBProcessor:
    """Обработка статей

# TODO: Извлечь Q&A-пары из поля Task.Comment
#
# 1. Подключиться к MSSQL (pymssql), выбрать Task.Id, Task.Name, Task.Comment,
#    Task.ServiceId, Task.TypeId, Task.PriorityId, Task.StatusId, Task.CreatedDate
# 2. Для каждого тикета распарсить Task.Comment (HTML) через BeautifulSoup:
#    - Выделить отдельные блоки комментариев (автор, дата, текст)
#    - Определить роль автора: сотрудник vs. техподдержка (по наличию имени в служебных ролях)
#    - Сформировать диалоговые пары (вопрос сотрудника → ответ поддержки)
# 3. Каждую пару сохранить как документ в JSONL:
#    { "text": "...", "ticket_id": 123, "service_id": 5, "type_id": 2,
#      "priority_id": 1, "status_id": 3, "created_date": "2024-01-15", "title": "..." }
# 4. Ожидаемый объём: ~300 000 документов
# 5. Вывод: data/dialogues.jsonl
