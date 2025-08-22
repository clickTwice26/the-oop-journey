#!/usr/bin/env python3

import sys
import os
import shutil
from datetime import datetime

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Import directly from app.py file using importlib
import importlib.util
spec = importlib.util.spec_from_file_location("main_app", "app.py")
main_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_app)

from app.models import db, User, Quiz, Question, QuizResult, Conversation, Message, Assessment, AssessmentResult

def backup_and_fresh_migration():
    """Backup existing database and create fresh database with new schema"""
    try:
        # Create Flask app
        flask_app = main_app.create_app()
        
        with flask_app.app_context():
            # Backup existing database if it exists
            db_path = os.path.join('instance', 'quizpilot.db')
            if os.path.exists(db_path):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f'instance/quizpilot_backup_{timestamp}.db'
                shutil.copy2(db_path, backup_path)
                print(f"✅ Database backed up to: {backup_path}")
                
                # Remove old database
                os.remove(db_path)
                print("🗑️ Old database removed")
            
            # Create fresh database with new schema
            db.create_all()
            print("✅ Fresh database created with new schema!")
            
            # Create test admin user
            admin_user = User(
                username='admin',
                email='admin@quizpilot.com',
                full_name='Administrator'
            )
            admin_user.set_password('admin123')
            
            test_user = User(
                username='testuser',
                email='test@quizpilot.com',
                full_name='Test User'
            )
            test_user.set_password('test123')
            
            db.session.add(admin_user)
            db.session.add(test_user)
            db.session.commit()
            
            print("✅ Default users created:")
            print("   - admin / admin123")
            print("   - testuser / test123")
            
            # Verify tables
            users_count = User.query.count()
            print(f"📊 Total users in database: {users_count}")
            
            return True
            
    except Exception as e:
        print(f"💥 Migration failed: {str(e)}")
        return False

if __name__ == '__main__':
    success = backup_and_fresh_migration()
    if success:
        print("\n🎉 Fresh migration completed successfully!")
        print("🔐 You can now login with admin/admin123 or testuser/test123")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)
