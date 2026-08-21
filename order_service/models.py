from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class OrderStatus(db.Model):
    __tablename__ = 'order_status'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    
    orders = db.relationship('Order', backref='status', lazy=True)
    
    def __repr__(self):
        return f'<OrderStatus {self.id}: {self.name}>'

class Payment(db.Model):
    __tablename__ = 'payment'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    
    orders = db.relationship('Order', backref='payment', lazy=True)
    
    def __repr__(self):
        return f'<Payment {self.id}: {self.name}>'

class Order(db.Model):
    __tablename__ = 'order'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    checkout_date = db.Column(db.DateTime(timezone=True), default=datetime.now())
    delivery_date = db.Column(db.DateTime, default=lambda: datetime.now() + timedelta(days=7))
    payment_id = db.Column(db.Integer, db.ForeignKey('payment.id'), nullable=False)
    address = db.Column(db.Text, default='г. Томск, ул. Зеленая, 15')
    status_id = db.Column(db.Integer, db.ForeignKey('order_status.id'), default=1)
    
    items = db.relationship('ItemsInOrder', backref='order', lazy=True)
    
    def __repr__(self):
        return f'<Order {self.id} by user {self.user_id}>'

class ItemsInOrder(db.Model):
    __tablename__ = 'items_in_order'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    book_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    def __repr__(self):
        return f'<ItemsInOrder {self.id} (order {self.order_id}, qty {self.quantity})>'