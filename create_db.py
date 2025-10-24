#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создание базы данных для системы "Книжный Мир"
"""

import sqlite3
import os

def create_database():
    """Создает базу данных SQLite с таблицами согласно требованиям"""
    
    # Создаем подключение к базе данных
    conn = sqlite3.connect('bookstore.db')
    cursor = conn.cursor()
    
    print("Создание базы данных...")
    
    # Создаем таблицы согласно нормализации до 3НФ
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        full_name VARCHAR(100) NOT NULL,
        role VARCHAR(20) NOT NULL CHECK (role IN ('guest', 'client', 'manager', 'admin')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица издательств
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS publishers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица жанров
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS genres (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(50) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица пунктов выдачи
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pickup_points (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) NOT NULL,
        address VARCHAR(255) NOT NULL,
        phone VARCHAR(20),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица книг
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(255) NOT NULL,
        author VARCHAR(100) NOT NULL,
        genre_id INTEGER NOT NULL,
        publisher_id INTEGER NOT NULL,
        year INTEGER NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        stock_quantity INTEGER DEFAULT 0,
        is_on_sale BOOLEAN DEFAULT FALSE,
        discount_price DECIMAL(10,2),
        cover_image VARCHAR(255),
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (genre_id) REFERENCES genres(id),
        FOREIGN KEY (publisher_id) REFERENCES publishers(id)
    )
    ''')
    
    # Таблица заказов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        pickup_point_id INTEGER NOT NULL,
        status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'ready', 'completed', 'cancelled')),
        total_amount DECIMAL(10,2) NOT NULL,
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completion_date TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (pickup_point_id) REFERENCES pickup_points(id)
    )
    ''')
    
    # Таблица позиций заказа
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        price DECIMAL(10,2) NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(id),
        FOREIGN KEY (book_id) REFERENCES books(id)
    )
    ''')
    
    # Создаем индексы для оптимизации
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_title ON books(title)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_author ON books(author)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)')
    
    print("Таблицы созданы успешно")
    
    # Добавляем тестовые данные
    add_test_data(cursor)
    
    conn.commit()
    conn.close()
    
    print("База данных создана: bookstore.db")

def add_test_data(cursor):
    """Добавляет тестовые данные в базу"""
    
    print("Добавление тестовых данных...")
    
    # Добавляем пользователей
    users_data = [
        ('a.orlova@bookworld.ru', 'Ah7kLp', 'Орлова Алина Викторовна', 'admin'),
        ('d.volkov@bookworld.ru', 'Bm2qR9', 'Волков Денис Сергеевич', 'admin'),
        ('i.semenova@bookworld.ru', 'Cn8tWx', 'Семенова Ирина Олеговна', 'manager'),
        ('m.kozlov@bookworld.ru', 'Df4yUz', 'Козлов Максим Игоревич', 'manager'),
        ('t.nikolaeva@bookworld.ru', 'Eg6vAs', 'Николаева Татьяна Петровна', 'manager'),
        ('a.belov@example.com', 'Fh9jQw', 'Белов Алексей Дмитриевич', 'client'),
        ('m.sokolova@example.com', 'Gi1kEx', 'Соколова Мария Андреевна', 'client'),
        ('i.morozov@example.com', 'Hj2lFy', 'Морозов Иван Павлович', 'client'),
        ('o.lebedeva@example.com', 'Kk3mGz', 'Лебедева Ольга Васильевна', 'client')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO users (login, password, full_name, role) 
        VALUES (?, ?, ?, ?)
    ''', users_data)
    
    # Добавляем издательства
    publishers_data = [
        ('Эксмо',),
        ('АСТ',),
        ('Питер',),
        ('Манн, Иванов и Фербер',),
        ('Альпина Паблишер',),
        ('Азбука',),
        ('Махаон',),
        ('София',),
        ('Иностранка',),
        ('Дрофа',)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO publishers (name) VALUES (?)
    ''', publishers_data)
    
    # Добавляем жанры
    genres_data = [
        ('Классика',),
        ('Антиутопия',),
        ('Детская',),
        ('Детектив',),
        ('Фэнтези',),
        ('Роман',),
        ('Фантастика',),
        ('Научная фантастика',)
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO genres (name) VALUES (?)
    ''', genres_data)
    
    # Добавляем пункты выдачи
    pickup_points_data = [
        ('Пункт выдачи 1', 'г. Москва, ул. Тверская, д. 10', '+7 (495) 123-45-67'),
        ('Пункт выдачи 2', 'г. Москва, пр-т Мира, д. 25', '+7 (495) 234-56-78'),
        ('Пункт выдачи 3', 'г. Санкт-Петербург, Невский пр-т, д. 45', '+7 (812) 345-67-89'),
        ('Пункт выдачи 4', 'г. Санкт-Петербург, ул. Садовая, д. 12', '+7 (812) 456-78-90'),
        ('Пункт выдачи 5', 'г. Екатеринбург, ул. Ленина, д. 33', '+7 (343) 567-89-01')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO pickup_points (name, address, phone) VALUES (?, ?, ?)
    ''', pickup_points_data)
    
    # Добавляем книги
    books_data = [
        ('Мастер и Маргарита', 'Михаил Булгаков', 1, 1, 1967, 450.00, 12, False, None, '1.png', 'Бессмертное произведение русской литературы, полное мистики и философских размышлений.'),
        ('1984', 'Джордж Оруэлл', 2, 2, 1949, 380.00, 8, False, None, '2.png', 'Знаменитая антиутопия, рассказывающая о тоталитарном обществе под постоянным контролем.'),
        ('Преступление и наказание', 'Фёдор Достоевский', 1, 3, 1866, 520.00, 15, False, None, '3.png', 'Глубокий психологический роман о преступлении и моральных муках раскаяния.'),
        ('Три товарища', 'Эрих Мария Ремарк', 6, 4, 1936, 420.00, 7, False, None, '4.png', 'Трогательная история о дружбе и любви на фоне сложного времени в Германии.'),
        ('Маленький принц', 'Антуан де Сент-Экзюпери', 3, 5, 1943, 350.00, 20, False, None, '5.png', 'Философская сказка для детей и взрослых, говорящая о самом важном в жизни.'),
        ('Шерлок Холмс (сборник)', 'Артур Конан Дойл', 4, 6, 1892, 480.00, 9, False, None, '6.png', 'Знаменитые расследования великого сыщика Шерлока Холмса и его друга доктора Ватсона.'),
        ('Гарри Поттер и философский камень', 'Джоан Роулинг', 5, 7, 1997, 550.00, 14, False, None, '7.png', 'Первая книга культовой серии о юном волшебнике Гарри Поттере.'),
        ('Убийство в Восточном экспрессе', 'Агата Кристи', 4, 8, 1934, 400.00, 11, False, None, '8.png', 'Одно из самых известных дел Эркюля Пуаро, разворачивающееся в поезде.'),
        ('Война и мир (том 1)', 'Лев Толстой', 1, 9, 1869, 600.00, 6, False, None, '9.png', 'Монументальный роман-эпопея, охватывающий судьбы людей на фоне войны с Наполеоном.'),
        ('Алхимик', 'Пауло Коэльо', 6, 10, 1988, 320.00, 18, False, None, '10.png', 'Притча о юном пастухе Сантьяго, отправившемся на поиски своего сокровища и предназначения.'),
        ('Портрет Дориана Грея', 'Оскар Уайльд', 1, 1, 1890, 280.00, 5, False, None, 'placeholder.png', 'История о красоте, разврате и таинственном портрете, стареющем вместо своего владельца.'),
        ('Над пропастью во ржи', 'Джером Сэлинджер', 6, 2, 1951, 350.00, 10, False, None, 'placeholder.png', 'Роман о подростковом бунте и поиске себя в лицемерном взрослом мире.'),
        ('Игра Эндера', 'Орсон Скотт Кард', 7, 3, 1985, 420.00, 0, False, None, 'placeholder.png', 'История одаренного мальчика, готовящегося к защите Земли от инопланетной угрозы.'),
        ('Автостопом по галактике', 'Дуглас Адамс', 7, 4, 1979, 380.00, 13, False, None, 'placeholder.png', 'Юмористическая фантастика о невероятных приключениях землянина Артура Дента.'),
        ('Цветы для Элджернона', 'Дэниел Киз', 6, 5, 1966, 400.00, 8, False, None, 'placeholder.png', 'Трогательная история человека, участвующего в эксперименте по повышению интеллекта.')
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', books_data)
    
    # Добавляем тестовые заказы
    orders_data = [
        (6, 1, 'pending', 850.00, '2024-01-15 10:30:00', None),  # Белов Алексей
        (7, 2, 'processing', 1200.00, '2024-01-16 14:20:00', None),  # Соколова Мария
        (8, 3, 'ready', 650.00, '2024-01-17 09:15:00', None),  # Морозов Иван
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO orders (user_id, pickup_point_id, status, total_amount, order_date, completion_date) 
        VALUES (?, ?, ?, ?, ?, ?)
    ''', orders_data)
    
    # Добавляем позиции заказов
    order_items_data = [
        (1, 1, 1, 450.00),  # Заказ 1: Мастер и Маргарита
        (1, 2, 1, 380.00),  # Заказ 1: 1984
        (2, 3, 2, 520.00),  # Заказ 2: Преступление и наказание
        (2, 4, 1, 420.00),  # Заказ 2: Три товарища
        (3, 5, 1, 350.00),  # Заказ 3: Маленький принц
        (3, 6, 1, 480.00),  # Заказ 3: Шерлок Холмс
    ]
    
    cursor.executemany('''
        INSERT OR IGNORE INTO order_items (order_id, book_id, quantity, price) 
        VALUES (?, ?, ?, ?)
    ''', order_items_data)
    
    print("Тестовые данные добавлены")

if __name__ == "__main__":
    create_database()