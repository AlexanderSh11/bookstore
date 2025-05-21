from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Genre(db.Model):
    __tablename__ = 'genre'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    books = db.relationship('Book', back_populates='genre')
    
    def __repr__(self):
        return f'<Genre {self.name}>'

class Book(db.Model):
    __tablename__ = 'book'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    genre_id = db.Column(db.Integer, db.ForeignKey('genre.id'))
    year = db.Column(db.Integer)
    publisher = db.Column(db.String(100))
    price = db.Column(db.Float, nullable=False)
    
    genre = db.relationship('Genre', back_populates='books')

    def __repr__(self):
        return f'<Book {self.title}>'

class ProductCatalog:
    @staticmethod
    def get_all_books(sort_by=None):
        query = Book.query.join(Genre)
        
        if sort_by:
            # Проверяем допустимость поля для сортировки
            valid_sort_fields = {'title', 'author', 'price'}
            if sort_by not in valid_sort_fields:
                raise ValueError(f"Invalid sort field. Allowed: {valid_sort_fields}")
                
            sort_column = getattr(Book, sort_by)     
            query = query.order_by(sort_column)
            
        return query.all()
    
    @staticmethod
    def search_books(query, sort_by):
        if not query:
            return []
            
        search_query = Book.query.join(Genre).filter(
            (Book.title.ilike(f'%{query}%')) | 
            (Book.author.ilike(f'%{query}%'))
        )
        
        if sort_by:
            valid_sort_fields = {'title', 'author', 'price'}
            if sort_by in valid_sort_fields:
                sort_column = getattr(Book, sort_by)
                search_query = search_query.order_by(sort_column)
                
        return search_query.all()

    @staticmethod
    def get_book_by_id(book_id):
        return Book.query.get(book_id)