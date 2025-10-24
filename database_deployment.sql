-- SQL-скрипт для развертывания базы данных "Книжный Мир"
-- Создание таблиц

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('guest', 'client', 'manager', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица издательств
CREATE TABLE IF NOT EXISTS publishers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица жанров
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица пунктов выдачи
CREATE TABLE IF NOT EXISTS pickup_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    address VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица книг
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
);

-- Таблица заказов
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
);

-- Таблица позиций заказа
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (book_id) REFERENCES books(id)
);

-- Создание индексов
CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_author ON books(author);
CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);

-- Вставка данных

-- Пользователи
INSERT OR IGNORE INTO users (login, password, full_name, role) VALUES ('a.orlova@bookworld.ru', 'Ah7kLp', 'Орлова Алина Викторовна', 'admin');
INSERT OR IGNORE INTO users (login, password, full_name, role) VALUES ('d.volkov@bookworld.ru', 'Bm2qR9', 'Волков Денис Сергеевич', 'admin');
INSERT OR IGNORE INTO users (login, password, full_name, role) VALUES ('i.semenova@bookworld.ru', 'Cn8tWx', 'Семенова Ирина Олеговна', 'manager');
INSERT OR IGNORE INTO users (login, password, full_name, role) VALUES ('m.kozlov@bookworld.ru', 'Df4yUz', 'Козлов Максим Игоревич', 'manager');
INSERT OR IGNORE INTO users (login, password, full_name, role) VALUES ('t.nikolaeva@bookworld.ru', 'Eg6vAs', 'Николаева Татьяна Петровна', 'manager');
INSERT OR IGNORE INTO users (login, password, full_name, role) VALUES ('a.belov@example.com', 'Fh9jQw', 'Белов Алексей Дмитриевич', 'client');
INSERT OR IGNORE INTO users (login, password, full_name, role) VALUES ('m.sokolova@example.com', 'Gi1kEx', 'Соколова Мария Андреевна', 'client');
INSERT OR IGNORE INTO users (login, password, full_name, role) VALUES ('i.morozov@example.com', 'Hj2lFy', 'Морозов Иван Павлович', 'client');
INSERT OR IGNORE INTO users (login, password, full_name, role) VALUES ('o.lebedeva@example.com', 'Kk3mGz', 'Лебедева Ольга Васильевна', 'client');

-- Издательства
INSERT OR IGNORE INTO publishers (name) VALUES ('Эксмо');
INSERT OR IGNORE INTO publishers (name) VALUES ('АСТ');
INSERT OR IGNORE INTO publishers (name) VALUES ('Питер');
INSERT OR IGNORE INTO publishers (name) VALUES ('Манн, Иванов и Фербер');
INSERT OR IGNORE INTO publishers (name) VALUES ('Альпина Паблишер');
INSERT OR IGNORE INTO publishers (name) VALUES ('ACT');
INSERT OR IGNORE INTO publishers (name) VALUES ('Азбука');
INSERT OR IGNORE INTO publishers (name) VALUES ('Махаон');
INSERT OR IGNORE INTO publishers (name) VALUES ('София');
INSERT OR IGNORE INTO publishers (name) VALUES ('Иностранка');

-- Жанры
INSERT OR IGNORE INTO genres (name) VALUES ('Художественная литература');
INSERT OR IGNORE INTO genres (name) VALUES ('Научная литература');
INSERT OR IGNORE INTO genres (name) VALUES ('Детская литература');
INSERT OR IGNORE INTO genres (name) VALUES ('Техническая литература');
INSERT OR IGNORE INTO genres (name) VALUES ('Справочная литература');
INSERT OR IGNORE INTO genres (name) VALUES ('Классика');
INSERT OR IGNORE INTO genres (name) VALUES ('Антиутопия');
INSERT OR IGNORE INTO genres (name) VALUES ('Детская');
INSERT OR IGNORE INTO genres (name) VALUES ('Детектив');
INSERT OR IGNORE INTO genres (name) VALUES ('Фэнтези');
INSERT OR IGNORE INTO genres (name) VALUES ('Роман');
INSERT OR IGNORE INTO genres (name) VALUES ('Фантастика');
INSERT OR IGNORE INTO genres (name) VALUES ('Научная фантастика');

