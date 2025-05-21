from flask import Flask, flash, jsonify, make_response, redirect, render_template, request, url_for
from flask_cors import CORS, cross_origin
import jwt
from models import Order, OrderStatus, Payment, ItemsInOrder, db
from config import Config
import requests

app = Flask(__name__)
app.config.from_object(Config)
app.config['JSON_AS_ASCII'] = False
db.init_app(app)

CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": "*",
    "expose_headers": "*",
    "supports_credentials": True
}})

@app.route('/orders')
def get_orders():
    current_user = get_current_user_from_token()

    # если токен устарел - очищаем cookie
    if not current_user and request.cookies.get('auth_token'):
        response = make_response(redirect('http://localhost:5000'))
        response.delete_cookie('auth_token')
        return response
    if not current_user:
        return render_template('401.html')
    
    orders = Order.query.filter_by(user_id=current_user["id"]).join(Payment).join(OrderStatus).all()

    return render_template('orders.html', current_user=current_user, orders=orders)

@app.route('/order/<int:id>')
def order_details(id):
    order = Order.query.get(id)
    user = get_current_user_from_token()
    if not user and request.cookies.get('auth_token'):
        response = make_response(redirect('http://localhost:5000'))
        response.delete_cookie('auth_token')
        return response
    if not user or order.user_id!=user["id"]:
        return render_template('401.html')
    
    if not order:
        return render_template('404.html'), 404
    items_in_order = ItemsInOrder.query.filter_by(order_id=id).all()
    # Запрашиваем данные о книгах из book_catalog_service
    book_ids = [item.book_id for item in items_in_order]
    books = get_books(book_ids)
    books_dict = {book["id"]: book for book in books}
    total = 0
    
    for item in items_in_order:
        if item.book_id in books_dict:
            book = books_dict[item.book_id]
            total += book["price"] * item.quantity
    return render_template('order_details.html', order=order, items_in_order=items_in_order, books=books, total=total)

def get_books(book_ids):
    if not book_ids:
        return []

    try:
        # Делаем запрос к сервису каталога
        response = requests.get(
            'http://localhost:5000/books',
            params={'ids': ','.join(map(str, book_ids))},
            timeout=3
        )
        if response.status_code == 200:
            # Преобразуем JSON-ответ в список объектов Book
            books_data = response.json()
            return books_data  # Возвращаем данные о книгах
        
        app.logger.error(f"User service returned {response.status_code}")
        return []
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Failed to fetch books: {str(e)}")
        return []

def get_current_user_from_token():
    token = request.cookies.get('auth_token')
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        user_id = payload.get('user_id')
        
        response = requests.get(
            f'http://localhost:5001/users/{user_id}',
            headers={'Authorization': f'Bearer {token}'},
            timeout=3
        )
        
        if response.status_code == 200:
            return response.json()
        return None
        
    except jwt.PyJWTError:
        return None
    except requests.exceptions.RequestException:
        return None

# отмена заказа
@app.route('/order/cancel/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    order = Order.query.get(order_id)
    
    if order:
        order.status_id = 3
        db.session.commit()
        flash('Заказ успешно отменен.', 'success')
    else:
        flash('Заказ не найден.', 'error')
    
    return redirect(url_for('get_orders'))

# оформление заказа
@app.route('/checkout', methods=['POST'])
@cross_origin(supports_credentials=True)
def checkout():
    try:
        # Проверка авторизации
        token = request.cookies.get('auth_token')
        if not token:
            return jsonify({'error': 'Требуется авторизация'}), 401
        
        current_user = get_current_user_from_token()
        if not current_user:
            return jsonify({'error': 'Недействительный токен'}), 401

        # Проверка данных
        if not request.is_json:
            return jsonify({'error': 'Запрос должен быть в формате JSON'}), 400
            
        data = request.get_json()
        
        # Получение корзины
        cart_response = requests.get(
            "http://localhost:5001/api/cart",
            cookies={'auth_token': token},
            headers={'Content-Type': 'application/json'}
        )
        
        if cart_response.status_code != 200:
            return jsonify({'error': 'Ошибка при получении корзины', 'details': cart_response.text}), 500
            
        cart_items = cart_response.json()
        if not cart_items:
            return jsonify({'error': 'Корзина пуста'}), 400
        # Создание заказа
        new_order = Order(
            user_id=int(current_user["id"]),
            payment_id=int(data['payment_method']),
            address=data['shipping_address'],
            status_id=1
        )
        
        db.session.add(new_order)
        db.session.flush()
        
        # Добавление товаров в заказ
        for item in cart_items:
            order_item = ItemsInOrder(
                order_id=new_order.id,
                user_id=current_user["id"],
                book_id=item['book_id'],
                quantity=item['quantity']
            )
            db.session.add(order_item)
        # Очистка корзины
        clear_response = requests.delete(
            "http://localhost:5001/api/cart/clear",
            cookies={'auth_token': token}
        )
        
        if clear_response.status_code != 200:
            db.session.rollback()
            return jsonify({'error': 'Ошибка при очистке корзины'}), 500
            
        db.session.commit()
        
        return redirect(url_for('get_orders'))
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Внутренняя ошибка сервера', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5002)