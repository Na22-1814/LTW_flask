from flask import Blueprint, render_template, url_for, flash, redirect, request, abort, current_app
from flask_login import current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional
from app import db
from app.models import User, Order, OrderDetail, Book, PaymentTransaction
from sqlalchemy import desc
from datetime import datetime, timezone
import secrets
import string

user_bp = Blueprint('user', __name__)


# User profile form
class UserProfileForm(FlaskForm):
    full_name = StringField('Họ và tên', validators=[Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=100)])
    phone_number = StringField('Số điện thoại', validators=[Length(max=20)])
    address = TextAreaField('Địa chỉ', validators=[Length(max=200)])
    submit = SubmitField('Cập nhật')


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Display and update user profile."""
    form = UserProfileForm()

    if form.validate_on_submit():
        try:
            # Check if email is already in use by another user
            existing_user = User.query.filter(
                User.Email == form.email.data,
                User.UserID != current_user.UserID
            ).first()

            if existing_user:
                flash('Email đã được sử dụng bởi tài khoản khác.', 'danger')
            else:
                current_user.Email = form.email.data
                current_user.FullName = form.full_name.data
                current_user.PhoneNumber = form.phone_number.data
                current_user.Address = form.address.data

                db.session.commit()
                flash('Thông tin tài khoản đã được cập nhật!', 'success')
                return redirect(url_for('user.profile'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating profile: {str(e)}")
            flash('Có lỗi xảy ra khi cập nhật thông tin.', 'danger')

    # Pre-populate form with current user data
    if request.method == 'GET':
        form.full_name.data = current_user.FullName
        form.email.data = current_user.Email
        form.phone_number.data = current_user.PhoneNumber
        form.address.data = current_user.Address

    # Get user's recently purchased books
    recent_orders = OrderDetail.query.join(Order).filter(
        Order.UserID == current_user.UserID,
        Order.PaymentStatus == True
    ).order_by(desc(Order.OrderDate)).limit(5).all()

    return render_template('user/profile.html',
                           title='Tài khoản',
                           form=form,
                           recent_orders=recent_orders)


@user_bp.route('/orders')
@login_required
def orders():
    """Display user's orders."""
    user_orders = Order.query.filter_by(UserID=current_user.UserID).order_by(desc(Order.OrderDate)).all()
    return render_template('user/orders.html', title='Đơn hàng của tôi', orders=user_orders)


@user_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Display order details."""
    order = Order.query.get_or_404(order_id)

    # Check if the order belongs to the current user
    if order.UserID != current_user.UserID and not current_user.is_admin():
        abort(403)

    order_details = OrderDetail.query.filter_by(OrderID=order_id).all()
    transactions = PaymentTransaction.query.filter_by(OrderID=order_id).all()

    return render_template('user/order_detail.html',
                           title=f'Chi tiết đơn hàng #{order_id}',
                           order=order,
                           order_details=order_details,
                           transactions=transactions)


@user_bp.route('/download/<int:order_detail_id>')
@login_required
def download_book(order_detail_id):
    """Download a purchased book."""
    try:
        order_detail = OrderDetail.query.get_or_404(order_detail_id)
        order = Order.query.get(order_detail.OrderID)

        # Check if the order belongs to the current user and has been paid
        if (order.UserID != current_user.UserID and not current_user.is_admin()) or not order.PaymentStatus:
            abort(403)

        # Update download status
        order_detail.DownloadStatus = True
        order_detail.DownloadDate = datetime.now(timezone.utc)
        db.session.commit()

        # Get book
        book = Book.query.get(order_detail.BookID)

        # Redirect to the book file
        return redirect(book.FilePath)

    except Exception as e:
        current_app.logger.error(f"Error downloading book: {str(e)}")
        flash('Có lỗi xảy ra khi tải sách.', 'danger')
        return redirect(url_for('user.orders'))


@user_bp.route('/book/<int:book_id>/buy', methods=['GET', 'POST'])
@login_required
def buy_book(book_id):
    """Purchase a book."""
    book = Book.query.get_or_404(book_id)

    # Check if user has already purchased this book
    existing_purchase = OrderDetail.query.join(Order).filter(
        Order.UserID == current_user.UserID,
        OrderDetail.BookID == book_id,
        Order.PaymentStatus == True
    ).first()

    if existing_purchase:
        flash('Bạn đã mua sách này rồi.', 'info')
        return redirect(url_for('book.book_detail', book_id=book_id))

    if request.method == 'POST':
        try:
            payment_method = request.form.get('payment_method')

            # Convert book price to float for SQL Server compatibility
            book_price = float(book.Price)

            # Create new order
            order = Order(
                UserID=current_user.UserID,
                OrderDate=datetime.now(timezone.utc),
                TotalAmount=book_price,
                PaymentMethod=payment_method,
                PaymentStatus=False,
                OrderStatus='Chờ thanh toán'
            )

            db.session.add(order)
            db.session.commit()

            # Create order detail
            order_detail = OrderDetail(
                OrderID=order.OrderID,
                BookID=book_id,
                Price=book_price,
                DownloadStatus=False
            )

            db.session.add(order_detail)

            # Generate transaction code
            transaction_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))

            # Create payment transaction
            transaction = PaymentTransaction(
                OrderID=order.OrderID,
                Amount=book_price,
                PaymentMethod=payment_method,
                TransactionDate=datetime.now(timezone.utc),
                TransactionCode=transaction_code,
                Status='Đang xử lý'
            )

            db.session.add(transaction)
            db.session.commit()

            # For demonstration purposes, automatically approve the payment
            # In a real application, you would integrate with payment gateways
            order.PaymentStatus = True
            order.OrderStatus = 'Hoàn thành'
            transaction.Status = 'Thành công'
            db.session.commit()

            flash('Thanh toán thành công! Bạn có thể tải sách ngay bây giờ.', 'success')
            return redirect(url_for('user.order_detail', order_id=order.OrderID))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error buying book: {str(e)}")
            flash('Có lỗi xảy ra khi mua sách. Vui lòng thử lại.', 'danger')

    return render_template('user/buy_book.html', title=f'Mua sách: {book.Title}', book=book)