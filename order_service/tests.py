import json
import jwt
from app import create_app
from config import Config
from models import db, Order, ItemsInOrder, OrderStatus, Payment
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
def order(app):
    """Создание тестовых записей для тестовой БД"""
    with app.app_context():

        status1 = OrderStatus(id=1, name='Оформлен')
        status2 = OrderStatus(id=2, name='Доставлен')
        status3 = OrderStatus(id=3, name='Отменен')
        status4 = OrderStatus(id=4, name='Получен')
        payment1 = Payment(id=1, name='Наличными, при получении')
        payment2 = Payment(id=2, name='Банковской картой, при получении')
        db.session.add_all([status1, status2, status3, status4, payment1, payment2])
        db.session.commit()

        order = Order(
            id=1,
            user_id=1,
            checkout_date=datetime.now(),
            delivery_date=datetime.now() + timedelta(days=7),
            payment_id=1,
            address='г. Томск, ул. Пушкина, 10',
            status_id=1
        )
        db.session.add(order)
        db.session.flush()

        item1 = ItemsInOrder(
            order_id=order.id,
            user_id=1,
            book_id=1,
            quantity=2
        )
        item2 = ItemsInOrder(
            order_id=order.id,
            user_id=1,
            book_id=2,
            quantity=1
        )

        db.session.add_all([item1, item2])
        db.session.commit()

        return order
    
@pytest.fixture
def user(app):
    """Мокирование пользователя"""
    return {
        'id': 1,
        'full_name': 'Иван Петров',
        'email': 'test@example.com',
        'phone': '123'
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

class TestEndpoints:
    """Тесты эндпоинтов приложения"""
    
    def test_orders_route_success(self, client, order, user):
        """Тест страницы заказов авторизованного пользователя"""

        # Генерация access-токена для мокированного пользователя, его сохранение в cookie-файлах
        token = jwt.encode({'user_id': user['id']}, client.application.config['SECRET_KEY'], algorithm='HS256')
        client.set_cookie(domain='localhost', key='auth_token', value=token)

        # Мокирование GET-запроса для проверки авторизации пользователя
        with patch('routes.requests.get') as mock_get:
            mock_get.return_value = MockResponse(json_data=user, status_code=200)

            response = client.get('/orders')
            assert response.status_code == 200
            assert 'Заказы' in response.data.decode('utf-8')

    def test_orders_route_unauthorized(self, client, order):
        """Тест страницы заказов без авторизации"""
        response = client.get('/order/1')
        assert response.status_code == 401
    
    @patch('routes.requests.get')
    def test_order_details_existing(self, mock_get, client, order, user):
        """Тест страницы деталей существующего заказа"""

        # Мокирование нескольких GET-запросов для получения пользователя, книг в заказе
        def mock_requests_get(url, *args, **kwargs):
            if url.startswith('http://localhost:5001/users/'):
                return MockResponse(json_data=user, status_code=200)
            elif url.startswith('http://localhost:5000/books'):
                return MockResponse(json_data=[
                    {'id': 1, 'title': 'Война и мир', 'price': 899.99},
                    {'id': 2, 'title': 'Анна Каренина', 'price': 759.99}
                ], status_code=200)
            else:
                return MockResponse(json_data={'error': 'not found'}, status_code=404)
        mock_get.side_effect = mock_requests_get

        # Генерация access-токена для мокированного пользователя, его сохранение в cookie-файлах
        token = jwt.encode({'user_id': user['id']}, client.application.config['SECRET_KEY'], algorithm='HS256')
        client.set_cookie(domain='localhost', key='auth_token', value=token)

        response = client.get('/order/1')
        assert response.status_code == 200
        assert 'Война и мир' in response.data.decode('utf-8')
    
    def test_order_details_notexisting(self, client, order):
        """Тест страницы деталей несуществующего заказа"""
        response = client.get('/order/999')
        assert response.status_code == 404

    def test_cancel_order_existing(self, client, order):
        """Тест отмены существующего заказа"""
        response = client.post(f'/order/cancel/1', follow_redirects=True)
        assert response.status_code == 200

    def test_cancel_order_notexisting(self, client):
        """Тест отмены несуществующего заказа"""
        response = client.post('/order/cancel/999', follow_redirects=True)
        assert response.status_code == 200


    @patch('routes.requests.get')
    @patch('routes.requests.delete')
    def test_checkout_success(self, mock_delete, mock_get, client, user):
        """Тест успешного оформления заказа"""

        # Мокирование корзины (запрос на получение пользователя, корзины и книг в ней)
        def mock_requests_get(url, *args, **kwargs):
            if url.startswith('http://localhost:5001/users/'):
                return MockResponse(json_data=user, status_code=200)
            elif url.startswith('http://localhost:5001/api/cart'):
                return MockResponse(json_data=[{'book_id': 1, 'quantity': 2}], status_code=200)
            elif url.startswith('http://localhost:5000/books'):
                return MockResponse(json_data=[
                    {'id': 1, 'title': 'Война и мир', 'price': 899.99},
                    {'id': 2, 'title': 'Анна Каренина', 'price': 759.99}
                ], status_code=200)
            else:
                return MockResponse(json_data={'error': 'not found'}, status_code=404)
        mock_get.side_effect = mock_requests_get

        # Мокирование запроса на отчистку корзины после оформления заказа
        mock_delete.return_value = MockResponse(json_data={'message': 'Cart cleared'}, status_code=200)

        # Генерация access-токена для мокированного пользователя, его сохранение в cookie-файлах
        token = jwt.encode({'user_id': user['id']}, client.application.config['SECRET_KEY'], algorithm='HS256')
        client.set_cookie(domain='localhost', key='auth_token', value=token)

        data = {
            'payment_method': 1,
            'shipping_address': 'ул. Пушкина, д. Колотушкина'
        }

        # POST-запрос оформления заказа
        response = client.post('/checkout', json=data, follow_redirects=True)
        assert response.status_code == 200
        assert 'Заказы' in response.data.decode('utf-8')

    def test_checkout_unauthorized(self, client):
        """Тест оформления заказа без токена"""
        response = client.post('/checkout', json={}, follow_redirects=True)
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data.get('error') == 'Требуется авторизация'

    @patch('routes.requests.get')
    def test_checkout_empty_cart(self, mock_get, client, user):
        """Тест оформления заказа с пустой корзиной"""

        # Мокирование пустой корзины (запрос на получение пользователя, пустой корзины)
        mock_get.side_effect = [
            MockResponse(json_data=user, status_code=200),
            MockResponse(json_data=[], status_code=200)
        ]

        token = jwt.encode({'user_id': user['id']}, client.application.config['SECRET_KEY'], algorithm='HS256')
        client.set_cookie(domain='localhost', key='auth_token', value=token)

        data = {
            'payment_method': 1,
            'shipping_address': 'ул. Пушкина, д. Колотушкина'
        }

        # POST-запрос оформления заказа из пустой корзины
        response = client.post('/checkout', json=data)
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data.get('error') == 'Корзина пуста'

if __name__ == '__main__':
    pytest.main([__file__, '-v'])