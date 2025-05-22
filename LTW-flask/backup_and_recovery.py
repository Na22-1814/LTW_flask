"""
Backup and Recovery script for database
"""

from app import create_app, db
from app.models import *
from sqlalchemy import text
import os
from datetime import datetime

app = create_app(os.getenv('FLASK_CONFIG', 'development'))

def backup_data():
    """Backup critical data before migration."""
    with app.app_context():
        try:
            print("Starting data backup...")

            # Backup Books data
            books = db.session.execute(text("""
                SELECT BookID, Title, Author, Publisher, PublishYear, 
                       CategoryID, Description, Price, CoverImage, FilePath, 
                       PageCount, AddedDate, UpdatedDate, Status
                FROM Books
            """)).fetchall()

            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_books_{timestamp}.sql"

            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write("-- Books Backup\n")
                f.write("-- Generated on: {}\n\n".format(datetime.now()))

                for book in books:
                    price_value = float(book.Price) if book.Price else 0.0

                    # Escape single quotes in text fields
                    title = book.Title.replace("'", "''") if book.Title else ''
                    author = book.Author.replace("'", "''") if book.Author else ''
                    publisher = book.Publisher.replace("'", "''") if book.Publisher else ''
                    description = book.Description.replace("'", "''") if book.Description else ''
                    cover_image = book.CoverImage.replace("'", "''") if book.CoverImage else ''
                    file_path = book.FilePath.replace("'", "''") if book.FilePath else ''

                    # Handle UpdatedDate properly
                    updated_date_str = "NULL"
                    if book.UpdatedDate:
                        updated_date_str = "'{}'".format(book.UpdatedDate)

                    # Build INSERT statement without nested f-strings
                    insert_stmt = (
                        "INSERT INTO Books (BookID, Title, Author, Publisher, PublishYear, "
                        "CategoryID, Description, Price, CoverImage, FilePath, PageCount, "
                        "AddedDate, UpdatedDate, Status) VALUES "
                        "({}, '{}', '{}', '{}', {}, {}, '{}', {}, '{}', '{}', {}, '{}', {}, {});\n"
                    ).format(
                        book.BookID,
                        title,
                        author,
                        publisher,
                        book.PublishYear or 'NULL',
                        book.CategoryID,
                        description,
                        price_value,
                        cover_image,
                        file_path,
                        book.PageCount or 'NULL',
                        book.AddedDate,
                        updated_date_str,
                        1 if book.Status else 0
                    )

                    f.write(insert_stmt)

            print(f"Backup completed: {backup_file}")

        except Exception as e:
            print(f"Backup failed: {str(e)}")
            raise e

def backup_all_tables():
    """Backup all critical tables."""
    with app.app_context():
        try:
            print("Starting full data backup...")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"backup_full_{timestamp}.sql"

            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write("-- Full Database Backup\n")
                f.write("-- Generated on: {}\n\n".format(datetime.now()))

                # Backup Books
                f.write("-- Books Table\n")
                books = db.session.execute(text("SELECT * FROM Books")).fetchall()
                for book in books:
                    price_value = float(book.Price) if book.Price else 0.0
                    f.write("INSERT INTO Books VALUES {};\n".format(tuple([
                        book.BookID, book.Title, book.Author, book.Publisher,
                        book.PublishYear, book.CategoryID, book.Description,
                        price_value, book.CoverImage, book.FilePath, book.PageCount,
                        str(book.AddedDate), str(book.UpdatedDate) if book.UpdatedDate else None,
                        book.Status
                    ])))

                # Backup Orders
                f.write("\n-- Orders Table\n")
                orders = db.session.execute(text("SELECT * FROM Orders")).fetchall()
                for order in orders:
                    total_amount = float(order.TotalAmount) if order.TotalAmount else 0.0
                    f.write("INSERT INTO Orders VALUES {};\n".format(tuple([
                        order.OrderID, order.UserID, str(order.OrderDate),
                        total_amount, order.PaymentMethod, order.PaymentStatus,
                        order.OrderStatus
                    ])))

                # Backup OrderDetails
                f.write("\n-- OrderDetails Table\n")
                order_details = db.session.execute(text("SELECT * FROM OrderDetails")).fetchall()
                for detail in order_details:
                    price_value = float(detail.Price) if detail.Price else 0.0
                    f.write("INSERT INTO OrderDetails VALUES {};\n".format(tuple([
                        detail.OrderDetailID, detail.OrderID, detail.BookID,
                        price_value, detail.DownloadStatus,
                        str(detail.DownloadDate) if detail.DownloadDate else None
                    ])))

                # Backup PaymentTransactions
                f.write("\n-- PaymentTransactions Table\n")
                transactions = db.session.execute(text("SELECT * FROM PaymentTransactions")).fetchall()
                for trans in transactions:
                    amount_value = float(trans.Amount) if trans.Amount else 0.0
                    f.write("INSERT INTO PaymentTransactions VALUES {};\n".format(tuple([
                        trans.TransactionID, trans.OrderID, amount_value,
                        trans.PaymentMethod, str(trans.TransactionDate),
                        trans.TransactionCode, trans.Status
                    ])))

            print(f"Full backup completed: {backup_file}")

        except Exception as e:
            print(f"Full backup failed: {str(e)}")
            raise e

