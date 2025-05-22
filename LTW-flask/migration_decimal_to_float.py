"""
Migration script to convert Decimal columns to Float for SQL Server compatibility
Run this script after updating the models
"""

from app import create_app, db
from sqlalchemy import text
import os

app = create_app(os.getenv('FLASK_CONFIG', 'development'))


def migrate_decimal_to_float():
    """Convert Decimal columns to Float in SQL Server."""
    with app.app_context():
        try:
            print("Starting migration: Convert Decimal to Float...")

            # Get current connection
            connection = db.engine.connect()

            # Start transaction
            trans = connection.begin()

            try:
                # Update Books table - Price column
                print("Updating Books.Price column...")
                connection.execute(text("""
                                        ALTER TABLE Books
                                        ALTER
                                        COLUMN Price FLOAT NOT NULL
                                        """))

                # Update Orders table - TotalAmount column
                print("Updating Orders.TotalAmount column...")
                connection.execute(text("""
                                        ALTER TABLE Orders
                                        ALTER
                                        COLUMN TotalAmount FLOAT NOT NULL
                                        """))

                # Update OrderDetails table - Price column
                print("Updating OrderDetails.Price column...")
                connection.execute(text("""
                                        ALTER TABLE OrderDetails
                                        ALTER
                                        COLUMN Price FLOAT NOT NULL
                                        """))

                # Update PaymentTransactions table - Amount column
                print("Updating PaymentTransactions.Amount column...")
                connection.execute(text("""
                                        ALTER TABLE PaymentTransactions
                                        ALTER
                                        COLUMN Amount FLOAT NOT NULL
                                        """))

                # Commit transaction
                trans.commit()
                print("Migration completed successfully!")

            except Exception as e:
                # Rollback transaction on error
                trans.rollback()
                print(f"Migration failed: {str(e)}")
                raise e

            finally:
                connection.close()

        except Exception as e:
            print(f"Error during migration: {str(e)}")
            raise e


if __name__ == '__main__':
    migrate_decimal_to_float()