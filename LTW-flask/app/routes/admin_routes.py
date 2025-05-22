from flask import Blueprint, render_template, url_for, flash, redirect, request, abort, current_app
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from sqlalchemy.sql.sqltypes import Integer
from wtforms import StringField, TextAreaField, DecimalField, IntegerField, SelectField, SubmitField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from app import db
from app.models import Book, Category, User, Order, OrderDetail, Review, Role, PaymentTransaction
from app.utils.auth_utils import admin_required
from app.utils.cloudinary_utils import upload_image, upload_file, delete_asset
from sqlalchemy import desc, func, cast
from datetime import datetime, timezone
from decimal import Decimal
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# Book form
class BookForm(FlaskForm):
    title = StringField('Tiêu đề', validators=[DataRequired(), Length(max=200)])
    author = StringField('Tác giả', validators=[Length(max=200)])
    publisher = StringField('Nhà xuất bản', validators=[Length(max=200)])
    publish_year = IntegerField('Năm xuất bản', validators=[Optional()])
    category = SelectField('Thể loại', coerce=int, validators=[DataRequired()])
    description = TextAreaField('Mô tả')
    price = DecimalField('Giá', validators=[DataRequired(), NumberRange(min=0)], places=2)
    page_count = IntegerField('Số trang', validators=[Optional()])
    cover_image = FileField('Ảnh bìa', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], 'Chỉ chấp nhận file ảnh!')
    ])
    book_file = FileField('File sách (PDF)', validators=[
        FileAllowed(['pdf'], 'Chỉ chấp nhận file PDF!')
    ])
    status = BooleanField('Hiển thị', default=True)
    submit = SubmitField('Lưu')


