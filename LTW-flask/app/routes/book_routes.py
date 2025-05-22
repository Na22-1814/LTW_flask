from flask import Blueprint, render_template, url_for, flash, redirect, request, abort
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional
from app import db
from app.models import Book, Category, Review
from sqlalchemy import desc, func, or_, text
from datetime import datetime


book_bp = Blueprint('book', __name__)

@book_bp.route('/')
def index():
    """Redirect to new books page."""
    return redirect(url_for('book.new_books'))

@book_bp.route('/new')
def new_books():
    """Display new books."""
    # Get the latest 9 books, ordered by added date
    books = Book.query.filter_by(Status=True).order_by(desc(Book.AddedDate)).limit(9).all()
    return render_template('books/new.html', title='Sách mới', books=books)

@book_bp.route('/category')
def categories():
    """Display all categories."""
    # Get all root categories (those without a parent)
    root_categories = Category.query.filter_by(ParentCategoryID=None, Status=True).all()
    return render_template('books/categories.html', title='Thể loại', categories=root_categories)

@book_bp.route('/category/<int:category_id>')
def category_books(category_id):
    """Display books in a specific category."""
    category = Category.query.get_or_404(category_id)
    
    # Get books directly in this category
    direct_books = Book.query.filter_by(CategoryID=category_id, Status=True).all()
    
    # Get books from subcategories
    subcategories = Category.query.filter_by(ParentCategoryID=category_id, Status=True).all()
    subcategory_books = []
    for subcat in subcategories:
        subcategory_books.extend(Book.query.filter_by(CategoryID=subcat.CategoryID, Status=True).all())
    
    # Combine the books
    books = direct_books + subcategory_books
    
    return render_template('books/category_books.html', 
                           title=f'Thể loại: {category.CategoryName}', 
                           category=category, 
                           books=books)

@book_bp.route('/book/<int:book_id>')
def book_detail(book_id):
    """Display book details."""
    book = Book.query.get_or_404(book_id)
    
    # If book is not active and user is not admin, return 404
    if not book.Status and (not current_user.is_authenticated or not current_user.is_admin()):
        abort(404)
    
    # Get related books (books in the same category)
    related_books = Book.query.filter(
        Book.CategoryID == book.CategoryID, 
        Book.BookID != book.BookID,
        Book.Status == True
    ).limit(3).all()
    
    # Get book reviews
    reviews = Review.query.filter_by(BookID=book_id, Status=True).order_by(desc(Review.ReviewDate)).all()
    
    return render_template('books/book_detail.html', 
                           title=book.Title, 
                           book=book, 
                           related_books=related_books,
                           reviews=reviews)

@book_bp.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('book.new_books'))

    # Tạo mẫu tìm kiếm
    search_term = f'%{query}%'

    # Search in title, author, and description
    books = Book.query.filter(
        Book.Status == True
    ).filter(
        or_(
            text("Title COLLATE Latin1_General_CI_AI LIKE :search"),
            text("Author COLLATE Latin1_General_CI_AI LIKE :search"),
            text("Description COLLATE Latin1_General_CI_AI LIKE :search")
        )
    ).params(search=search_term).all()

    return render_template('books/search_results.html',
                           title='Kết quả tìm kiếm',
                           query=query,
                           books=books)

# Review form
class ReviewForm(FlaskForm):
    rating = SelectField('Đánh giá', choices=[(str(i), str(i)) for i in range(1, 6)], validators=[DataRequired()])
    comment = TextAreaField('Nhận xét', validators=[DataRequired()])
    submit = SubmitField('Gửi đánh giá')

@book_bp.route('/book/<int:book_id>/review', methods=['GET', 'POST'])
@login_required
def add_review(book_id):
    """Add a review for a book."""
    book = Book.query.get_or_404(book_id)
    
    # Check if user has already reviewed this book
    existing_review = Review.query.filter_by(
        BookID=book_id, 
        UserID=current_user.UserID
    ).first()
    
    if existing_review:
        flash('Bạn đã đánh giá sách này rồi.', 'warning')
        return redirect(url_for('book.book_detail', book_id=book_id))
    
    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            BookID=book_id,
            UserID=current_user.UserID,
            Rating=int(form.rating.data),
            Comment=form.comment.data,
            ReviewDate=datetime.utcnow(),
            Status=True
        )
        
        db.session.add(review)
        db.session.commit()
        
        flash('Đánh giá của bạn đã được gửi!', 'success')
        return redirect(url_for('book.book_detail', book_id=book_id))
    
    return render_template('books/add_review.html', 
                           title=f'Đánh giá: {book.Title}', 
                           book=book, 
                           form=form)