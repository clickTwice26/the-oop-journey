from flask import Flask
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__, template_folder='app/templates', static_folder='app/static')
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'oop-journey-secret-key-change-in-production-2025')
    
    # Use absolute path for database
    db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'quizpilot.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 104857600))  # 100MB
    
    # Session configuration
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_TYPE'] = 'filesystem'
    
    # Initialize extensions
    from app.models import db
    db.init_app(app)
    
    migrate = Migrate()
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes import main_bp, quiz_bp, api_bp
    from app.auth_routes import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(quiz_bp, url_prefix='/quiz')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        from app.models import db
        db.create_all()
    app.run(debug=True, port=8080)
