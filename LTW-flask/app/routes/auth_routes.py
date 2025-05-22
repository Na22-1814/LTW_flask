from flask import Blueprint, render_template, url_for, flash, redirect, request
from flask_login import login_user, current_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from app import db, bcrypt
from app.models import User, Role
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Tên tài khoản', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Mật khẩu', validators=[DataRequired()])
    confirm_password = PasswordField('Xác nhận mật khẩu', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Đăng ký')

    def validate_username(self, username):
        user = User.query.filter_by(Username=username.data).first()
        if user:
            raise ValidationError('Tên tài khoản đã tồn tại. Vui lòng chọn tên khác.')

    def validate_email(self, email):
        user = User.query.filter_by(Email=email.data).first()
        if user:
            raise ValidationError('Email đã được sử dụng. Vui lòng dùng email khác.')


class LoginForm(FlaskForm):
    username = StringField('Tên tài khoản', validators=[DataRequired()])
    password = PasswordField('Mật khẩu', validators=[DataRequired()])
    remember = BooleanField('Nhớ tài khoản')
    submit = SubmitField('Đăng nhập')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('book.new_books'))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        # Get user role ID (2 for regular users)
        user_role = Role.query.filter_by(RoleName='User').first()
        if not user_role:
            flash('Lỗi hệ thống. Vui lòng thử lại sau.', 'danger')
            return redirect(url_for('auth.register'))

        user = User(
            Username=form.username.data,
            Email=form.email.data,
            Password=hashed_password,
            RoleID=user_role.RoleID,
            RegisterDate=datetime.utcnow()
        )

        db.session.add(user)
        db.session.commit()

        flash('Tài khoản đã được tạo! Bạn có thể đăng nhập ngay bây giờ.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', title='Đăng Ký', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('book.new_books'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(Username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.Password, form.password.data):
            login_user(user, remember=form.remember.data)
            user.LastLogin = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('book.new_books'))
        else:
            flash('Đăng nhập không thành công. Vui lòng kiểm tra tên tài khoản và mật khẩu.', 'danger')

    return render_template('auth/login.html', title='Đăng Nhập', form=form)


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('book.new_books'))