def verify_data_integrity():
    """Verify data integrity after migration."""
    with app.app_context():
        try:
            print("Verifying data integrity...")

            # Check Books table
            book_count = db.session.execute(text("SELECT COUNT(*) FROM Books")).scalar()
            print(f"Books count: {book_count}")

            # Check Orders table
            order_count = db.session.execute(text("SELECT COUNT(*) FROM Orders")).scalar()
            print(f"Orders count: {order_count}")

            # Check OrderDetails table
            order_detail_count = db.session.execute(text("SELECT COUNT(*) FROM OrderDetails")).scalar()
            print(f"OrderDetails count: {order_detail_count}")

            # Check PaymentTransactions table
            transaction_count = db.session.execute(text("SELECT COUNT(*) FROM PaymentTransactions")).scalar()
            print(f"PaymentTransactions count: {transaction_count}")

            # Test price values
            sample_book = db.session.execute(text("SELECT TOP 1 Price FROM Books WHERE Price IS NOT NULL")).fetchone()
            if sample_book:
                print(f"Sample book price: {sample_book.Price} (type: {type(sample_book.Price)})")

            # Test data type compatibility
            print("\nTesting data type compatibility...")
            test_result = db.session.execute(text("""
                SELECT 
                    MIN(Price) as min_price,
                    MAX(Price) as max_price,
                    AVG(Price) as avg_price
                FROM Books 
                WHERE Price IS NOT NULL
            """)).fetchone()

            if test_result:
                print(f"Price statistics - Min: {test_result.min_price}, Max: {test_result.max_price}, Avg: {test_result.avg_price}")

            print("Data integrity verification completed!")

        except Exception as e:
            print(f"Verification failed: {str(e)}")
            raise e

def test_insert_operation():
    """Test insert operation with new data types."""
    with app.app_context():
        try:
            print("Testing insert operation...")

            # Test creating a new book record
            test_book = Book(
                Title="Test Book for Migration",
                Author="Test Author",
                Publisher="Test Publisher",
                PublishYear=2025,
                CategoryID=1,
                Description="Test description for migration testing",
                Price=99.99,
                CoverImage="http://test.com/cover.jpg",
                FilePath="http://test.com/book.pdf",
                PageCount=100,
                AddedDate=datetime.now(),
                Status=True
            )

            db.session.add(test_book)
            db.session.commit()

            print(f"Test book created successfully with ID: {test_book.BookID}")

            # Clean up test data
            db.session.delete(test_book)
            db.session.commit()
            print("Test book deleted successfully")

            print("Insert operation test completed!")

        except Exception as e:
            db.session.rollback()
            print(f"Insert operation test failed: {str(e)}")
            raise e

if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'backup':
            backup_data()
        elif command == 'backup-all':
            backup_all_tables()
        elif command == 'verify':
            verify_data_integrity()
        elif command == 'test':
            test_insert_operation()
        else:
            print("Usage: python backup_and_recovery.py [backup|backup-all|verify|test]")
    else:
        print("Available commands:")
        print("  backup      - Backup Books table only")
        print("  backup-all  - Backup all tables")
        print("  verify      - Verify data integrity")
        print("  test        - Test insert operation")
        print("\nUsage: python backup_and_recovery.py [command]")