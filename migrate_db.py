#!/usr/bin/env python3

import sys
import os

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Import directly from app.py file
from app import create_app
from app.models import db, User, Quiz, Question, QuizResult, Conversation, Message, Assessment, AssessmentResult

def migrate_database():
    """Create/update database tables"""
    flask_app = create_app()
    
    with flask_app.app_context():
        try:
            # Create all tables
            db.create_all()
            print("✅ Database tables created/updated successfully!")
            
            # Check if User table exists and has records
            user_count = User.query.count()
            print(f"📊 Users in database: {user_count}")
            
            # Check other tables
            quiz_count = Quiz.query.count()
            print(f"📊 Quizzes in database: {quiz_count}")
            
        except Exception as e:
            print(f"❌ Error creating database tables: {e}")
            return False
    
    return True

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n🚀 Database migration completed successfully!")
        print("You can now run the application with authentication enabled.")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
