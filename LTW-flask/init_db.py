from app import create_app, db
from app.models import User, Role, Category
from flask_bcrypt import Bcrypt
from datetime import datetime
import os

app = create_app(os.getenv('FLASK_CONFIG', 'development'))
bcrypt = Bcrypt(app)


def init_db():
    """Initialize database with basic data."""
    with app.app_context():
        # Create roles if they don't exist
        admin_role = Role.query.filter_by(RoleName='Admin').first()
        if not admin_role:
            admin_role = Role(RoleName='Admin', Description='Quản trị viên hệ thống')
            db.session.add(admin_role)

        user_role = Role.query.filter_by(RoleName='User').first()
        if not user_role:
            user_role = Role(RoleName='User', Description='Người dùng thông thường')
            db.session.add(user_role)

        db.session.commit()

        # Create admin user if it doesn't exist
        admin_user = User.query.filter_by(Username='admin').first()
        if not admin_user:
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin_user = User(
                Username='admin',
                Password=hashed_password,
                Email='admin@aloha.vn',
                FullName='Quản trị viên',
                RoleID=admin_role.RoleID,
                RegisterDate=datetime.utcnow(),
                Status=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print('Admin user created')

        # Create main categories if they don't exist
        categories = [
            ('Lập trình', 'Sách về lập trình và phát triển phần mềm', None),
            ('Văn học', 'Sách văn học trong và ngoài nước', None),
            ('Kinh tế', 'Sách về kinh tế, kinh doanh, tài chính', None),
            ('Kỹ năng sống', 'Sách phát triển bản thân và kỹ năng sống', None),
            ('Python', 'Sách về ngôn ngữ lập trình Python', 1),
            ('Java', 'Sách về ngôn ngữ lập trình Java', 1),
            ('JavaScript', 'Sách về ngôn ngữ lập trình JavaScript', 1),
            ('C++', 'Sách về ngôn ngữ lập trình C++', 1),
            ('Văn học Việt Nam', 'Tác phẩm của các nhà văn Việt Nam', 2),
            ('Văn học nước ngoài', 'Tác phẩm của các nhà văn quốc tế', 2),
        ]

        for name, desc, parent_id in categories:
            category = Category.query.filter_by(CategoryName=name).first()
            if not category:
                category = Category(
                    CategoryName=name,
                    Description=desc,
                    ParentCategoryID=parent_id,
                    Status=True
                )
                db.session.add(category)

        db.session.commit()
        print('Categories created')

        print('Database initialized successfully')


if __name__ == '__main__':
    init_db()