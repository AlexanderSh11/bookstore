from flask import Flask, jsonify, make_response, render_template, request
import jwt
from models import Book, ProductCatalog, db
from config import Config
import requests

app = Flask(__name__)
app.config.from_object(Config)
app.config['JSON_AS_ASCII'] = False
db.init_app(app)

@app.route('/')
def catalog():
    current_user = get_current_user_from_token()

    sort_by = request.args.get('sort_by')
    
    books = ProductCatalog.get_all_books(sort_by=sort_by)

    # если токен устарел - очищаем cookie
    if not current_user and request.cookies.get('auth_token'):
        response = make_response(render_template(
            'catalog.html', 
            books=books, 
            sort_by=sort_by,
            current_user=None
        ))
        response.delete_cookie('auth_token')
        return response
    
    return render_template('catalog.html', books=books, sort_by=sort_by, current_user=current_user)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    sort_by = request.args.get('sort_by')
    current_user = get_current_user_from_token()
    if query:
        # поиск по названию и автору с сортировкой
        books = ProductCatalog.search_books(query, sort_by)
    else:
        books = []
    return render_template('catalog.html', books=books, search_query=query, sort_by=sort_by, current_user=current_user)

@app.route('/book/<int:id>')
def book_details(id):
    book = ProductCatalog.get_book_by_id(id)
    if not book:
        return render_template('404.html'), 404
    return render_template('book_details.html', book=book)

@app.route('/books', methods=['GET'])
def get_books():
    # Получаем строку с ID книг
    ids_str = request.args.get('ids', '')
    if not ids_str:
        return jsonify({'error': 'Missing ids parameter'}), 400

    try:
        # Преобразуем строку в список чисел
        book_ids = [int(id) for id in ids_str.split(',')]
    except ValueError:
        return jsonify({'error': 'Invalid ids format'}), 400

    # Получаем книги из базы данных
    books = Book.query.filter(Book.id.in_(book_ids)).all()
    # Преобразуем объекты Book в словари для JSON-сериализации
    books_data = [{
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'price': book.price,
        'year': book.year,
        'description': book.description,
        'publisher': book.publisher,
    } for book in books]

    return jsonify(books_data)

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)