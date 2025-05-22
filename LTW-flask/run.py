from app import create_app, db
import os

app = create_app(os.getenv('FLASK_CONFIG', 'development'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))