-- Пункты выдачи
INSERT OR IGNORE INTO pickup_points (name, address, phone) VALUES ('Центральный офис', 'ул. Ленина, 1', '+7 (495) 123-45-67');
INSERT OR IGNORE INTO pickup_points (name, address, phone) VALUES ('ТЦ "Мега"', 'ул. Мира, 15', '+7 (495) 234-56-78');
INSERT OR IGNORE INTO pickup_points (name, address, phone) VALUES ('ТЦ "Галерея"', 'пр. Победы, 25', '+7 (495) 345-67-89');

-- Книги
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Мастер и Маргарита', 'Михаил Булгаков', 6, 1, 2020, 450, 12, 1, 380, '1.png', 'Бессмертное произведение русской литературы, полное мистики и философских размышлений');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('1984', 'Джордж Оруэлл', 7, 6, 2019, 520, 8, 0, NULL, '2.png', 'Знаменитая антиутопия, рассказывающая о тоталитарном обществе под постоянным контролем');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Преступление и наказание', 'Федор Достоевский', 6, 1, 2021, 480, 15, 1, 430, '3.png', 'Глубокий психологический роман о преступлении и моральных муках раскаяния');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Три товарища', 'Эрих Мария Ремарк', 6, 7, 2018, 590, 7, 0, NULL, '4.png', 'Трогательная история о дружбе и любви на фоне сложного времени в Германии');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Маленький принц', 'Антуан де Сент-Экзюпери', 8, 8, 2022, 380, 20, 1, 340, '5.png', 'Философская сказка для детей и взрослых, говорящая о самом важном в жизни');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Шерлок Холмс (сборник)', 'Артур Конан Дойл', 9, 1, 2020, 650, 9, 1, 590, '6.png', 'Знаменитые расследования великого сыщика Шерлока Холмса и его друга доктора Ватсона');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Гарри Поттер и философский камень', 'Джоан Роулинг', 10, 8, 2021, 720, 14, 0, NULL, '7.png', 'Первая книга культовой серии о юном волшебнике Гарри Поттере');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Убийство в Восточном экспрессе', 'Агата Кристи', 9, 1, 2019, 430, 11, 1, 390, '8.png', 'Одно из самых известных дел Эркюля Пуаро, разворачивающееся в поезде');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Война и мир (том 1)', 'Лев Толстой', 6, 6, 2021, 550, 6, 0, NULL, '9.png', 'Монументальный роман-эпопея, охватывающий судьбы людей на фоне войны с Наполеоном');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Алхимик', 'Пауло Коэльо', 11, 9, 2020, 480, 18, 1, 430, '10.png', 'Притча о юном пастухе Сантьяго, отправившемся на поиски своего сокровища и предназначения');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Портрет Дориана Грея', 'Оскар Уайльд', 6, 1, 2018, 460, 5, 0, NULL, 'placeholder.png', 'История о красоте, разврате и таинственном портрете, стареющем вместо своего владельца');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Над пропастью во ржи', 'Джером Сэлинджер', 6, 7, 2019, 390, 10, 1, 350, 'placeholder.png', 'Роман о подростковом бунте и поиске себя в лицемерном взрослом мире');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Игра Эндера', 'Орсон Скотт Кард', 12, 1, 2021, 540, 0, 0, NULL, 'placeholder.png', 'История одаренного мальчика, готовящегося к защите Земли от инопланетной угрозы');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Автостопом по галактике', 'Дуглас Адамс', 12, 6, 2020, 510, 13, 1, 460, 'placeholder.png', 'Юмористическая фантастика о невероятных приключениях землянина Артура Дента');
INSERT OR IGNORE INTO books (title, author, genre_id, publisher_id, year, price, stock_quantity, is_on_sale, discount_price, cover_image, description) VALUES ('Цветы для Элджернона', 'Дэниел Киз', 13, 10, 2021, 470, 8, 1, 420, 'placeholder.png', 'Трогательная история человека, участвующего в эксперименте по повышению интеллекта');
