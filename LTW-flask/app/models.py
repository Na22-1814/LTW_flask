from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager
from slugify import slugify
from decimal import Decimal


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Role(db.Model):
    __tablename__ = 'Roles'

    RoleID = db.Column(db.Integer, primary_key=True)
    RoleName = db.Column(db.String(50), nullable=False)
    Description = db.Column(db.String(200))

    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f'<Role {self.RoleName}>'


class User(db.Model, UserMixin):
    __tablename__ = 'Users'

    UserID = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(50), unique=True, nullable=False)
    Password = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(100), unique=True, nullable=False)
    FullName = db.Column(db.String(100))
    PhoneNumber = db.Column(db.String(20))
    Address = db.Column(db.String(200))
    RoleID = db.Column(db.Integer, db.ForeignKey('Roles.RoleID'), nullable=False)
    RegisterDate = db.Column(db.DateTime, default=datetime.utcnow)
    LastLogin = db.Column(db.DateTime)
    Status = db.Column(db.Boolean, default=True)

    orders = db.relationship('Order', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)

    def get_id(self):
        return str(self.UserID)

    def is_admin(self):
        return self.role.RoleName == 'Admin'

    def __repr__(self):
        return f'<User {self.Username}>'


class Category(db.Model):
    __tablename__ = 'Categories'

    CategoryID = db.Column(db.Integer, primary_key=True)
    CategoryName = db.Column(db.String(100), nullable=False)
    Description = db.Column(db.String(500))
    ParentCategoryID = db.Column(db.Integer, db.ForeignKey('Categories.CategoryID'))
    Status = db.Column(db.Boolean, default=True)

    books = db.relationship('Book', backref='category', lazy=True)
    subcategories = db.relationship('Category',
                                    backref=db.backref('parent', remote_side=[CategoryID]),
                                    lazy=True)

    def __repr__(self):
        return f'<Category {self.CategoryName}>'


class Book(db.Model):
    __tablename__ = 'Books'

    BookID = db.Column(db.Integer, primary_key=True)
    Title = db.Column(db.String(200), nullable=False)
    Author = db.Column(db.String(200))
    Publisher = db.Column(db.String(200))
    PublishYear = db.Column(db.Integer)
    CategoryID = db.Column(db.Integer, db.ForeignKey('Categories.CategoryID'))
    Description = db.Column(db.Text)
    # Sử dụng Float thay vì Numeric để tránh lỗi precision với SQL Server
    Price = db.Column(db.Float, nullable=False)
    CoverImage = db.Column(db.String(255))  # Cloudinary URL
    FilePath = db.Column(db.String(255), nullable=False)  # Cloudinary URL
    PageCount = db.Column(db.Integer)
    AddedDate = db.Column(db.DateTime, default=datetime.utcnow)
    UpdatedDate = db.Column(db.DateTime)
    Status = db.Column(db.Boolean, default=True)


    order_details = db.relationship('OrderDetail', backref='book', lazy=True)
    reviews = db.relationship('Review', backref='book', lazy=True)

    @property
    def slug(self):
        return slugify(self.Title)

    def __repr__(self):
        return f'<Book {self.Title}>'


class Order(db.Model):
    __tablename__ = 'Orders'

    OrderID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    OrderDate = db.Column(db.DateTime, default=datetime.utcnow)
    # Sử dụng Float thay vì Numeric
    TotalAmount = db.Column(db.Float, nullable=False)
    PaymentMethod = db.Column(db.String(50))
    PaymentStatus = db.Column(db.Boolean, default=False)
    OrderStatus = db.Column(db.String(50), default='Chờ xác nhận')

    order_details = db.relationship('OrderDetail', backref='order', lazy=True)
    payment_transactions = db.relationship('PaymentTransaction', backref='order', lazy=True)

    def __repr__(self):
        return f'<Order {self.OrderID}>'


class OrderDetail(db.Model):
    __tablename__ = 'OrderDetails'

    OrderDetailID = db.Column(db.Integer, primary_key=True)
    OrderID = db.Column(db.Integer, db.ForeignKey('Orders.OrderID'), nullable=False)
    BookID = db.Column(db.Integer, db.ForeignKey('Books.BookID'), nullable=False)
    # Sử dụng Float thay vì Numeric
    Price = db.Column(db.Float, nullable=False)
    DownloadStatus = db.Column(db.Boolean, default=False)
    DownloadDate = db.Column(db.DateTime)

    def __repr__(self):
        return f'<OrderDetail {self.OrderDetailID}>'


class Review(db.Model):
    __tablename__ = 'Reviews'

    ReviewID = db.Column(db.Integer, primary_key=True)
    BookID = db.Column(db.Integer, db.ForeignKey('Books.BookID'), nullable=False)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    Rating = db.Column(db.Integer, nullable=False)
    Comment = db.Column(db.String(1000))
    ReviewDate = db.Column(db.DateTime, default=datetime.utcnow)
    Status = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Review {self.ReviewID}>'


class PaymentTransaction(db.Model):
    __tablename__ = 'PaymentTransactions'

    TransactionID = db.Column(db.Integer, primary_key=True)
    OrderID = db.Column(db.Integer, db.ForeignKey('Orders.OrderID'), nullable=False)
    # Sử dụng Float thay vì Numeric
    Amount = db.Column(db.Float, nullable=False)
    PaymentMethod = db.Column(db.String(50), nullable=False)
    TransactionDate = db.Column(db.DateTime, default=datetime.utcnow)
    TransactionCode = db.Column(db.String(100))
    Status = db.Column(db.String(50))

    def __repr__(self):
        return f'<PaymentTransaction {self.TransactionID}>'