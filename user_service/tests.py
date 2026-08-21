import json
from flask import url_for
import jwt
from app import create_app
from config import Config
from models import db, User, Cart
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

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
def cart(app):
    """Создание тестовых записей товаров в корзине для тестовой БД"""
    with app.app_context():
        cart1 = Cart(
            id=1,
            user_id=1,
            book_id=1,
            quantity=2
        )
        cart2 = Cart(
            id=2,
            user_id=1,
            book_id=2,
            quantity=1
        )
        cart3 = Cart(
            id=3,
            user_id=1,
            book_id=3,
            quantity=2
        )

        db.session.add_all([cart1, cart2, cart3])
        db.session.commit()

        return [{
            'id': cart1.id,
            'user_id': cart1.user_id,
            'book_id': cart1.book_id,
            'quantity': cart1.quantity,
        }, {
            'id': cart2.id,
            'user_id': cart2.user_id,
            'book_id': cart2.book_id,
            'quantity': cart2.quantity,
        }, {
            'id': cart3.id,
            'user_id': cart3.user_id,
            'book_id': cart3.book_id,
            'quantity': cart3.quantity,
        }]
    
@pytest.fixture
def user(app):
    """Создание тестового пользователя в тестовой БД"""
    with app.app_context():

        user = User(
            id=1,
            full_name="Иван Петров",
            email="test@email.com",
            phone="123"
        )
        user.set_password('password')
        db.session.add(user)
        db.session.commit()

        return {
            'id': user.id,
            'full_name': user.full_name,
            'email': user.email,
            'phone': user.phone
        }

class MockResponse:
    """Мокирование ответов от http-запросов к другим сервисам"""
    def __init__(self, json_data, status_code):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json

    @property
    def text(self):
        return str(self._json)

def generate_token(user_id, secret):
        return jwt.encode({'user_id': user_id}, secret, algorithm='HS256')

