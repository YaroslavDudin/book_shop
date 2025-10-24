#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное приложение системы "Книжный Мир"
Полнофункциональная система управления книжным магазином
"""

import sys
import os
import zipfile
import xml.etree.ElementTree as ET
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QMessageBox, QStackedWidget, QFrame, QScrollArea,
                             QGridLayout, QComboBox, QCheckBox, QSpinBox,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QDialog, QDialogButtonBox, QFormLayout,
                             QTextEdit, QDateEdit, QGroupBox, QSplitter)
from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtGui import QPixmap, QFont, QIcon, QPalette, QColor
import sqlite3
from datetime import datetime

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, db_path='bookstore.db'):
        self.db_path = db_path
        self.order_updates = {}  # Кэш для обновлений заказов
    
    def get_connection(self):
        """Получает подключение к базе данных"""
        return sqlite3.connect(self.db_path)
    
    def authenticate_user(self, login, password):
        """Аутентификация пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, full_name, role FROM users 
            WHERE login = ? AND password = ?
        ''', (login, password))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'full_name': result[1],
                'role': result[2]
            }
        return None
    
    def get_books(self, search_query=None, genre_filter=None, sort_by='title'):
        """Получает список книг с фильтрацией и сортировкой"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT b.id, b.title, b.author, g.name as genre, p.name as publisher,
                   b.year, b.price, b.stock_quantity, b.is_on_sale, b.discount_price,
                   b.cover_image, b.description
            FROM books b
            JOIN genres g ON b.genre_id = g.id
            JOIN publishers p ON b.publisher_id = p.id
            WHERE 1=1
        '''
        
        params = []
        
        if search_query:
            query += ' AND (b.title LIKE ? OR b.author LIKE ?)'
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        
        if genre_filter:
            query += ' AND g.name = ?'
            params.append(genre_filter)
        
        # Сортировка
        if sort_by == 'title':
            query += ' ORDER BY b.title'
        elif sort_by == 'author':
            query += ' ORDER BY b.author'
        elif sort_by == 'price':
            query += ' ORDER BY b.price'
        elif sort_by == 'year':
            query += ' ORDER BY b.year DESC'
        
        cursor.execute(query, params)
        books = cursor.fetchall()
        conn.close()
        
        # Убираем дубликаты по названию и автору (оставляем только первую запись)
        seen_books = set()
        unique_books = []
        for book in books:
            book_key = (book[1].lower().strip(), book[2].lower().strip())  # title, author
            if book_key not in seen_books:
                seen_books.add(book_key)
                unique_books.append(book)
        
        return unique_books
    
    def get_genres(self):
        """Получает список жанров"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM genres ORDER BY name')
        genres = cursor.fetchall()
        conn.close()
        return genres
    
    def get_orders(self):
        """Получает список заказов"""
        # Сначала пытаемся загрузить заказы из базы данных
        db_orders = self.get_orders_from_db()
        
        # Затем загружаем заказы из Excel файла
        excel_orders = self.get_orders_from_excel()
        
        # Объединяем заказы из базы данных и Excel
        all_orders = db_orders + excel_orders
        
        # Применяем обновления из кэша
        for order_id, updates in self.order_updates.items():
            for i, order in enumerate(all_orders):
                if str(order[0]) == str(order_id):
                    # Обновляем заказ с изменениями
                    updated_order = list(order)
                    if 'status' in updates:
                        updated_order[7] = updates['status']
                    if 'delivery_date' in updates:
                        updated_order[3] = updates['delivery_date']
                    if 'pickup_code' in updates:
                        updated_order[6] = updates['pickup_code']
                    all_orders[i] = tuple(updated_order)
                    break
        
        print(f"Загружено {len(all_orders)} заказов (из БД: {len(db_orders)}, из Excel: {len(excel_orders)})")
        return all_orders
    
    def get_orders_from_db(self):
        """Получает заказы из базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT o.id, o.user_id, o.pickup_point_id, o.status, o.total_amount, 
                   o.order_date, o.completion_date, u.full_name
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            ORDER BY o.id DESC
        ''')
        
        orders = cursor.fetchall()
        conn.close()
        
        # Преобразуем данные из БД в нужный формат
        formatted_orders = []
        for order in orders:
            # Форматируем даты
            if order[5]:
                if hasattr(order[5], 'strftime'):
                    order_date = order[5].strftime('%d.%m.%Y')
                else:
                    # Если это строка, пытаемся преобразовать
                    try:
                        from datetime import datetime
                        if isinstance(order[5], str):
                            # Пытаемся распарсить строку даты
                            if ' ' in order[5]:
                                dt = datetime.strptime(order[5], '%Y-%m-%d %H:%M:%S')
                            else:
                                dt = datetime.strptime(order[5], '%Y-%m-%d')
                            order_date = dt.strftime('%d.%m.%Y')
                        else:
                            order_date = str(order[5])
                    except:
                        order_date = str(order[5])
            else:
                order_date = ''
            
            if order[6]:
                if hasattr(order[6], 'strftime'):
                    delivery_date = order[6].strftime('%d.%m.%Y')
                else:
                    # Если это строка, пытаемся преобразовать
                    try:
                        from datetime import datetime
                        if isinstance(order[6], str):
                            # Пытаемся распарсить строку даты
                            if ' ' in order[6]:
                                dt = datetime.strptime(order[6], '%Y-%m-%d %H:%M:%S')
                            else:
                                dt = datetime.strptime(order[6], '%Y-%m-%d')
                            delivery_date = dt.strftime('%d.%m.%Y')
                        else:
                            delivery_date = str(order[6])
                    except:
                        delivery_date = str(order[6])
            else:
                delivery_date = ''
            
            # Преобразуем статус из БД в понятный формат
            status_mapping = {
                'pending': 'Новый',
                'processing': 'В обработке', 
                'ready': 'Готов к выдаче',
                'completed': 'Доставлен',
                'cancelled': 'Отменен'
            }
            display_status = status_mapping.get(order[3], order[3])
            
            # Получаем дополнительные данные из кэша
            order_id = order[0]
            client_name = order[7] or 'Пользователь'
            composition = 'Состав заказа'
            pickup_code = ''
            
            # Проверяем кэш для этого заказа
            if order_id in self.order_updates:
                cache_data = self.order_updates[order_id]
                if 'client_name' in cache_data:
                    client_name = cache_data['client_name']
                if 'composition' in cache_data:
                    composition = cache_data['composition']
                if 'pickup_code' in cache_data:
                    pickup_code = cache_data['pickup_code']
            
            formatted_order = (
                order[0],  # ID заказа
                composition,  # Состав заказа
                order_date,
                delivery_date,
                order[2],  # ID пункта выдачи
                client_name,  # ФИО клиента
                pickup_code,  # Код для получения
                display_status  # Статус
            )
            formatted_orders.append(formatted_order)
        
        return formatted_orders
    
    def get_orders_from_excel(self):
        """Получает заказы из Excel файла"""
        # Пытаемся загрузить заказы из Excel файла
        orders_data = self.load_orders_from_excel()
        
        if orders_data:
            # Преобразуем данные из Excel в нужный формат
            orders = []
            for i, order_data in enumerate(orders_data):
                # Конвертируем даты из Excel формата
                order_date = self.excel_date_to_string(order_data.get('Дата заказа', ''))
                delivery_date = self.excel_date_to_string(order_data.get('Дата доставки', ''))
                
                order = (
                    order_data.get('Номер заказа', i + 1001),
                    order_data.get('Состав заказа (Артикул, Кол-во)', ''),
                    order_date,
                    delivery_date,
                    order_data.get('ID Пункта выдачи', 0),
                    order_data.get('ФИО клиента', ''),
                    order_data.get('Код для получения', ''),
                    order_data.get('Статус заказа', 'Новый')
                )
                orders.append(order)
            
            return orders
        else:
            # Если не удалось загрузить из Excel, используем тестовые данные
            test_orders = [
                (1001, 'B112F4, 1, F635R4, 2', '15.02.2025', '20.02.2025', 3, 'Белов Алексей Дмитриевич', 'Z1X9Y2', 'Доставлен'),
                (1002, 'H782T5, 1, G783F5, 1', '16.02.2025', '21.02.2025', 7, 'Соколова Мария Андреевна', 'A3B4C5', 'Доставлен'),
                (1003, 'J384T6, 1, D572U8, 1', '18.02.2025', '23.02.2025', 12, 'Морозов Иван Павлович', 'D6E7F8', 'Доставлен'),
                (1004, 'F572H7, 1, D329H3, 1', '20.02.2025', '25.02.2025', 5, 'Лебедева Ольга Васильевна', 'G9H0I1', 'Доставлен'),
                (1005, 'B112F4, 2, F635R4, 1', '01.03.2025', '06.03.2025', 18, 'Белов Алексей Дмитриевич', 'J2K3L4', 'В обработке'),
                (1006, 'H782T5, 1, G783F5, 2', '02.03.2025', '07.03.2025', 22, 'Соколова Мария Андреевна', 'M5N6O7', 'В обработке'),
                (1007, 'J384T6, 3, D572U8, 1', '03.03.2025', '08.03.2025', 9, 'Морозов Иван Павлович', 'P8Q9R0', 'В обработке'),
                (1008, 'F572H7, 1, D329H3, 2', '04.03.2025', '09.03.2025', 31, 'Лебедева Ольга Васильевна', 'S1T2U3', 'В обработке'),
                (1009, 'B320R5, 1, G432E4, 1', '05.03.2025', '10.03.2025', 14, 'Белов Алексей Дмитриевич', 'V4W5X6', 'Новый'),
                (1010, 'S213E3, 1, E482R4, 1', '06.03.2025', '11.03.2025', 27, 'Соколова Мария Андреевна', 'Y7Z8A9', 'Новый')
            ]
            
            return test_orders
    
    def get_order_items(self, order_id):
        """Получает позиции заказа"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT b.title, oi.quantity, oi.price
            FROM order_items oi
            JOIN books b ON oi.book_id = b.id
            WHERE oi.order_id = ?
        '''
        
        cursor.execute(query, (order_id,))
        items = cursor.fetchall()
        conn.close()
        
        return items
    
    def update_order_status(self, order_id, status):
        """Обновляет статус заказа"""
        # Преобразуем статус из отображаемого формата в формат БД
        status_mapping = {
            'Новый': 'pending',
            'В обработке': 'processing',
            'Готов к выдаче': 'ready', 
            'Доставлен': 'completed',
            'Отменен': 'cancelled'
        }
        db_status = status_mapping.get(status, status)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE orders SET status = ? WHERE id = ?
        ''', (db_status, order_id))
        
        conn.commit()
        conn.close()
    
    def add_book(self, title, author, genre_id, publisher_id, year, price, 
                 stock_quantity, is_on_sale=False, discount_price=None, 
                 cover_image='placeholder.png', description=''):
        """Добавляет новую книгу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO books (title, author, genre_id, publisher_id, year, price,
                             stock_quantity, is_on_sale, discount_price, cover_image, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, author, genre_id, publisher_id, year, price, stock_quantity,
              is_on_sale, discount_price, cover_image, description))
        
        conn.commit()
        conn.close()
    
    def update_book(self, book_id, title, author, genre_id, publisher_id, year, 
                   price, stock_quantity, is_on_sale=False, discount_price=None, 
                   cover_image='placeholder.png', description=''):
        """Обновляет книгу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Проверяем, существует ли книга
        cursor.execute('SELECT id FROM books WHERE id = ?', (book_id,))
        if not cursor.fetchone():
            print(f"Книга с ID {book_id} не найдена")
            conn.close()
            return False
        
        # Обновляем книгу
        cursor.execute('''
            UPDATE books SET title=?, author=?, genre_id=?, publisher_id=?, year=?,
                           price=?, stock_quantity=?, is_on_sale=?, discount_price=?,
                           cover_image=?, description=?
            WHERE id=?
        ''', (title, author, genre_id, publisher_id, year, price, stock_quantity,
              is_on_sale, discount_price, cover_image, description, book_id))
        
        # Проверяем, сколько строк было обновлено
        rows_affected = cursor.rowcount
        print(f"Обновлено строк: {rows_affected} для книги ID {book_id}")
        
        conn.commit()
        conn.close()
        return rows_affected > 0
    
    def delete_book(self, book_id):
        """Удаляет книгу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        conn.close()
    
    def get_users(self):
        """Получает список пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, login, full_name, role FROM users ORDER BY role, full_name')
        users = cursor.fetchall()
        conn.close()
        return users
    
    def add_user(self, login, password, full_name, role):
        """Добавляет нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (login, password, full_name, role)
            VALUES (?, ?, ?, ?)
        ''', (login, password, full_name, role))
        
        conn.commit()
        conn.close()
    
    def update_user(self, user_id, login, password, full_name, role):
        """Обновляет пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET login=?, password=?, full_name=?, role=?
            WHERE id=?
        ''', (login, password, full_name, role, user_id))
        
        conn.commit()
        conn.close()
    
    def delete_user(self, user_id):
        """Удаляет пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
    
    def get_publishers(self):
        """Получает список издательств"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM publishers ORDER BY name')
        publishers = cursor.fetchall()
        conn.close()
        return publishers
    
    def add_publisher(self, name):
        """Добавляет издательство"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO publishers (name) VALUES (?)', (name,))
        conn.commit()
        conn.close()
    
    def add_genre(self, name):
        """Добавляет жанр"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO genres (name) VALUES (?)', (name,))
        conn.commit()
        conn.close()
    
    def add_order(self, user_id, pickup_point_id, order_items, total_amount, order_date, completion_date):
        """Добавляет новый заказ"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Добавляем заказ
        cursor.execute('''
            INSERT INTO orders (user_id, pickup_point_id, total_amount, order_date, completion_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, pickup_point_id, total_amount, order_date, completion_date, 'pending'))
        
        order_id = cursor.lastrowid
        
        # Добавляем позиции заказа
        for book_id, quantity, price in order_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, book_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, book_id, quantity, price))
        
        conn.commit()
        conn.close()
        return order_id
    
    def add_order_with_status(self, user_id, pickup_point_id, order_items, total_amount, order_date, completion_date, status):
        """Добавляет новый заказ с указанным статусом"""
        # Преобразуем статус из отображаемого формата в формат БД
        status_mapping = {
            'Новый': 'pending',
            'В обработке': 'processing',
            'Готов к выдаче': 'ready',
            'Доставлен': 'completed',
            'Отменен': 'cancelled'
        }
        db_status = status_mapping.get(status, 'pending')
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Добавляем заказ
        cursor.execute('''
            INSERT INTO orders (user_id, pickup_point_id, total_amount, order_date, completion_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, pickup_point_id, total_amount, order_date, completion_date, db_status))
        
        order_id = cursor.lastrowid
        
        # Добавляем позиции заказа
        for book_id, quantity, price in order_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, book_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, book_id, quantity, price))
        
        conn.commit()
        conn.close()
        return order_id
    
    def add_order_with_details(self, pickup_point_id, order_items, total_amount, order_date, completion_date, status, client_name, composition, pickup_code):
        """Добавляет новый заказ с полными деталями"""
        # Преобразуем статус из отображаемого формата в формат БД
        status_mapping = {
            'Новый': 'pending',
            'В обработке': 'processing',
            'Готов к выдаче': 'ready',
            'Доставлен': 'completed',
            'Отменен': 'cancelled'
        }
        db_status = status_mapping.get(status, 'pending')
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Добавляем заказ
        cursor.execute('''
            INSERT INTO orders (user_id, pickup_point_id, total_amount, order_date, completion_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (1, pickup_point_id, total_amount, order_date, completion_date, db_status))
        
        order_id = cursor.lastrowid
        
        # Добавляем позиции заказа
        for book_id, quantity, price in order_items:
            cursor.execute('''
                INSERT INTO order_items (order_id, book_id, quantity, price)
                VALUES (?, ?, ?, ?)
            ''', (order_id, book_id, quantity, price))
        
        # Сохраняем дополнительные данные в кэш для отображения
        if order_id not in self.order_updates:
            self.order_updates[order_id] = {}
        
        self.order_updates[order_id]['client_name'] = client_name
        self.order_updates[order_id]['composition'] = composition
        self.order_updates[order_id]['pickup_code'] = pickup_code
        
        conn.commit()
        conn.close()
        return order_id
    
    def delete_order(self, order_id):
        """Удаляет заказ"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Сначала удаляем позиции заказа
        cursor.execute('DELETE FROM order_items WHERE order_id = ?', (order_id,))
        
        # Затем удаляем сам заказ
        cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        
        conn.commit()
        conn.close()
    
    def get_order_by_id(self, order_id):
        """Получает заказ по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, pickup_point_id, status, total_amount, order_date, completion_date
            FROM orders WHERE id = ?
        ''', (order_id,))
        
        order = cursor.fetchone()
        conn.close()
        return order
    
    def excel_date_to_string(self, excel_date):
        """Конвертирует Excel дату в читаемую строку"""
        try:
            # Excel даты начинаются с 1 января 1900 года
            # Нужно вычесть 2 дня из-за особенностей Excel
            from datetime import datetime, timedelta
            excel_epoch = datetime(1900, 1, 1)
            date = excel_epoch + timedelta(days=int(excel_date) - 2)
            return date.strftime('%d.%m.%Y')
        except:
            return str(excel_date)
    
    def read_excel_file(self, file_path):
        """Читает Excel файл (.xlsx) и возвращает данные в виде списка словарей"""
        try:
            # Excel файлы - это zip архивы
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Читаем sharedStrings.xml для строковых значений
                shared_strings = {}
                try:
                    with zip_file.open('xl/sharedStrings.xml') as f:
                        tree = ET.parse(f)
                        root = tree.getroot()
                        for i, si in enumerate(root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si')):
                            text_elem = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
                            if text_elem is not None:
                                shared_strings[i] = text_elem.text or ""
                except:
                    pass
                
                # Читаем worksheet
                worksheet_path = 'xl/worksheets/sheet1.xml'
                if worksheet_path not in zip_file.namelist():
                    # Ищем первый worksheet
                    for name in zip_file.namelist():
                        if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                            worksheet_path = name
                            break
                
                with zip_file.open(worksheet_path) as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    
                    # Находим все строки
                    rows = root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row')
                    
                    data = []
                    headers = []
                    
                    for row_idx, row in enumerate(rows):
                        cells = row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c')
                        row_data = []
                        
                        for cell in cells:
                            cell_type = cell.get('t', '')
                            cell_value = ''
                            
                            # Получаем значение ячейки
                            value_elem = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                            if value_elem is not None:
                                cell_value = value_elem.text or ''
                                
                                # Если это строка, получаем из sharedStrings
                                if cell_type == 's' and cell_value.isdigit():
                                    cell_value = shared_strings.get(int(cell_value), '')
                            
                            row_data.append(cell_value)
                        
                        if row_data:
                            if row_idx == 0:
                                # Первая строка - заголовки
                                headers = row_data
                            else:
                                # Остальные строки - данные
                                if len(row_data) == len(headers):
                                    row_dict = {}
                                    for i, header in enumerate(headers):
                                        if i < len(row_data):
                                            row_dict[header] = row_data[i]
                                    data.append(row_dict)
                    
                    return data
                    
        except Exception as e:
            print(f"Ошибка при чтении Excel файла: {e}")
            return []
    
    def load_orders_from_excel(self):
        """Загружает заказы из файла orders.xlsx"""
        file_path = "Модуль 1/Прил_2_ОЗ_КОД 09.02.07-2-2026-М1/orders.xlsx"
        
        if not os.path.exists(file_path):
            print(f"Файл {file_path} не найден")
            return []
        
        try:
            orders_data = self.read_excel_file(file_path)
            print(f"Загружено {len(orders_data)} заказов из Excel файла")
            
            # Выводим структуру данных для понимания
            if orders_data:
                print("Структура данных:")
                print("Заголовки:", list(orders_data[0].keys()))
                print("Первый заказ:", orders_data[0])
            
            return orders_data
        except Exception as e:
            print(f"Ошибка при загрузке заказов: {e}")
            return []

class LoginWindow(QWidget):
    """Окно авторизации"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Вход в систему - Книжный Мир')
        self.setFixedSize(600, 500)
        self.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                font-family: 'Times New Roman', serif;
            }
            QLabel {
                color: #333;
                font-size: 16px;
                font-weight: bold;
                background-color: transparent;
            }
            QLineEdit {
                padding: 15px;
                border: 2px solid #7FFF00;
                border-radius: 8px;
                font-size: 14px;
                background-color: #FFFFFF;
                color: #333;
                min-height: 20px;
            }
            QLineEdit:focus {
                border-color: #00FA9A;
                background-color: #FFFFFF;
            }
            QPushButton {
                background-color: #00FA9A;
                color: #333;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #7FFF00;
            }
            QPushButton:pressed {
                background-color: #00FA9A;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Логотип компании
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setFixedSize(120, 120)
        logo_label.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                border: 2px solid #7FFF00;
                border-radius: 8px;
                margin-bottom: 20px;
                padding: 10px;
            }
        """)
        
        # Загружаем логотип
        try:
            logo_path = "Модуль 1/Прил_2_ОЗ_КОД 09.02.07-2-2026-М1/Icon.png"
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                logo_label.setPixmap(scaled_pixmap)
            else:
                logo_label.setText("📚")
                logo_label.setStyleSheet("font-size: 48px;")
        except:
            logo_label.setText("📚")
            logo_label.setStyleSheet("font-size: 48px;")
        
        layout.addWidget(logo_label)
        
        # Заголовок
        title_label = QLabel('Книжный Мир')
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 32px; 
            font-weight: bold; 
            color: #333; 
            margin-bottom: 30px;
            background-color: transparent;
            padding: 10px;
        """)
        layout.addWidget(title_label)
        
        # Подзаголовок
        subtitle_label = QLabel('Система управления книжным магазином')
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            font-size: 14px; 
            color: #666; 
            margin-bottom: 20px;
            background-color: transparent;
            padding: 5px;
        """)
        layout.addWidget(subtitle_label)
        
        # Поля ввода
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText('Логин')
        self.login_input.setMinimumHeight(50)
        layout.addWidget(self.login_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText('Пароль')
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(50)
        layout.addWidget(self.password_input)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.login_button = QPushButton('Войти')
        self.login_button.clicked.connect(self.login)
        self.login_button.setMinimumHeight(40)
        button_layout.addWidget(self.login_button)
        
        self.guest_button = QPushButton('Войти как гость')
        self.guest_button.clicked.connect(self.login_as_guest)
        self.guest_button.setMinimumHeight(40)
        self.guest_button.setStyleSheet("""
            QPushButton {
                background-color: #7FFF00;
                color: #333;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: bold;
                min-height: 40px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #00FA9A;
            }
        """)
        button_layout.addWidget(self.guest_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def login(self):
        """Обработка входа в систему"""
        login = self.login_input.text().strip()
        password = self.password_input.text().strip()
        
        if not login or not password:
            QMessageBox.warning(self, 'Ошибка', 'Введите логин и пароль')
            return
        
        db_manager = DatabaseManager()
        user = db_manager.authenticate_user(login, password)
        
        if user:
            self.parent.current_user = user
            self.parent.show_main_window()
        else:
            QMessageBox.warning(self, 'Ошибка', 'Неверный логин или пароль')
    
    def login_as_guest(self):
        """Вход как гость"""
        self.parent.current_user = {
            'id': None,
            'full_name': 'Гость',
            'role': 'guest'
        }
        self.parent.show_main_window()

class BookCard(QFrame):
    """Карточка книги"""
    
    def __init__(self, book_data, parent=None):
        super().__init__(parent)
        self.book_data = book_data
        self.init_ui()
    
    def init_ui(self):
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(1)
        self.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 2px solid #7FFF00;
                border-radius: 8px;
                margin: 8px;
            }
            QFrame:hover {
                border-color: #00FA9A;
            }
        """)
        
        # Выделяем книги без остатка
        if self.book_data[7] == 0:  # stock_quantity
            self.setStyleSheet("""
                QFrame {
                    background-color: #ADD8E6;
                    border: 2px solid #74b9ff;
                    border-radius: 8px;
                    margin: 8px;
                }
            """)
        
        # Выделяем книги в акции
        if self.book_data[8] and self.book_data[9]:  # is_on_sale and discount_price
            self.setStyleSheet("""
                QFrame {
                    background-color: #FFE4B5;
                    border: 2px solid #FF8C00;
                    border-radius: 8px;
                    margin: 8px;
                }
            """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Обложка книги
        cover_label = QLabel()
        cover_label.setFixedSize(120, 160)
        cover_label.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                border: 2px solid #7FFF00;
                border-radius: 8px;
            }
        """)
        cover_label.setAlignment(Qt.AlignCenter)
        cover_label.setScaledContents(True)
        
        # Загружаем изображение книги
        image_filename = self.book_data[10] if self.book_data[10] else 'placeholder.png'
        image_path = f"Модуль 1/Прил_2_ОЗ_КОД 09.02.07-2-2026-М1/{image_filename}"
        
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                cover_label.setPixmap(pixmap.scaled(116, 156, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                # Если изображение не найдено, используем placeholder
                placeholder_path = "Модуль 1/Прил_2_ОЗ_КОД 09.02.07-2-2026-М1/placeboholder.png"
                placeholder_pixmap = QPixmap(placeholder_path)
                if not placeholder_pixmap.isNull():
                    cover_label.setPixmap(placeholder_pixmap.scaled(116, 156, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    cover_label.setText("📖")
                    cover_label.setStyleSheet("font-size: 48px;")
        except:
            # В случае ошибки используем placeholder
            try:
                placeholder_path = "Модуль 1/Прил_2_ОЗ_КОД 09.02.07-2-2026-М1/placeboholder.png"
                placeholder_pixmap = QPixmap(placeholder_path)
                if not placeholder_pixmap.isNull():
                    cover_label.setPixmap(placeholder_pixmap.scaled(116, 156, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                else:
                    cover_label.setText("📖")
                    cover_label.setStyleSheet("font-size: 48px;")
            except:
                cover_label.setText("📖")
                cover_label.setStyleSheet("font-size: 48px;")
        
        layout.addWidget(cover_label)
        
        # Информация о книге
        title_author = f"{self.book_data[1]} | {self.book_data[2]}"
        title_label = QLabel(title_author)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        layout.addWidget(title_label)
        
        # Детали
        details = [
            f"Жанр: {self.book_data[3]}",
            f"Издательство: {self.book_data[4]}",
            f"Год: {self.book_data[5]}",
        ]
        
        for detail in details:
            detail_label = QLabel(detail)
            detail_label.setStyleSheet("font-size: 12px; color: #666;")
            layout.addWidget(detail_label)
        
        # Цена
        price_layout = QHBoxLayout()
        
        if self.book_data[8]:  # is_on_sale
            # Акционная цена
            old_price = QLabel(f"₽{self.book_data[6]:.0f}")
            old_price.setStyleSheet("text-decoration: line-through; color: red; font-size: 12px;")
            price_layout.addWidget(old_price)
            
            new_price = QLabel(f"₽{self.book_data[9]:.0f}")
            new_price.setStyleSheet("font-weight: bold; font-size: 16px; color: #333;")
            price_layout.addWidget(new_price)
        else:
            price = QLabel(f"₽{self.book_data[6]:.0f}")
            price.setStyleSheet("font-weight: bold; font-size: 16px; color: #333;")
            price_layout.addWidget(price)
        
        layout.addLayout(price_layout)
        
        # Количество на складе
        stock_label = QLabel(f"На складе: {self.book_data[7]} шт.")
        if self.book_data[7] == 0:
            stock_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            stock_label.setStyleSheet("color: #666;")
        layout.addWidget(stock_label)
        
        self.setLayout(layout)

class CatalogWidget(QWidget):
    """Виджет каталога книг"""
    
    def __init__(self, db_manager, user_role, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_role = user_role
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title_label = QLabel('Каталог книг')
        title_label.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            color: #333; 
            margin-bottom: 20px;
            background-color: #FFFFFF;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #7FFF00;
        """)
        layout.addWidget(title_label)
        
        # Панель фильтров (для всех ролей кроме гостя)
        if self.user_role in ['manager', 'admin', 'client']:
            filter_frame = QFrame()
            filter_frame.setStyleSheet("""
                background-color: #FFFFFF;
                border: 2px solid #7FFF00; 
                border-radius: 8px; 
                padding: 15px;
                margin: 5px;
            """)
            filter_layout = QHBoxLayout()
            
            # Поиск (для всех ролей)
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText('Поиск по названию или автору...')
            self.search_input.textChanged.connect(self.apply_filters)
            filter_layout.addWidget(self.search_input)
            
            # Фильтр по жанру (только для менеджера и администратора)
            if self.user_role in ['manager', 'admin']:
                self.genre_combo = QComboBox()
                self.genre_combo.addItem('Все жанры')
                genres = self.db_manager.get_genres()
                for genre in genres:
                    self.genre_combo.addItem(genre[1])
                self.genre_combo.currentTextChanged.connect(self.apply_filters)
                filter_layout.addWidget(self.genre_combo)
                
                # Сортировка (только для менеджера и администратора)
                self.sort_combo = QComboBox()
                self.sort_combo.addItems(['По названию', 'По автору', 'По цене', 'По году'])
                self.sort_combo.currentTextChanged.connect(self.apply_filters)
                filter_layout.addWidget(self.sort_combo)
            
            filter_frame.setLayout(filter_layout)
            layout.addWidget(filter_frame)
        
        # Область прокрутки для книг
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FFFFFF;
            }
        """)
        
        # Контейнер для карточек книг
        self.books_widget = QWidget()
        self.books_layout = QGridLayout()
        self.books_layout.setSpacing(15)
        self.books_widget.setLayout(self.books_layout)
        
        scroll_area.setWidget(self.books_widget)
        layout.addWidget(scroll_area)
        
        self.setLayout(layout)
        
        # Загружаем книги
        self.load_books()
    
    def load_books(self):
        """Загружает книги в каталог"""
        # УДАЛЯЕМ ВСЕ ВИДЖЕТЫ ИЗ LAYOUT
        while self.books_layout.count() > 0:
            item = self.books_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Рекурсивно удаляем все элементы из вложенного layout
                while item.layout().count() > 0:
                    child_item = item.layout().takeAt(0)
                    if child_item.widget():
                        child_item.widget().deleteLater()
                item.layout().deleteLater()
        
        # Получаем параметры фильтрации
        search_query = None
        genre_filter = None
        sort_by = 'title'
        
        if hasattr(self, 'search_input'):
            search_query = self.search_input.text().strip() if self.search_input.text().strip() else None
        
        if hasattr(self, 'genre_combo') and self.genre_combo.currentText() != 'Все жанры':
            genre_filter = self.genre_combo.currentText()
        
        if hasattr(self, 'sort_combo'):
            sort_mapping = {
                'По названию': 'title',
                'По автору': 'author',
                'По цене': 'price',
                'По году': 'year'
            }
            sort_by = sort_mapping.get(self.sort_combo.currentText(), 'title')
        
        # Получаем книги из базы данных (дубликаты уже убраны в get_books)
        books = self.db_manager.get_books(search_query, genre_filter, sort_by)
        
        print(f"Загружено {len(books)} уникальных книг")
        
        # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА - очищаем layout еще раз
        while self.books_layout.count() > 0:
            item = self.books_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Создаем карточки книг
        row, col = 0, 0
        max_cols = 4
        
        for book in books:
            book_card = BookCard(book)
            self.books_layout.addWidget(book_card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
    
    def apply_filters(self):
        """Применяет фильтры и перезагружает книги"""
        self.load_books()

class OrdersWidget(QWidget):
    """Виджет заказов для менеджера и администратора"""
    
    def __init__(self, db_manager, user_role, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_role = user_role
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок и кнопки управления
        header_layout = QHBoxLayout()
        
        title_label = QLabel('Управление заказами')
        title_label.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            color: #333; 
            margin-bottom: 20px;
            background-color: #FFFFFF;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #7FFF00;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Кнопка добавления заказа (только для менеджера и администратора)
        if self.user_role in ['manager', 'admin']:
            add_order_btn = QPushButton('Добавить заказ')
            add_order_btn.setStyleSheet("""
                QPushButton {
                    background-color: #00FA9A;
                    color: #333;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    min-height: 32px;
                }
                QPushButton:hover {
                    background-color: #7FFF00;
                }
            """)
            add_order_btn.clicked.connect(self.add_order_dialog)
            header_layout.addWidget(add_order_btn)
        
        layout.addLayout(header_layout)
        
        # Таблица заказов
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(9)
        self.orders_table.setHorizontalHeaderLabels([
            'Номер заказа', 'Состав заказа', 'Дата заказа', 'Дата доставки', 
            'ID Пункта выдачи', 'ФИО клиента', 'Код для получения', 'Статус заказа', 'Действия'
        ])
        self.orders_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 2px solid #7FFF00;
                border-radius: 8px;
                gridline-color: #7FFF00;
            }
            QHeaderView::section {
                background-color: #7FFF00;
                color: #333;
                font-weight: bold;
                padding: 8px;
            }
            QTableWidgetItem {
                padding: 8px;
            }
        """)
        
        layout.addWidget(self.orders_table)
        
        self.setLayout(layout)
        
        # Загружаем заказы
        self.load_orders()
    
    def load_orders(self):
        """Загружает заказы в таблицу"""
        orders = self.db_manager.get_orders()
        
        # Очищаем таблицу перед загрузкой
        self.orders_table.setRowCount(0)
        self.orders_table.setRowCount(len(orders))
        
        for row, order in enumerate(orders):
            self.orders_table.setItem(row, 0, QTableWidgetItem(str(order[0])))  # Номер заказа
            self.orders_table.setItem(row, 1, QTableWidgetItem(order[1]))       # Состав заказа
            self.orders_table.setItem(row, 2, QTableWidgetItem(order[2]))       # Дата заказа
            self.orders_table.setItem(row, 3, QTableWidgetItem(order[3]))         # Дата доставки
            self.orders_table.setItem(row, 4, QTableWidgetItem(str(order[4]))) # ID Пункта выдачи
            self.orders_table.setItem(row, 5, QTableWidgetItem(order[5]))       # ФИО клиента
            self.orders_table.setItem(row, 6, QTableWidgetItem(order[6]))       # Код для получения
            self.orders_table.setItem(row, 7, QTableWidgetItem(order[7]))       # Статус заказа
            
            # Кнопка деталей заказа
            details_button = QPushButton('Детали')
            details_button.setStyleSheet("""
                QPushButton {
                    background-color: #00FA9A;
                    color: #333;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    min-height: 22px;
                    min-width: 60px;
                    max-width: 80px;
                }
                QPushButton:hover {
                    background-color: #7FFF00;
                }
            """)
            details_button.clicked.connect(lambda checked, oid=order[0]: self.show_order_details(oid))
            
            self.orders_table.setCellWidget(row, 8, details_button)
    
    def show_order_details(self, order_id):
        """Показывает детали заказа"""
        # Получаем данные заказа
        order_data = self.db_manager.get_order_by_id(order_id)
        if not order_data:
            # Если заказ не найден в БД, используем данные из Excel
            orders = self.db_manager.get_orders()
            order_data = None
            for order in orders:
                if str(order[0]) == str(order_id):
                    order_data = {
                        'id': order[0],
                        'client_name': order[5],
                        'pickup_point_id': order[4],
                        'total_amount': 0.0,
                        'order_date': order[2],
                        'delivery_date': order[3],
                        'pickup_code': order[6],
                        'status': order[7],
                        'composition': order[1]
                    }
                    break
        else:
            # Преобразуем данные из БД в нужный формат
            order_data = {
                'id': order_data[0],
                'user_id': order_data[1],
                'pickup_point_id': order_data[2],
                'status': order_data[3],
                'total_amount': order_data[4],
                'order_date': order_data[5],
                'delivery_date': order_data[6] if order_data[6] else '',
                'pickup_code': '',  # В БД нет этого поля
                'client_name': 'Пользователь',  # В БД нет этого поля
                'composition': 'Состав заказа'  # В БД нет этого поля
            }
        
        if not order_data:
            QMessageBox.warning(self, 'Ошибка', 'Заказ не найден')
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Детали заказа #{order_id}')
        dialog.setModal(True)
        dialog.resize(600, 500)
        
        layout = QVBoxLayout()
        
        # Информация о заказе
        info_group = QGroupBox('Информация о заказе')
        info_layout = QFormLayout()
        
        # Поля для редактирования (только для менеджера и администратора)
        if self.user_role in ['manager', 'admin']:
            self.status_combo = QComboBox()
            self.status_combo.addItems(['Новый', 'В обработке', 'Готов к выдаче', 'Доставлен', 'Отменен'])
            self.status_combo.setCurrentText(order_data.get('status', 'Новый'))
            info_layout.addRow('Статус заказа:', self.status_combo)
            
            self.pickup_code_input = QLineEdit(str(order_data.get('pickup_code', '')))
            info_layout.addRow('Код для получения:', self.pickup_code_input)
            
            self.delivery_date_input = QLineEdit(str(order_data.get('delivery_date', '')))
            info_layout.addRow('Дата доставки:', self.delivery_date_input)
        else:
            # Только для просмотра
            info_layout.addRow('Статус заказа:', QLabel(str(order_data.get('status', 'Новый'))))
            info_layout.addRow('Код для получения:', QLabel(str(order_data.get('pickup_code', ''))))
            info_layout.addRow('Дата доставки:', QLabel(str(order_data.get('delivery_date', ''))))
        
        info_layout.addRow('ФИО клиента:', QLabel(str(order_data.get('client_name', ''))))
        info_layout.addRow('ID Пункта выдачи:', QLabel(str(order_data.get('pickup_point_id', ''))))
        info_layout.addRow('Дата заказа:', QLabel(str(order_data.get('order_date', ''))))
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Состав заказа
        composition_text = order_data.get('composition', 'Не указан')
        if composition_text == 'Состав заказа':  # Если это заглушка из БД
            composition_text = 'Не указан'
        composition_label = QLabel(f"Состав заказа: {composition_text}")
        composition_label.setWordWrap(True)
        composition_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin: 5px;
            }
        """)
        layout.addWidget(composition_label)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        if self.user_role in ['manager', 'admin']:
            save_button = QPushButton('Сохранить изменения')
            save_button.setStyleSheet("""
                QPushButton {
                    background-color: #00FA9A;
                    color: #333;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    min-height: 32px;
                }
                QPushButton:hover {
                    background-color: #7FFF00;
                }
            """)
            save_button.clicked.connect(lambda: self.save_order_changes(order_id, dialog))
            button_layout.addWidget(save_button)
        
        close_button = QPushButton('Закрыть')
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #7FFF00;
                color: #333;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #00FA9A;
            }
        """)
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def save_order_changes(self, order_id, dialog):
        """Сохраняет изменения в заказе"""
        try:
            # Обновляем статус заказа в базе данных
            new_status = self.status_combo.currentText()
            self.db_manager.update_order_status(order_id, new_status)
            
            # Сохраняем изменения в кэш
            if order_id not in self.db_manager.order_updates:
                self.db_manager.order_updates[order_id] = {}
            
            self.db_manager.order_updates[order_id]['status'] = new_status
            
            # Сохраняем другие изменения если они есть
            if hasattr(self, 'delivery_date_input'):
                self.db_manager.order_updates[order_id]['delivery_date'] = self.delivery_date_input.text()
            
            if hasattr(self, 'pickup_code_input'):
                self.db_manager.order_updates[order_id]['pickup_code'] = self.pickup_code_input.text()
            
            QMessageBox.information(self, 'Успех', 'Изменения сохранены')
            dialog.accept()
            self.load_orders()  # Обновляем список заказов
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Не удалось сохранить изменения: {str(e)}')
    
    def change_order_status(self, order_id):
        """Изменяет статус заказа"""
        # ПРОВЕРЯЕМ РОЛЬ ПОЛЬЗОВАТЕЛЯ
        if self.user_role not in ['manager', 'admin']:
            QMessageBox.warning(self, 'Доступ запрещен', 'Только менеджеры и администраторы могут изменять статус заказов!')
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle('Изменение статуса заказа')
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        
        # Выбор статуса
        status_label = QLabel('Выберите новый статус:')
        layout.addWidget(status_label)
        
        status_combo = QComboBox()
        status_combo.addItems(['Новый', 'В обработке', 'Готов к выдаче', 'Доставлен', 'Отменен'])
        layout.addWidget(status_combo)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            new_status = status_combo.currentText()
            self.db_manager.update_order_status(order_id, new_status)
            self.load_orders()
            QMessageBox.information(self, 'Успех', 'Статус заказа обновлен')
    
    def edit_order_dialog(self, order_id):
        """Диалог редактирования заказа"""
        # ПРОВЕРЯЕМ РОЛЬ ПОЛЬЗОВАТЕЛЯ
        if self.user_role not in ['manager', 'admin']:
            QMessageBox.warning(self, 'Доступ запрещен', 'Только менеджеры и администраторы могут редактировать заказы!')
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f'Редактирование заказа #{order_id}')
        dialog.setModal(True)
        dialog.resize(400, 300)
        
        layout = QFormLayout()
        
        # Поля формы
        order_number_input = QLineEdit(str(order_id))
        order_number_input.setReadOnly(True)
        composition_input = QLineEdit()
        order_date_input = QLineEdit()
        delivery_date_input = QLineEdit()
        pickup_id_input = QLineEdit()
        client_name_input = QLineEdit()
        code_input = QLineEdit()
        status_combo = QComboBox()
        status_combo.addItems(['Новый', 'В обработке', 'Готов к выдаче', 'Доставлен', 'Отменен'])
        
        layout.addRow('Номер заказа:', order_number_input)
        layout.addRow('Состав заказа:', composition_input)
        layout.addRow('Дата заказа:', order_date_input)
        layout.addRow('Дата доставки:', delivery_date_input)
        layout.addRow('ID Пункта выдачи:', pickup_id_input)
        layout.addRow('ФИО клиента:', client_name_input)
        layout.addRow('Код для получения:', code_input)
        layout.addRow('Статус заказа:', status_combo)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            QMessageBox.information(self, 'Успех', 'Заказ обновлен')
            self.load_orders()
    
    def add_order_dialog(self):
        """Диалог добавления заказа"""
        dialog = QDialog(self)
        dialog.setWindowTitle('Добавить заказ')
        dialog.setModal(True)
        dialog.resize(500, 400)
        
        layout = QFormLayout()
        
        # Поля формы
        client_name_input = QLineEdit()
        pickup_point_input = QLineEdit()
        order_date_input = QLineEdit()
        delivery_date_input = QLineEdit()
        pickup_code_input = QLineEdit()
        composition_input = QTextEdit()
        composition_input.setMaximumHeight(80)
        status_combo = QComboBox()
        status_combo.addItems(['Новый', 'В обработке', 'Готов к выдаче', 'Доставлен', 'Отменен'])
        
        # Устанавливаем текущую дату
        from datetime import datetime, timedelta
        today = datetime.now().strftime('%d.%m.%Y')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%d.%m.%Y')
        
        order_date_input.setText(today)
        delivery_date_input.setText(tomorrow)
        
        layout.addRow('ФИО клиента:', client_name_input)
        layout.addRow('ID Пункта выдачи:', pickup_point_input)
        layout.addRow('Дата заказа:', order_date_input)
        layout.addRow('Дата доставки:', delivery_date_input)
        layout.addRow('Код для получения:', pickup_code_input)
        layout.addRow('Состав заказа:', composition_input)
        layout.addRow('Статус заказа:', status_combo)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # Проверяем обязательные поля
            if not client_name_input.text().strip():
                QMessageBox.warning(self, 'Ошибка', 'Введите ФИО клиента')
                return
            
            try:
                pickup_point_id = int(pickup_point_input.text())
            except ValueError:
                QMessageBox.warning(self, 'Ошибка', 'Введите корректный ID пункта выдачи')
                return
            
            # Создаем заказ (пока без позиций)
            order_items = []  # Пустой список позиций
            total_amount = 0.0
            
            # Получаем выбранный статус
            selected_status = status_combo.currentText()
            
            # Получаем состав заказа
            composition = composition_input.toPlainText().strip()
            
            # Получаем код для получения
            pickup_code = pickup_code_input.text().strip()
            
            # Создаем заказ с выбранным статусом и дополнительными полями
            order_id = self.db_manager.add_order_with_details(
                pickup_point_id,
                order_items,
                total_amount,
                order_date_input.text().strip(),
                delivery_date_input.text().strip(),
                selected_status,
                client_name_input.text().strip(),
                composition,
                pickup_code
            )
            
            self.load_orders()
            QMessageBox.information(self, 'Успех', 'Заказ добавлен')

class AdminWidget(QWidget):
    """Виджет администратора"""
    
    def __init__(self, db_manager, catalog_widget=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.catalog_widget = catalog_widget
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        title_label = QLabel('Панель администратора')
        title_label.setStyleSheet("""
            font-size: 28px; 
            font-weight: bold; 
            color: #333; 
            margin-bottom: 20px;
            background-color: #FFFFFF;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #7FFF00;
        """)
        layout.addWidget(title_label)
        
        # Вкладки для разных функций
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #7FFF00;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #7FFF00;
                color: #333;
                padding: 10px 20px;
                margin-right: 2px;
                border-radius: 8px 8px 0 0;
            }
            QTabBar::tab:selected {
                background-color: #00FA9A;
            }
        """)
        
        # Управление книгами
        books_tab = self.create_books_management_tab()
        tab_widget.addTab(books_tab, 'Управление книгами')
        
        # Управление пользователями
        users_tab = self.create_users_management_tab()
        tab_widget.addTab(users_tab, 'Управление пользователями')
        
        
        layout.addWidget(tab_widget)
        self.setLayout(layout)
    
    def create_books_management_tab(self):
        """Создает вкладку управления книгами"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        add_book_btn = QPushButton('Добавить книгу')
        add_book_btn.setStyleSheet("""
            QPushButton {
                background-color: #00FA9A;
                color: #333;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #7FFF00;
            }
        """)
        add_book_btn.clicked.connect(self.add_book_dialog)
        buttons_layout.addWidget(add_book_btn)
        
        refresh_btn = QPushButton('Обновить')
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #00FA9A;
                color: #333;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #7FFF00;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_books_table)
        buttons_layout.addWidget(refresh_btn)
        
        layout.addLayout(buttons_layout)
        
        # Таблица книг
        self.books_table = QTableWidget()
        self.books_table.setColumnCount(8)
        self.books_table.setHorizontalHeaderLabels([
            'ID', 'Название', 'Автор', 'Жанр', 'Издательство', 'Цена', 'Количество', 'Действия'
        ])
        self.books_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 2px solid #7FFF00;
                border-radius: 8px;
                gridline-color: #7FFF00;
            }
            QHeaderView::section {
                background-color: #7FFF00;
                color: #333;
                font-weight: bold;
                padding: 8px;
            }
            QTableWidgetItem {
                padding: 8px;
            }
        """)
        
        layout.addWidget(self.books_table)
        
        widget.setLayout(layout)
        self.load_books_table()
        return widget
    
    def create_users_management_tab(self):
        """Создает вкладку управления пользователями"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        add_user_btn = QPushButton('Добавить пользователя')
        add_user_btn.setStyleSheet("""
            QPushButton {
                background-color: #00FA9A;
                color: #333;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #7FFF00;
            }
        """)
        add_user_btn.clicked.connect(self.add_user_dialog)
        buttons_layout.addWidget(add_user_btn)
        
        refresh_btn = QPushButton('Обновить')
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #00FA9A;
                color: #333;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #7FFF00;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_users_table)
        buttons_layout.addWidget(refresh_btn)
        
        layout.addLayout(buttons_layout)
        
        # Таблица пользователей
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels([
            'ID', 'Логин', 'ФИО', 'Роль', 'Действия'
        ])
        self.users_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 2px solid #7FFF00;
                border-radius: 8px;
                gridline-color: #7FFF00;
            }
            QHeaderView::section {
                background-color: #7FFF00;
                color: #333;
                font-weight: bold;
                padding: 8px;
            }
            QTableWidgetItem {
                padding: 8px;
            }
        """)
        
        layout.addWidget(self.users_table)
        
        widget.setLayout(layout)
        self.load_users_table()
        return widget
    
    
    def load_books_table(self):
        """Загружает книги в таблицу"""
        books = self.db_manager.get_books()
        
        # Очищаем таблицу перед загрузкой
        self.books_table.setRowCount(0)
        self.books_table.setRowCount(len(books))
        
        for row, book in enumerate(books):
            self.books_table.setItem(row, 0, QTableWidgetItem(str(book[0])))
            self.books_table.setItem(row, 1, QTableWidgetItem(book[1]))
            self.books_table.setItem(row, 2, QTableWidgetItem(book[2]))
            self.books_table.setItem(row, 3, QTableWidgetItem(book[3]))
            self.books_table.setItem(row, 4, QTableWidgetItem(book[4]))
            try:
                price = float(book[6])
                self.books_table.setItem(row, 5, QTableWidgetItem(f"₽{price:.2f}"))
            except (ValueError, TypeError):
                self.books_table.setItem(row, 5, QTableWidgetItem(str(book[6])))
            self.books_table.setItem(row, 6, QTableWidgetItem(str(book[7])))
            
            # Кнопки управления
            button_layout = QHBoxLayout()
            
            edit_button = QPushButton('Редактировать')
            edit_button.setStyleSheet("""
                QPushButton {
                    background-color: #00FA9A;
                    color: #333;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    min-height: 22px;
                    min-width: 70px;
                    max-width: 85px;
                }
                QPushButton:hover {
                    background-color: #7FFF00;
                }
            """)
            edit_button.clicked.connect(lambda checked, bid=book[0]: self.edit_book_dialog(bid))
            button_layout.addWidget(edit_button)
            
            delete_button = QPushButton('Удалить')
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b6b;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    min-height: 22px;
                    min-width: 60px;
                    max-width: 75px;
                }
                QPushButton:hover {
                    background-color: #ff5252;
                }
            """)
            delete_button.clicked.connect(lambda checked, bid=book[0]: self.delete_book(bid))
            button_layout.addWidget(delete_button)
            
            button_widget = QWidget()
            button_widget.setLayout(button_layout)
            self.books_table.setCellWidget(row, 7, button_widget)
    
    def load_users_table(self):
        """Загружает пользователей в таблицу"""
        users = self.db_manager.get_users()
        
        self.users_table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            self.users_table.setItem(row, 0, QTableWidgetItem(str(user[0])))
            self.users_table.setItem(row, 1, QTableWidgetItem(user[1]))
            self.users_table.setItem(row, 2, QTableWidgetItem(user[2]))
            self.users_table.setItem(row, 3, QTableWidgetItem(user[3]))
            
            # Кнопки управления
            button_layout = QHBoxLayout()
            
            edit_button = QPushButton('Редактировать')
            edit_button.setStyleSheet("""
                QPushButton {
                    background-color: #00FA9A;
                    color: #333;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    min-height: 22px;
                    min-width: 70px;
                    max-width: 85px;
                }
                QPushButton:hover {
                    background-color: #7FFF00;
                }
            """)
            edit_button.clicked.connect(lambda checked, uid=user[0]: self.edit_user_dialog(uid))
            button_layout.addWidget(edit_button)
            
            delete_button = QPushButton('Удалить')
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #ff6b6b;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    min-height: 22px;
                    min-width: 60px;
                    max-width: 75px;
                }
                QPushButton:hover {
                    background-color: #ff5252;
                }
            """)
            delete_button.clicked.connect(lambda checked, uid=user[0]: self.delete_user(uid))
            button_layout.addWidget(delete_button)
            
            button_widget = QWidget()
            button_widget.setLayout(button_layout)
            self.users_table.setCellWidget(row, 4, button_widget)
    
    
    def add_book_dialog(self):
        """Диалог добавления книги"""
        dialog = QDialog(self)
        dialog.setWindowTitle('Добавить книгу')
        dialog.setModal(True)
        dialog.resize(400, 500)
        
        layout = QFormLayout()
        
        # Поля формы
        title_input = QLineEdit()
        author_input = QLineEdit()
        year_input = QSpinBox()
        year_input.setRange(1900, 2030)
        year_input.setValue(2023)
        price_input = QLineEdit()
        stock_input = QSpinBox()
        stock_input.setRange(0, 1000)
        stock_input.setValue(1)
        description_input = QTextEdit()
        description_input.setMaximumHeight(100)
        
        # Выбор жанра и издательства
        genre_combo = QComboBox()
        genres = self.db_manager.get_genres()
        genre_combo.addItems([g[1] for g in genres])
        
        publisher_combo = QComboBox()
        publishers = self.db_manager.get_publishers()
        publisher_combo.addItems([p[1] for p in publishers])
        
        # Акция
        sale_checkbox = QCheckBox('В акции')
        discount_input = QLineEdit()
        discount_input.setPlaceholderText('Акционная цена')
        
        layout.addRow('Название:', title_input)
        layout.addRow('Автор:', author_input)
        layout.addRow('Жанр:', genre_combo)
        layout.addRow('Издательство:', publisher_combo)
        layout.addRow('Год:', year_input)
        layout.addRow('Цена:', price_input)
        layout.addRow('Количество:', stock_input)
        layout.addRow('Описание:', description_input)
        layout.addRow('', sale_checkbox)
        layout.addRow('Акционная цена:', discount_input)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # Получаем ID жанра и издательства
            genre_id = genre_combo.currentIndex() + 1
            publisher_id = publishers[publisher_combo.currentIndex()][0]
            
            # Проверяем обязательные поля
            if not title_input.text().strip():
                QMessageBox.warning(self, 'Ошибка', 'Введите название книги')
                return
            
            if not author_input.text().strip():
                QMessageBox.warning(self, 'Ошибка', 'Введите автора книги')
                return
            
            try:
                price = float(price_input.text())
            except ValueError:
                QMessageBox.warning(self, 'Ошибка', 'Введите корректную цену')
                return
            
            # Обработка акции
            is_on_sale = sale_checkbox.isChecked()
            discount_price = None
            if is_on_sale and discount_input.text().strip():
                try:
                    discount_price = float(discount_input.text())
                except ValueError:
                    QMessageBox.warning(self, 'Ошибка', 'Введите корректную акционную цену')
                    return
            
            # Добавляем книгу
            self.db_manager.add_book(
                title_input.text().strip(),
                author_input.text().strip(),
                genre_id,
                publisher_id,
                year_input.value(),
                price,
                stock_input.value(),
                is_on_sale,
                discount_price,
                'placeholder.png',
                description_input.toPlainText().strip()
            )
            self.load_books_table()
            # Обновляем каталог если он есть
            if self.catalog_widget:
                self.catalog_widget.load_books()
            QMessageBox.information(self, 'Успех', 'Книга добавлена')
    
    def edit_book_dialog(self, book_id):
        """Диалог редактирования книги"""
        # Получаем данные книги
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.title, b.author, b.year, b.price, b.stock_quantity,
                     b.is_on_sale, b.discount_price, b.description, b.genre_id, b.publisher_id, b.cover_image
            FROM books b WHERE b.id = ?
        ''', (book_id,))
        
        book_data = cursor.fetchone()
        conn.close()
        
        if not book_data:
            QMessageBox.warning(self, 'Ошибка', 'Книга не найдена')
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle('Редактировать книгу')
        dialog.setModal(True)
        dialog.resize(400, 500)
        
        layout = QFormLayout()
        
        # Поля формы с текущими данными
        title_input = QLineEdit(book_data[0])
        author_input = QLineEdit(book_data[1])
        year_input = QSpinBox()
        year_input.setRange(1900, 2030)
        year_input.setValue(book_data[2])
        price_input = QLineEdit(str(book_data[3]))
        stock_input = QSpinBox()
        stock_input.setRange(0, 1000)
        stock_input.setValue(book_data[4])
        description_input = QTextEdit(book_data[7] or '')
        description_input.setMaximumHeight(100)
        
        # Выбор жанра и издательства
        genre_combo = QComboBox()
        genres = self.db_manager.get_genres()
        genre_combo.addItems([g[1] for g in genres])
        genre_combo.setCurrentIndex(book_data[8] - 1)  # ID жанра - 1
        
        publisher_combo = QComboBox()
        publishers = self.db_manager.get_publishers()
        publisher_combo.addItems([p[1] for p in publishers])
        publisher_combo.setCurrentIndex(book_data[9] - 1)  # ID издательства - 1
        
        # Сохраняем текущую обложку
        current_cover_image = book_data[10] if book_data[10] else 'placeholder.png'
        
        # Акция
        sale_checkbox = QCheckBox('В акции')
        sale_checkbox.setChecked(bool(book_data[5]))
        discount_input = QLineEdit(str(book_data[6]) if book_data[6] else '')
        discount_input.setPlaceholderText('Акционная цена')
        
        layout.addRow('Название:', title_input)
        layout.addRow('Автор:', author_input)
        layout.addRow('Жанр:', genre_combo)
        layout.addRow('Издательство:', publisher_combo)
        layout.addRow('Год:', year_input)
        layout.addRow('Цена:', price_input)
        layout.addRow('Количество:', stock_input)
        layout.addRow('Описание:', description_input)
        layout.addRow('', sale_checkbox)
        layout.addRow('Акционная цена:', discount_input)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # Получаем ID жанра и издательства
            genre_id = genre_combo.currentIndex() + 1
            publisher_id = publishers[publisher_combo.currentIndex()][0]
            
            # Обновляем книгу
            self.db_manager.update_book(
                book_id,
                title_input.text().strip(),
                author_input.text().strip(),
                genre_id,
                publisher_id,
                year_input.value(),
                float(price_input.text()),
                stock_input.value(),
                sale_checkbox.isChecked(),
                float(discount_input.text()) if discount_input.text().strip() else None,
                current_cover_image,  # Сохраняем текущую обложку
                description_input.toPlainText().strip()
            )
            self.load_books_table()
            # Обновляем каталог если он есть
            if self.catalog_widget:
                self.catalog_widget.load_books()
            QMessageBox.information(self, 'Успех', 'Книга обновлена')
    
    def delete_book(self, book_id):
        """Удаление книги"""
        reply = QMessageBox.question(
            self, 'Подтверждение', 
            'Вы уверены, что хотите удалить эту книгу?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db_manager.delete_book(book_id)
            self.load_books_table()
            # Обновляем каталог если он есть
            if self.catalog_widget:
                self.catalog_widget.load_books()
            QMessageBox.information(self, 'Успех', 'Книга удалена')
    
    def add_user_dialog(self):
        """Диалог добавления пользователя"""
        dialog = QDialog(self)
        dialog.setWindowTitle('Добавить пользователя')
        dialog.setModal(True)
        dialog.resize(300, 200)
        
        layout = QFormLayout()
        
        # Поля формы
        login_input = QLineEdit()
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        full_name_input = QLineEdit()
        role_combo = QComboBox()
        role_combo.addItems(['client', 'manager', 'admin'])
        
        layout.addRow('Логин:', login_input)
        layout.addRow('Пароль:', password_input)
        layout.addRow('ФИО:', full_name_input)
        layout.addRow('Роль:', role_combo)
        
        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            self.db_manager.add_user(
                login_input.text().strip(),
                password_input.text().strip(),
                full_name_input.text().strip(),
                role_combo.currentText()
            )
            self.load_users_table()
            QMessageBox.information(self, 'Успех', 'Пользователь добавлен')
    
    def edit_user_dialog(self, user_id):
        """Диалог редактирования пользователя"""
        QMessageBox.information(self, 'Редактирование', 'Функция редактирования в разработке')
    
    def delete_user(self, user_id):
        """Удаление пользователя"""
        reply = QMessageBox.question(
            self, 'Подтверждение', 
            'Вы уверены, что хотите удалить этого пользователя?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db_manager.delete_user(user_id)
            self.load_users_table()
            QMessageBox.information(self, 'Успех', 'Пользователь удален')
    
    
    def delete_order(self, order_id):
        """Удаление заказа"""
        reply = QMessageBox.question(
            self, 'Подтверждение', 
            'Вы уверены, что хотите удалить этот заказ?',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.db_manager.delete_order(order_id)
            self.load_admin_orders_table()
            QMessageBox.information(self, 'Успех', 'Заказ удален')
    
    def refresh_books_table(self):
        """Обновляет таблицу книг"""
        self.load_books_table()
    
    def refresh_users_table(self):
        """Обновляет таблицу пользователей"""
        self.load_users_table()

class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.current_user = None
        self.db_manager = DatabaseManager()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle('Книжный Мир - Система управления')
        self.setMinimumSize(1200, 800)
        
        # Устанавливаем иконку приложения
        try:
            icon_path = "Модуль 1/Прил_2_ОЗ_КОД 09.02.07-2-2026-М1/Icon.ico"
            self.setWindowIcon(QIcon(icon_path))
        except:
            pass  # Если иконка не найдена, продолжаем без неё
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FFFFFF;
                font-family: 'Times New Roman', serif;
            }
        """)
        
        # Центральный виджет
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Стекированный виджет для переключения между окнами
        self.stacked_widget = QStackedWidget()
        
        # Окно авторизации
        self.login_window = LoginWindow(self)
        self.stacked_widget.addWidget(self.login_window)
        
        # Главное окно (будет создано после авторизации)
        self.main_widget = None
        
        layout = QVBoxLayout()
        layout.addWidget(self.stacked_widget)
        self.central_widget.setLayout(layout)
        
        # Показываем окно авторизации
        self.stacked_widget.setCurrentWidget(self.login_window)
    
    def show_main_window(self):
        """Показывает главное окно после авторизации"""
        if self.main_widget:
            self.stacked_widget.removeWidget(self.main_widget)
        
        self.main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Верхняя панель с информацией о пользователе
        top_panel = QFrame()
        top_panel.setStyleSheet("""
            QFrame {
                background-color: #7FFF00;
                color: #333;
                padding: 15px;
                border-radius: 8px;
                margin: 5px;
            }
        """)
        top_layout = QHBoxLayout()
        
        user_label = QLabel(f"Пользователь: {self.current_user['full_name']} ({self.current_user['role']})")
        user_label.setStyleSheet("color: #333; font-size: 16px; font-weight: bold;")
        top_layout.addWidget(user_label)
        
        top_layout.addStretch()
        
        logout_button = QPushButton('Выйти')
        logout_button.setStyleSheet("""
            QPushButton {
                background-color: #00FA9A;
                color: #333;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                min-height: 32px;
            }
            QPushButton:hover {
                background-color: #7FFF00;
            }
        """)
        logout_button.clicked.connect(self.logout)
        top_layout.addWidget(logout_button)
        
        top_panel.setLayout(top_layout)
        main_layout.addWidget(top_panel)
        
        # Создаем вкладки в зависимости от роли
        if self.current_user['role'] == 'guest':
            # Только каталог для гостя
            self.catalog_widget = CatalogWidget(self.db_manager, self.current_user['role'])
            main_layout.addWidget(self.catalog_widget)
        elif self.current_user['role'] == 'client':
            # Каталог с поиском для клиента
            self.catalog_widget = CatalogWidget(self.db_manager, self.current_user['role'])
            main_layout.addWidget(self.catalog_widget)
        elif self.current_user['role'] == 'manager':
            # Каталог и заказы для менеджера
            tab_widget = QTabWidget()
            tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    border: 2px solid #7FFF00;
                    border-radius: 8px;
                }
                QTabBar::tab {
                    background-color: #7FFF00;
                    color: #333;
                    padding: 10px 20px;
                    margin-right: 2px;
                    border-radius: 8px 8px 0 0;
                }
                QTabBar::tab:selected {
                    background-color: #00FA9A;
                }
            """)
            
            self.catalog_widget = CatalogWidget(self.db_manager, self.current_user['role'])
            self.orders_widget = OrdersWidget(self.db_manager, self.current_user['role'])
            
            tab_widget.addTab(self.catalog_widget, 'Каталог книг')
            tab_widget.addTab(self.orders_widget, 'Заказы')
            
            main_layout.addWidget(tab_widget)
        elif self.current_user['role'] == 'admin':
            # Полный функционал для администратора
            tab_widget = QTabWidget()
            tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    border: 2px solid #7FFF00;
                    border-radius: 8px;
                }
                QTabBar::tab {
                    background-color: #7FFF00;
                    color: #333;
                    padding: 10px 20px;
                    margin-right: 2px;
                    border-radius: 8px 8px 0 0;
                }
                QTabBar::tab:selected {
                    background-color: #00FA9A;
                }
            """)
            
            self.catalog_widget = CatalogWidget(self.db_manager, self.current_user['role'])
            self.orders_widget = OrdersWidget(self.db_manager, self.current_user['role'])
            self.admin_widget = AdminWidget(self.db_manager, self.catalog_widget)
            
            tab_widget.addTab(self.catalog_widget, 'Каталог книг')
            tab_widget.addTab(self.orders_widget, 'Заказы')
            tab_widget.addTab(self.admin_widget, 'Администрирование')
            
            main_layout.addWidget(tab_widget)
        
        self.main_widget.setLayout(main_layout)
        self.stacked_widget.addWidget(self.main_widget)
        self.stacked_widget.setCurrentWidget(self.main_widget)
    
    def logout(self):
        """Выход из системы"""
        self.current_user = None
        self.stacked_widget.setCurrentWidget(self.login_window)

def main():
    app = QApplication(sys.argv)
    
    # Устанавливаем стиль приложения
    app.setStyle('Fusion')
    
    # Создаем базу данных если её нет
    if not os.path.exists('bookstore.db'):
        from create_db import create_database
        create_database()
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