# Category form
class CategoryForm(FlaskForm):
    name = StringField('Tên thể loại', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Mô tả', validators=[Length(max=500)])
    parent_category = SelectField('Thể loại cha', coerce=int, validators=[Optional()])
    status = BooleanField('Hiển thị', default=True)
    submit = SubmitField('Lưu')


# User form
class UserForm(FlaskForm):
    username = StringField('Tên tài khoản', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Length(max=100)])
    full_name = StringField('Họ và tên', validators=[Length(max=100)])
    phone_number = StringField('Số điện thoại', validators=[Length(max=20)])
    address = TextAreaField('Địa chỉ', validators=[Length(max=200)])
    role = SelectField('Vai trò', coerce=int, validators=[DataRequired()])
    status = BooleanField('Kích hoạt', default=True)
    submit = SubmitField('Lưu')


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Admin dashboard."""
    # Count statistics
    book_count = Book.query.count()
    user_count = User.query.count()
    order_count = Order.query.count()
    download_count = db.session.query(func.count(OrderDetail.OrderDetailID)) \
                         .filter(OrderDetail.DownloadStatus == True).scalar() or 0

    # Top categories
    top_categories = db.session.query(
        Category.CategoryName,
        func.count(Book.BookID).label('book_count')
    ).join(Book, Category.CategoryID == Book.CategoryID) \
        .group_by(Category.CategoryName) \
        .order_by(func.count(Book.BookID).desc()) \
        .limit(5).all()

    # Recent orders
    recent_orders = Order.query.order_by(desc(Order.OrderDate)).limit(5).all()

    # Monthly downloads chart data
    current_time = datetime.now(timezone.utc)
    current_year = current_time.year

    # Sử dụng EXTRACT thay vì func.month để tương thích với SQL Server
    monthly_downloads = db.session.query(
        func.extract('month', OrderDetail.DownloadDate).label('month'),
        func.count(OrderDetail.OrderDetailID).label('count')
    ).filter(
        func.extract('year', OrderDetail.DownloadDate) == current_year,
        OrderDetail.DownloadStatus == True
    ).group_by(func.extract('month', OrderDetail.DownloadDate)).all()

    # Format chart data
    months = [0] * 12
    for month, count in monthly_downloads:
        if month and 1 <= int(month) <= 12:
            months[int(month) - 1] = count

    # Tạo biến now với timezone-aware
    now = datetime.now(timezone.utc)
    max_monthly_downloads = max(months) if months else 0
    return render_template('admin/dashboard.html',
                           title='Dashboard',
                           book_count=book_count,
                           user_count=user_count,
                           order_count=order_count,
                           download_count=download_count,
                           top_categories=top_categories,
                           recent_orders=recent_orders,
                           monthly_downloads=months,
                           max_monthly_downloads=max_monthly_downloads,
                           now=now)


# Book management
@admin_bp.route('/books')
@login_required
@admin_required
def books():
    """List all books."""
    books = Book.query.order_by(desc(Book.AddedDate)).all()
    return render_template('admin/books.html', title='Quản lý sách', books=books)


@admin_bp.route('/books/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_book():
    """Add a new book."""
    form = BookForm()

    # Populate category choices
    form.category.choices = [(cat.CategoryID, cat.CategoryName) for cat in Category.query.all()]

    if form.validate_on_submit():
        try:
            # Upload cover image to Cloudinary if provided
            cover_image_url = None
            if form.cover_image.data:
                result = upload_image(form.cover_image.data)
                if result:
                    cover_image_url = result['secure_url']

            # Upload book file to Cloudinary (required)
            if not form.book_file.data:
                flash('File sách là bắt buộc!', 'danger')
                return render_template('admin/book_form.html', title='Thêm sách mới', form=form, book=None)

            result = upload_file(form.book_file.data)
            if not result:
                flash('Không thể tải file sách lên. Vui lòng thử lại.', 'danger')
                return render_template('admin/book_form.html', title='Thêm sách mới', form=form, book=None)

            file_url = result['secure_url']

            # Convert Decimal to float for SQL Server compatibility
            price_value = float(form.price.data) if form.price.data else 0.0

            # Create new book
            book = Book(
                Title=form.title.data,
                Author=form.author.data,
                Publisher=form.publisher.data,
                PublishYear=form.publish_year.data,
                CategoryID=form.category.data,
                Description=form.description.data,
                Price=price_value,
                CoverImage=cover_image_url,
                FilePath=file_url,
                PageCount=form.page_count.data,
                AddedDate=datetime.now(timezone.utc),
                Status=form.status.data
            )

            db.session.add(book)
            db.session.commit()

            flash('Sách mới đã được thêm vào!', 'success')
            return redirect(url_for('admin.books'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding book: {str(e)}")
            flash('Có lỗi xảy ra khi thêm sách. Vui lòng thử lại.', 'danger')

    return render_template('admin/book_form.html', title='Thêm sách mới', form=form, book=None)


@admin_bp.route('/books/bulk-update', methods=['POST'])
@login_required
@admin_required
def bulk_update_books():
    """Update status of multiple books at once."""
    try:
        book_ids = request.form.get('book_ids', '').split(',')
        status = request.form.get('status') == '1'

        # Loại bỏ chuỗi rỗng
        book_ids = [book_id for book_id in book_ids if book_id.strip()]

        if not book_ids:
            flash('Không có sách nào được chọn để cập nhật!', 'warning')
            return redirect(url_for('admin.books'))

        # Cập nhật trạng thái các sách
        Book.query.filter(Book.BookID.in_(book_ids)).update({Book.Status: status}, synchronize_session=False)
        db.session.commit()

        status_text = 'kích hoạt' if status else 'ẩn'
        flash(f'Đã {status_text} {len(book_ids)} sách!', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error bulk updating books: {str(e)}")
        flash('Có lỗi xảy ra khi cập nhật sách.', 'danger')

    return redirect(url_for('admin.books'))


@admin_bp.route('/books/bulk-delete', methods=['POST'])
@login_required
@admin_required
def bulk_delete_books():
    """Delete multiple books at once."""
    try:
        book_ids = request.form.get('book_ids', '').split(',')

        # Loại bỏ chuỗi rỗng
        book_ids = [book_id for book_id in book_ids if book_id.strip()]

        if not book_ids:
            flash('Không có sách nào được chọn để xóa!', 'warning')
            return redirect(url_for('admin.books'))

        # Kiểm tra xem sách có liên kết đến đơn hàng không
        ordered_books = OrderDetail.query.filter(OrderDetail.BookID.in_(book_ids)).first()
        if ordered_books:
            flash('Không thể xóa một số sách vì đã có người mua!', 'danger')
            return redirect(url_for('admin.books'))

        # Xóa các sách đã chọn
        books = Book.query.filter(Book.BookID.in_(book_ids)).all()
        for book in books:
            db.session.delete(book)

        db.session.commit()
        flash(f'Đã xóa {len(books)} sách!', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error bulk deleting books: {str(e)}")
        flash('Có lỗi xảy ra khi xóa sách.', 'danger')

    return redirect(url_for('admin.books'))


@admin_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_book(book_id):
    """Edit a book."""
    book = Book.query.get_or_404(book_id)
    form = BookForm()

    # Populate category choices
    form.category.choices = [(cat.CategoryID, cat.CategoryName) for cat in Category.query.all()]

    if form.validate_on_submit():
        try:
            # Convert Decimal to float for SQL Server compatibility
            price_value = float(form.price.data) if form.price.data else 0.0

            # Update book details
            book.Title = form.title.data
            book.Author = form.author.data
            book.Publisher = form.publisher.data
            book.PublishYear = form.publish_year.data
            book.CategoryID = form.category.data
            book.Description = form.description.data
            book.Price = price_value
            book.PageCount = form.page_count.data
            book.Status = form.status.data
            book.UpdatedDate = datetime.now(timezone.utc)

            # Upload new cover image if provided
            if form.cover_image.data:
                result = upload_image(form.cover_image.data)
                if result:
                    book.CoverImage = result['secure_url']

            # Upload new book file if provided
            if form.book_file.data:
                result = upload_file(form.book_file.data)
                if result:
                    book.FilePath = result['secure_url']

            db.session.commit()

            flash('Thông tin sách đã được cập nhật!', 'success')
            return redirect(url_for('admin.books'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating book: {str(e)}")
            flash('Có lỗi xảy ra khi cập nhật sách.', 'danger')

    # Pre-populate form with current book data
    if request.method == 'GET':
        form.title.data = book.Title
        form.author.data = book.Author
        form.publisher.data = book.Publisher
        form.publish_year.data = book.PublishYear
        form.category.data = book.CategoryID
        form.description.data = book.Description
        form.price.data = Decimal(str(book.Price))
        form.page_count.data = book.PageCount
        form.status.data = book.Status

    return render_template('admin/book_form.html', title='Sửa thông tin sách', form=form, book=book)


@admin_bp.route('/books/delete/<int:book_id>', methods=['POST'])
@login_required
@admin_required
def delete_book(book_id):
    """Delete a book."""
    try:
        book = Book.query.get_or_404(book_id)

        # Check if book is linked to any orders
        order_details = OrderDetail.query.filter_by(BookID=book_id).first()
        if order_details:
            flash('Không thể xóa sách này vì đã có người mua!', 'danger')
            return redirect(url_for('admin.books'))

        # Delete book
        db.session.delete(book)
        db.session.commit()

        flash('Sách đã được xóa!', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting book: {str(e)}")
        flash('Có lỗi xảy ra khi xóa sách.', 'danger')

    return redirect(url_for('admin.books'))


# Category management
@admin_bp.route('/categories')
@login_required
@admin_required
def categories():
    """List all categories."""
    categories = Category.query.all()
    return render_template('admin/categories.html', title='Quản lý thể loại', categories=categories)


@admin_bp.route('/categories/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_category():
    """Add a new category."""
    form = CategoryForm()

    # Populate parent category choices
    form.parent_category.choices = [(0, 'Không có')] + [(cat.CategoryID, cat.CategoryName) for cat in
                                                        Category.query.all()]

    if form.validate_on_submit():
        try:
            # Create new category
            category = Category(
                CategoryName=form.name.data,
                Description=form.description.data,
                ParentCategoryID=form.parent_category.data if form.parent_category.data != 0 else None,
                Status=form.status.data
            )

            db.session.add(category)
            db.session.commit()

            flash('Thể loại mới đã được thêm vào!', 'success')
            return redirect(url_for('admin.categories'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error adding category: {str(e)}")
            flash('Có lỗi xảy ra khi thêm thể loại.', 'danger')

    return render_template('admin/category_form.html', title='Thêm thể loại mới', form=form, category=None)


@admin_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_category(category_id):
    """Edit a category."""
    category = Category.query.get_or_404(category_id)
    form = CategoryForm()

    # Populate parent category choices (excluding self and children)
    excluded_ids = [category_id]

    # Get all children and descendants
    def get_children_ids(parent_id):
        children = Category.query.filter_by(ParentCategoryID=parent_id).all()
        result = []
        for child in children:
            result.append(child.CategoryID)
            result.extend(get_children_ids(child.CategoryID))
        return result

    excluded_ids.extend(get_children_ids(category_id))

    # Filter categories that can be parents
    available_categories = Category.query.filter(~Category.CategoryID.in_(excluded_ids)).all()
    form.parent_category.choices = [(0, 'Không có')] + [(cat.CategoryID, cat.CategoryName) for cat in
                                                        available_categories]

    if form.validate_on_submit():
        try:
            # Update category details
            category.CategoryName = form.name.data
            category.Description = form.description.data
            category.ParentCategoryID = form.parent_category.data if form.parent_category.data != 0 else None
            category.Status = form.status.data

            db.session.commit()

            flash('Thông tin thể loại đã được cập nhật!', 'success')
            return redirect(url_for('admin.categories'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating category: {str(e)}")
            flash('Có lỗi xảy ra khi cập nhật thể loại.', 'danger')

    # Pre-populate form with current category data
    if request.method == 'GET':
        form.name.data = category.CategoryName
        form.description.data = category.Description
        form.parent_category.data = category.ParentCategoryID if category.ParentCategoryID else 0
        form.status.data = category.Status

    return render_template('admin/category_form.html', title='Sửa thông tin thể loại', form=form, category=category)


@admin_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
@admin_required
def delete_category(category_id):
    """Delete a category."""
    try:
        category = Category.query.get_or_404(category_id)

        # Check if category has books
        books = Book.query.filter_by(CategoryID=category_id).first()
        if books:
            flash('Không thể xóa thể loại này vì đã có sách thuộc thể loại!', 'danger')
            return redirect(url_for('admin.categories'))

        # Check if category has subcategories
        subcategories = Category.query.filter_by(ParentCategoryID=category_id).first()
        if subcategories:
            flash('Không thể xóa thể loại này vì có thể loại con!', 'danger')
            return redirect(url_for('admin.categories'))

        # Delete category
        db.session.delete(category)
        db.session.commit()

        flash('Thể loại đã được xóa!', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting category: {str(e)}")
        flash('Có lỗi xảy ra khi xóa thể loại.', 'danger')

    return redirect(url_for('admin.categories'))


# User management
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users."""
    users = User.query.all()
    return render_template('admin/users.html', title='Quản lý người dùng', users=users)


