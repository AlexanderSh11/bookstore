from app import create_app
from config import Config
from models import db, ProductCatalog, Book, Genre
import pytest
import json

class TestConfig(Config):
    """Мокирование базы данных для юнит-тестирования (подключение к SQLite)"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test_secret'

@pytest.fixture
def app():
    """Создание приложения с тестовой конфигурацией. Создание таблиц и их удаление после каждого теста"""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def books(app):
    """Создание тестовых записей в тестовые таблицы БД"""
    with app.app_context():
        genre1 = Genre(name="Классика")
        db.session.add(genre1)
        db.session.commit()

        book1 = Book(title="Война и мир", author="Лев Толстой", price=899.99, year=1869, description="Эпический роман о русском обществе во время наполеоновских войн", publisher="Русский вестник", genre=genre1)
        book2 = Book(title="Мёртвые души", author="Николай Гоголь", price=579.99, year=1842, description="Психологический роман о русском офицере Печорине", publisher="Отечественные записки", genre=genre1)
        book3 = Book(title="Анна Каренина", author="Лев Толстой", price=759.99, year=1877, description="Трагическая история любви замужней женщины", publisher="Русский вестник", genre=genre1)
        db.session.add_all([book1, book2, book3])
        db.session.commit()
        return [book1, book2, book3]

class TestProductCatalog:
    """Тесты для класса ProductCatalog"""
    
    def test_get_all_books_no_sort(self, client, books):
        """Тест получения всех книг"""
        books_ = ProductCatalog.get_all_books()
        assert len(books_) == 3
        assert isinstance(books_[0], Book)
    
    def test_get_all_books_sort_by_title(self, client, books):
        """Тест сортировки по названию"""
        books_ = ProductCatalog.get_all_books(sort_by='title')
        titles = [book.title for book in books_]
        assert titles == ['Анна Каренина', 'Война и мир', 'Мёртвые души']
    
    def test_get_all_books_sort_by_author(self, client, books):
        """Тест сортировки по автору"""
        books_ = ProductCatalog.get_all_books(sort_by='author')
        authors = [book.author for book in books_]
        assert authors == ['Лев Толстой', 'Лев Толстой', 'Николай Гоголь']
    
    def test_get_all_books_sort_by_price(self, client, books):
        """Тест сортировки по цене"""
        books_ = ProductCatalog.get_all_books(sort_by='price')
        prices = [book.price for book in books_]
        assert prices == [579.99, 759.99, 899.99]
    
    def test_search_books_by_title(self, client, books):
        """Тест поиска по названию"""
        books_ = ProductCatalog.search_books('ир', None)
        assert len(books_) == 1
        title = books_[0].title
        assert title == 'Война и мир'
    
    def test_search_books_by_author(self, client, books):
        """Тест поиска по автору"""
        books_ = ProductCatalog.search_books('лев', None)
        assert len(books_) == 2
        authors = {book.author for book in books_}
        assert authors == {'Лев Толстой'}
    
    def test_search_books_with_sorting(self, client, books):
        """Тест поиска с сортировкой"""
        books_ = ProductCatalog.search_books('Лев', 'price')
        prices = [book.price for book in books_]
        assert prices == [759.99, 899.99]
    
    def test_get_book_by_id_existing(self, client, books):
        """Тест получения книги по существующему ID"""
        book = ProductCatalog.get_book_by_id(1)
        assert book is not None
        assert book.title == 'Война и мир'
    
    def test_get_book_by_id_nonexistent(self, client, books):
        """Тест получения книги по несуществующему ID"""
        book = ProductCatalog.get_book_by_id(999)
        assert book is None

class TestEndpoints:
    """Тесты эндпоинтов приложения"""
    
    def test_catalog_route(self, client, books):
        """Тест главной страницы каталога"""
        response = client.get('/')
        assert response.status_code == 200
    
    def test_catalog_route_sorted(self, client, books):
        """Тест каталога с сортировкой"""
        response = client.get('/?sort_by=price')
        assert response.status_code == 200
    
    def test_search_route(self, client, books):
        """Тест поиска"""
        response = client.get('/search?q=анна')
        assert response.status_code == 200
        assert 'Анна Каренина' in response.data.decode('utf-8')
    
    def test_search_route_empty(self, client, books):
        """Тест поиска с пустым запросом"""
        response = client.get('/search?q=')
        assert response.status_code == 200
        assert 'Книги не найдены' in response.data.decode('utf-8')
    
    def test_search_route_sorted(self, client, books):
        """Тест поиска с сортировкой"""
        response = client.get('/search?q=н&sort_by=price')
        assert response.status_code == 200
        assert 'Анна Каренина' in response.data.decode('utf-8')
        assert 'Война и мир' in response.data.decode('utf-8')
    
    def test_book_details_existing(self, client, books):
        """Тест страницы деталей существующей книги"""
        response = client.get('/book/1')
        assert response.status_code == 200
        assert 'Война и мир' in response.data.decode('utf-8')
    
    def test_book_details_notexisting(self, client, books):
        """Тест страницы деталей несуществующей книги"""
        response = client.get('/book/999')
        assert response.status_code == 404
    
    def test_get_books_by_ids(self, client, books):
        """Тест получения книг по ID"""
        response = client.get('/books?ids=1,2,3')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data) == 3
        assert data[0]['title'] == 'Война и мир'
        assert data[1]['title'] == 'Мёртвые души'
        assert data[2]['title'] == 'Анна Каренина'
    
    def test_get_books_empty_ids(self, client, books):
        """Тест получения книг без указания ID"""
        response = client.get('/books')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_get_books_invalid_ids(self, client, books):
        """Тест получения книг с невалидными ID"""
        response = client.get('/books?ids=1,invalid,3')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

if __name__ == '__main__':
    pytest.main([__file__, '-v'])