class TestUserEndpoints:
    """Тесты эндпоинтов для регистрации, авторизации, выхода и профиля"""

    def test_get_user_by_id(self, client, user):
        """Тест получения пользователя по ID"""
        response = client.get(f'/users/{user["id"]}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['email'] == user['email']
        assert data['username'] == user['full_name']

    def test_get_user_by_id_notexisting(self, client, user):
        """Тест получения несуществующего пользователя по ID"""
        response = client.get('/users/999')
        assert response.status_code == 404

    def test_register(self, client, app):
        """Тест регистрации нового пользователя"""
        with app.app_context():
            response = client.post('/register', data={
                'full_name': 'Василий Васильев',
                'email': 'newuser@gmail.com',
                'phone': '9999999999',
                'password': 'newpassword'
            }, follow_redirects=True)
            
            assert response.status_code == 200
            user = User.query.filter_by(email='newuser@gmail.com').first()
            assert user is not None
            assert user.check_password('newpassword')

    def test_register_duplicate_email(self, client, user):
        """Тест регистрации с уже существующим email"""
        response = client.post('/register', data={
            'full_name': 'Иван Петров',
            'email': user['email'],
            'phone': '0000000000',
            'password': 'password'
        }, follow_redirects=True)

        assert 'Email уже зарегистрирован' in response.data.decode('utf-8')

    def test_register_duplicate_phone(self, client, user):
        """Тест регистрации с уже существующим телефоном"""
        response = client.post('/register', data={
            'full_name': 'Иван Петров',
            'email': 'allo@gmail.com',
            'phone': user['phone'],
            'password': 'password'
        }, follow_redirects=True)

        assert 'Телефон уже зарегистрирован' in response.data.decode('utf-8')

    def test_login_success(self, client, user):
        """Тест успешного логина"""
        response = client.post('/login', data={
            'email': user['email'],
            'password': 'password'
        }, follow_redirects=False)

        assert response.status_code == 302
        assert 'auth_token' in response.headers.get('Set-Cookie', '')

    def test_login_invalid_credentials(self, client, user):
        """Тест входа с неправильными данными"""
        response = client.post('/login', data={
            'email': user['email'],
            'password': 'wrongpassword'
        }, follow_redirects=True)
        # Переход на страницу авторизации
        assert 'Нет аккаунта?' in response.data.decode('utf-8')

    def test_profile_with_invalid_token(self, client, user):
        """Тест авторизации (доступа к профилю) с истекшим токеном в cookie-файлах"""
        
        invalid_token = "notvalidtoken"
        client.set_cookie(domain='localhost', key='auth_token', value=invalid_token)

        response = client.get('/profile', follow_redirects=True)

        assert response.status_code == 200
        assert 'Нет аккаунта?' in response.data.decode('utf-8')

    def test_profile_access(self, client, user):
        """Тест доступа к профилю авторизованного пользователя"""
        token = generate_token(user['id'], TestConfig.SECRET_KEY)
        client.set_cookie(domain='localhost', key='auth_token', value=token)

        response = client.get('/profile')
        assert response.status_code == 200
        assert 'Иван Петров' in response.data.decode('utf-8')

    def test_profile_no_token(self, client):
        """Тест доступа к профилю без авторизации"""
        response = client.get('/profile', follow_redirects=True)
        # Переход на страницу авторизации
        assert 'Нет аккаунта?' in response.data.decode('utf-8')

    def test_logout(self, client, user):
        """Тест выхода из аккаунта"""
        token = generate_token(user['id'], TestConfig.SECRET_KEY)
        client.set_cookie(domain='localhost', key='auth_token', value=token)

        response = client.post('/logout', follow_redirects=False)
        assert response.status_code == 302
        assert 'auth_token=;' in response.headers.get('Set-Cookie', '')


class TestCartEndpoints:
    """Тесты эндпоинтов для работы с корзиной"""

    def test_add_to_cart(self, client, user):
        """Добавление товара в корзину"""
        response = client.post('/cart/add', json={
            'book_id': 1,
            'user_id': user['id']
        }, follow_redirects=True)
        
        assert response.status_code == 200
        with client.application.app_context():
            item = Cart.query.filter_by(user_id=user['id'], book_id=1).first()
            assert item is not None
            assert item.quantity == 1

    @patch('routes.get_books')
    def test_api_cart(self, mock_get_books, client, user, cart):
        """Получение содержимого корзины"""
        token = generate_token(user['id'], TestConfig.SECRET_KEY)
        client.set_cookie(domain='localhost', key='auth_token', value=token)

        # Мокирование ответа с книгами
        mock_get_books.return_value = [
            {'id': 1, 'title': 'Война и мир', 'author': 'Лев Толстой', 'price': 899.99},
            {'id': 2, 'title': 'Мёртвые души', 'author': 'Николай Гоголь', 'price': 579.99},
            {'id': 3, 'title': 'Анна Каренина', 'author': 'Лев Толстой', 'price': 759.99}
        ]

        response = client.get('/api/cart')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 3


    def test_clear_cart(self, client, user, cart):
        """Очистка корзины"""
        token = generate_token(user['id'], TestConfig.SECRET_KEY)
        client.set_cookie(domain='localhost', key='auth_token', value=token)

        response = client.delete('/api/cart/clear', follow_redirects=False)
        assert response.status_code == 302
        with client.application.app_context():
            remaining = Cart.query.filter_by(user_id=user['id']).count()
            assert remaining == 0


    def test_remove_from_cart(self, client, user, cart):
        """Удаление товара из корзины"""
        response = client.post(f'/cart/remove/{user['id']}/{cart[2]['book_id']}', follow_redirects=True)
        assert response.status_code == 200

        with client.application.app_context():
            item = db.session.get(Cart, cart[2]['id'])
            assert item is None


    def test_edit_cart_item_increase(self, client, user, cart):
        """Увеличение количества в корзине"""
        response = client.post(f'/cart/edit/{cart[1]['id']}/inc', follow_redirects=True)
        assert response.status_code == 200

        with client.application.app_context():
            item = db.session.get(Cart, cart[1]['id'])
            assert item.quantity == 2


    def test_edit_cart_item_decrease_and_delete(self, client, user, cart):
        """Уменьшение количества и удаление при 1"""
        response = client.post(f'/cart/edit/{cart[0]['id']}/dec', follow_redirects=True)
        assert response.status_code == 200

        with client.application.app_context():
            item = db.session.get(Cart, cart[0]['id'])
            assert item.quantity == 1

        response = client.post(f'/cart/edit/{cart[0]['id']}/dec', follow_redirects=True)
        assert response.status_code == 200

        with client.application.app_context():
            item = db.session.get(Cart, cart[0]['id'])
            assert item is None

if __name__ == '__main__':
    pytest.main([__file__, '-v'])