@admin_bp.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit a user."""
    user = User.query.get_or_404(user_id)
    form = UserForm()

    # Populate role choices
    form.role.choices = [(role.RoleID, role.RoleName) for role in Role.query.all()]

    if form.validate_on_submit():
        try:
            # Check if username is already in use by another user
            existing_user = User.query.filter(
                User.Username == form.username.data,
                User.UserID != user_id
            ).first()

            if existing_user:
                flash('Tên tài khoản đã tồn tại!', 'danger')
                return render_template('admin/user_form.html', title='Sửa thông tin người dùng', form=form, user=user)

            # Check if email is already in use by another user
            existing_user = User.query.filter(
                User.Email == form.email.data,
                User.UserID != user_id
            ).first()

            if existing_user:
                flash('Email đã được sử dụng!', 'danger')
                return render_template('admin/user_form.html', title='Sửa thông tin người dùng', form=form, user=user)

            # Update user details
            user.Username = form.username.data
            user.Email = form.email.data
            user.FullName = form.full_name.data
            user.PhoneNumber = form.phone_number.data
            user.Address = form.address.data
            user.RoleID = form.role.data
            user.Status = form.status.data

            db.session.commit()

            flash('Thông tin người dùng đã được cập nhật!', 'success')
            return redirect(url_for('admin.users'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating user: {str(e)}")
            flash('Có lỗi xảy ra khi cập nhật người dùng.', 'danger')

    # Pre-populate form with current user data
    if request.method == 'GET':
        form.username.data = user.Username
        form.email.data = user.Email
        form.full_name.data = user.FullName
        form.phone_number.data = user.PhoneNumber
        form.address.data = user.Address
        form.role.data = user.RoleID
        form.status.data = user.Status

    return render_template('admin/user_form.html', title='Sửa thông tin người dùng', form=form, user=user)


@admin_bp.route('/users/ban/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def ban_user(user_id):
    """Ban/unban a user."""
    try:
        user = User.query.get_or_404(user_id)

        # Cannot ban yourself
        if user.UserID == current_user.UserID:
            flash('Bạn không thể khóa tài khoản của chính mình!', 'danger')
            return redirect(url_for('admin.users'))

        # Toggle status
        user.Status = not user.Status
        db.session.commit()

        status_text = 'kích hoạt' if user.Status else 'khóa'
        flash(f'Tài khoản {user.Username} đã được {status_text}!', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error banning user: {str(e)}")
        flash('Có lỗi xảy ra khi thay đổi trạng thái người dùng.', 'danger')

    return redirect(url_for('admin.users'))


# Order management
@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    """List all orders."""
    orders = Order.query.order_by(desc(Order.OrderDate)).all()
    return render_template('admin/orders.html', title='Quản lý đơn hàng', orders=orders)


@admin_bp.route('/orders/<int:order_id>')
@login_required
@admin_required
def order_detail(order_id):
    """View order details."""
    order = Order.query.get_or_404(order_id)
    order_details = OrderDetail.query.filter_by(OrderID=order_id).all()
    transactions = PaymentTransaction.query.filter_by(OrderID=order_id).all()

    return render_template('admin/order_detail.html',
                           title=f'Chi tiết đơn hàng #{order_id}',
                           order=order,
                           order_details=order_details,
                           transactions=transactions)


@admin_bp.route('/orders/update/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def update_order(order_id):
    """Update order status."""
    try:
        order = Order.query.get_or_404(order_id)

        status = request.form.get('status')
        payment_status = request.form.get('payment_status') == 'true'

        # Update order
        order.OrderStatus = status
        order.PaymentStatus = payment_status
        db.session.commit()

        flash('Trạng thái đơn hàng đã được cập nhật!', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating order: {str(e)}")
        flash('Có lỗi xảy ra khi cập nhật đơn hàng.', 'danger')

    return redirect(url_for('admin.order_detail', order_id=order_id))


# Review management
@admin_bp.route('/reviews')
@login_required
@admin_required
def reviews():
    """List all reviews."""
    reviews = Review.query.order_by(desc(Review.ReviewDate)).all()
    return render_template('admin/reviews.html', title='Quản lý đánh giá', reviews=reviews)


@admin_bp.route('/reviews/toggle/<int:review_id>', methods=['POST'])
@login_required
@admin_required
def toggle_review(review_id):
    """Approve/hide a review."""
    try:
        review = Review.query.get_or_404(review_id)

        # Toggle status
        review.Status = not review.Status
        db.session.commit()

        status_text = 'hiển thị' if review.Status else 'ẩn'
        flash(f'Đánh giá đã được {status_text}!', 'success')

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error toggling review: {str(e)}")
        flash('Có lỗi xảy ra khi thay đổi trạng thái đánh giá.', 'danger')

    return redirect(url_for('admin.reviews'))