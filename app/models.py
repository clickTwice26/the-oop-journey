from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import Text
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True)
    conversations = db.relationship('Conversation', backref='user', lazy=True)
    assessment_results = db.relationship('AssessmentResult', backref='user', lazy=True)
    quizzes = db.relationship('Quiz', backref='creator', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'student_id': self.student_id,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    source_file_name = db.Column(db.String(255))
    source_file_type = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('QuizResult', backref='quiz', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'source_file_name': self.source_file_name,
            'source_file_type': self.source_file_type,
            'created_at': self.created_at.isoformat(),
            'questions': [q.to_dict() for q in self.questions]
        }

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text, nullable=False)
    option_b = db.Column(db.Text, nullable=False)
    option_c = db.Column(db.Text, nullable=False)
    option_d = db.Column(db.Text, nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # A, B, C, or D
    explanation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'question_text': self.question_text,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'options': [self.option_a, self.option_b, self.option_c, self.option_d],
            'correct_answer': self.correct_answer,
            'explanation': self.explanation
        }

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_session = db.Column(db.String(100), nullable=True)  # Keep for backward compatibility
    score_percentage = db.Column(db.Integer, nullable=False)
    correct_answers = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    time_spent_minutes = db.Column(db.Integer)
    user_answers = db.Column(JSON)  # Stores list of user answers
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'quiz_id': self.quiz_id,
            'user_session': self.user_session,
            'score_percentage': self.score_percentage,
            'correct_answers': self.correct_answers,
            'total_questions': self.total_questions,
            'time_spent_minutes': self.time_spent_minutes,
            'user_answers': self.user_answers,
            'completed_at': self.completed_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default='New Conversation')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_session = db.Column(db.String(100), nullable=True)  # Keep for backward compatibility
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'user_session': self.user_session,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'message_count': len(self.messages),
            'last_message': self.messages[-1].to_dict() if self.messages else None
        }

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, nullable=False, default=True)
    image_url = db.Column(Text)  # For base64 images
    message_type = db.Column(db.String(20), default='text')  # text, mcq, true_false, suggestion
    interactive_data = db.Column(JSON)  # For storing MCQ/interactive content
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'content': self.content,
            'is_user': self.is_user,
            'image_url': self.image_url,
            'message_type': self.message_type,
            'interactive_data': self.interactive_data,
            'timestamp': self.timestamp.isoformat()
        }

class InteractiveLearningSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # mcq, true_false
    question_data = db.Column(JSON, nullable=False)
    user_answer = db.Column(db.String(100))
    is_correct = db.Column(db.Boolean)
    explanation = db.Column(db.Text)
    answered_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = db.relationship('Conversation', backref='learning_sessions')
    message = db.relationship('Message', backref='learning_session')
    
    def to_dict(self):
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'message_id': self.message_id,
            'question_type': self.question_type,
            'question_data': self.question_data,
            'user_answer': self.user_answer,
            'is_correct': self.is_correct,
            'explanation': self.explanation,
            'answered_at': self.answered_at.isoformat() if self.answered_at else None,
            'created_at': self.created_at.isoformat()
        }

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    concept = db.Column(db.String(50), nullable=False)  # encapsulation, inheritance, polymorphism, abstraction
    difficulty = db.Column(db.String(20), default='medium')  # easy, medium, hard
    questions = db.Column(JSON, nullable=False)  # JSON array of questions
    assessment_metadata = db.Column(JSON)  # Additional metadata like generation info
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    results = db.relationship('AssessmentResult', backref='assessment', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'concept': self.concept,
            'difficulty': self.difficulty,
            'questions': self.questions,
            'assessment_metadata': self.assessment_metadata,
            'created_at': self.created_at.isoformat()
        }

class AssessmentResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_session = db.Column(db.String(100), nullable=True)  # Keep for backward compatibility
    score_percentage = db.Column(db.Float, nullable=False)
    user_answers = db.Column(JSON, nullable=False)  # User's answers
    ai_feedback = db.Column(JSON)  # AI-generated feedback
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'user_session': self.user_session,
            'score_percentage': self.score_percentage,
            'user_answers': self.user_answers,
            'ai_feedback': self.ai_feedback,
            'completed_at': self.completed_at.isoformat()
        }
