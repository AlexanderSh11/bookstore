from datetime import datetime, timedelta, timezone
from flask import jsonify, make_response, render_template, request, redirect, url_for, flash
import jwt
import requests
from models import Cart, db, User

def init_app(app):
    def generate_jwt_token(user_id):
        """Функция генерации токена с ID пользователя"""
        payload = {
            'user_id': user_id,
            'exp': datetime.now(timezone.utc) + timedelta(hours=24)
        }
        return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

    def verify_jwt_token(token):
        """Функция проверки токена"""
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            return payload['user_id']
        except jwt.PyJWTError:
            return None

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Регистрация нового пользователя и отображение страницы регистрации"""
        if request.method == 'POST':
            full_name = request.form['full_name']
            email = request.form['email']
            phone = request.form['phone']
            password = request.form['password']

            if User.query.filter_by(email=email).first():
                flash('Email уже зарегистрирован', 'error')
                return redirect(url_for('register'))
            
            if User.query.filter_by(phone=phone).first():
                flash('Телефон уже зарегистрирован', 'error')
                return redirect(url_for('register'))

            new_user = User(
                full_name=full_name,
                email=email,
                phone=phone
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()

            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Авторизация пользователя и отображение страницы авторизации"""
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            
            user = User.query.filter_by(email=email).first()
            
            if not user or not user.check_password(password):
                flash('Неверный email или пароль', 'error')
                return redirect(url_for('login'))
            
            token = generate_jwt_token(user.id)
            
            # ответ с установкой cookie
            response = make_response(redirect('http://localhost:5000'))
            response.set_cookie(
                'auth_token',
                token,
                httponly=True,
                secure=False,
                samesite='Lax',
                max_age=86400  # 24 часа
            )
            return response
        
        return render_template('login.html')

    @app.route('/profile')
    def profile():
        """Страница профиля пользователя"""
        token = request.cookies.get('auth_token')
        if not token:
            flash('Пожалуйста, войдите', 'error')
            return redirect(url_for('login'))
        
        user_id = verify_jwt_token(token)
        if not user_id:
            flash('Недействительная сессия', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(user_id)
        return render_template('profile.html', current_user=user)

    @app.route('/logout', methods=['POST'])
    def logout():
        """Функция выхода из аккаунта с удалением access токена, переход на страницу каталога"""
        response = make_response(redirect('http://localhost:5000'))
        response.delete_cookie('auth_token')
        flash('Вы успешно вышли', 'success')
        return response

    @app.route('/users/<int:id>')
    def get_user_by_id(id):
        """Функция получения пользователя по ID"""
        user = User.query.get(id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'id': user.id,
            'username': user.full_name,
            'email': user.email,
            'phone': user.phone
        })

    @app.route('/cart')
    def cart():
        """Отображение корзины авторизованного пользователя"""
        token = request.cookies.get('auth_token')
        if not token:
            flash('Пожалуйста, войдите', 'error')
            return redirect(url_for('login'))
        
        user_id = verify_jwt_token(token)
        if not user_id:
            flash('Недействительная сессия', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(user_id)

        carts, books = get_cart(user)
        
        books_dict = {book["id"]: book for book in books}
        total = 0
        valid_carts = []
        
        for item in carts:
            if item.book_id in books_dict:
                book = books_dict[item.book_id]
                total += book["price"] * item.quantity
                valid_carts.append({
                    'cart_item': item,
                    'book': book
                })

        return render_template('cart.html', current_user=user, books=books, carts=carts, total=total)
    
    @app.route('/api/cart')
    def api_cart():
        """Функция получения книг из корзины пользователя"""
        token = request.cookies.get('auth_token')
        if not token:
            flash('Пожалуйста, войдите', 'error')
            return redirect(url_for('login'))
        
        user_id = verify_jwt_token(token)
        if not user_id:
            flash('Недействительная сессия', 'error')
            return redirect(url_for('login'))
        
        user = User.query.get(user_id)

        cart_items = Cart.query.filter_by(user_id=user_id).all()
        
        # Запрашиваем данные о книгах из book_catalog_service
        book_ids = [item.book_id for item in cart_items]
        books = get_books(book_ids)
        
        response = [{
            'id': item.id,
            'book_id': item.book_id,
            'quantity': item.quantity,
            'book_info': next((b for b in books if b['id'] == item.book_id), None)
        } for item in cart_items]
        return response

    def get_cart(user):
        """Функция получения книг из корзины по пользователю"""
        user_id = user.id
        cart_items = Cart.query.filter_by(user_id=user_id).all()
        
        # Запрашиваем данные о книгах из book_catalog_service
        book_ids = [item.book_id for item in cart_items]
        books = get_books(book_ids)
        
        return cart_items, books

    def get_books(book_ids):
        """Функция получения книг по их ID (запрос к сервису каталога)"""
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

    @app.route('/cart/add', methods=['POST'])
    def add_to_cart():
        """Функция добавления книги в корзину"""
        data = request.get_json()
            
        book_id = int(data['book_id'])
        user_id = int(data['user_id'])

        if Cart.query.filter_by(book_id=book_id, user_id=user_id).first():
            flash('Товар уже добавлен', 'error')
            return redirect(url_for('cart'))

        new_cart_item = Cart(
            book_id=book_id,
            user_id=user_id,
            quantity=1
        )
            
        db.session.add(new_cart_item)
        db.session.commit()

        flash('Товар успешно добавлен.', 'success')
        return redirect(url_for('cart'))

    @app.route('/cart/remove/<int:user_id>/<int:book_id>', methods=['POST'])
    def remove_from_cart(user_id, book_id):
        """Функция удаления книги из корзины"""
        cart_item = Cart.query.filter_by(book_id=book_id, user_id=user_id).first()
        
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
            flash('Товар успешно удален из корзины.', 'success')
        else:
            flash('Товар не найден в корзине.', 'error')
        
        return redirect(url_for('cart'))
    
    @app.route('/cart/edit/<int:cart_item_id>/<action>', methods=['POST'])
    def edit_cart_item(cart_item_id, action):
        """Функция изменения количества книг в корзине"""
        cart_item = Cart.query.get_or_404(cart_item_id)
        
        if action == 'inc':
            cart_item.quantity += 1
        elif action == 'dec':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                # Если количество = 1 и нажали "-", можно удалить товар
                db.session.delete(cart_item)
                db.session.commit()
                flash('Товар удален из корзины', 'info')
                return redirect(url_for('cart'))
        
        db.session.commit()
        return redirect(url_for('cart'))

    @app.route('/api/cart/clear', methods=['DELETE'])
    def clear_cart():
        """Функция отчистки корзины с перенаправлением к заказам пользователя"""
        token = request.cookies.get('auth_token')
        if not token:
            flash('Пожалуйста, войдите', 'error')
            return redirect(url_for('login'))
        
        user_id = verify_jwt_token(token)
        if not user_id:
            flash('Недействительная сессия', 'error')
            return redirect(url_for('login'))
        Cart.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        return redirect("http://localhost:5002/orders")