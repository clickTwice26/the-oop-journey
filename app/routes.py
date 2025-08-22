from flask import Blueprint, render_template, request, jsonify, current_app, session
from werkzeug.utils import secure_filename
from app.models import Quiz, Question, QuizResult, Message, Conversation, Assessment, AssessmentResult, db
from app.services.quiz_generation_service import QuizGenerationService
from app.services.file_processing_service import FileProcessingService
from app.services.chat_service import ChatService
from app.services.assessment_service import AssessmentService
import os
import uuid
from datetime import datetime

# Blueprints
main_bp = Blueprint('main', __name__)
quiz_bp = Blueprint('quiz', __name__)
api_bp = Blueprint('api', __name__)

# File upload configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Main routes
@main_bp.route('/')
def index():
    return render_template('index.html', title='OOP Journey - AI-Powered Learning')

@main_bp.route('/learn')
def learn():
    return render_template('learn.html', title='Learn OOP Concepts')

@main_bp.route('/learn/inheritance')
def learn_inheritance():
    return render_template('learn/inheritance_java.html', title='Master Inheritance - OOP Concepts')

@main_bp.route('/learn/polymorphism')
def learn_polymorphism():
    return render_template('learn/polymorphism_java.html', title='Master Polymorphism - OOP Concepts')

@main_bp.route('/learn/abstraction')
def learn_abstraction():
    return render_template('learn/abstraction_java.html', title='Master Abstraction - OOP Concepts')

@main_bp.route('/learn/encapsulation')
def learn_encapsulation():
    return render_template('learn/encapsulation_java.html', title='Master Encapsulation - OOP Concepts')

@main_bp.route('/learn/encapsulation/assessment')
def assess_encapsulation():
    return render_template('assessment.html', title='Encapsulation Assessment - OOP Concepts')

@main_bp.route('/learn/inheritance/assessment')
def assess_inheritance():
    return render_template('assessment.html', title='Inheritance Assessment - OOP Concepts')

@main_bp.route('/learn/polymorphism/assessment')
def assess_polymorphism():
    return render_template('assessment.html', title='Polymorphism Assessment - OOP Concepts')

@main_bp.route('/learn/abstraction/assessment')
def assess_abstraction():
    return render_template('assessment.html', title='Abstraction Assessment - OOP Concepts')

@main_bp.route('/chat')
def chat():
    chat_service = ChatService()
    conversations = chat_service.get_user_conversations()
    
    # Get current conversation ID from query parameter
    conversation_id = request.args.get('conversation_id', type=int)
    current_conversation = None
    messages = []
    
    if conversation_id:
        current_conversation = chat_service.get_or_create_conversation(conversation_id)
        messages = Message.query.filter_by(
            conversation_id=current_conversation.id
        ).order_by(Message.timestamp.asc()).all()
    
    return render_template('chat.html', 
                         title='AI Chat', 
                         conversations=conversations,
                         current_conversation=current_conversation,
                         messages=messages)

# Quiz routes
@quiz_bp.route('/')
@quiz_bp.route('/generator')
def quiz_generator():
    return render_template('quiz-generator.html', title='Quiz Generator')

@quiz_bp.route('/list')
def quiz_list():
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()
    return render_template('quiz-list.html', title='My Quizzes', quizzes=quizzes)

@quiz_bp.route('/take/<int:quiz_id>')
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz-view.html', title=f'Take Quiz: {quiz.title}', quiz=quiz)

@quiz_bp.route('/review')
def quiz_review():
    quiz_id = request.args.get('quizId', type=int)
    result_id = request.args.get('resultId', type=int)
    
    if not quiz_id:
        return render_template('error.html', error='Quiz ID is required')
    
    quiz = Quiz.query.get_or_404(quiz_id)
    result = None
    if result_id:
        result = QuizResult.query.get(result_id)
    
    return render_template('quiz-review.html', 
                         title=f'Review: {quiz.title}', 
                         quiz=quiz, 
                         result=result)

# API routes
@api_bp.route('/quizzes/generate', methods=['POST'])
def generate_quiz():
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Get form data
        title = request.form.get('title', 'Untitled Quiz')
        num_questions = int(request.form.get('numQuestions', 10))
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 
                                f"{uuid.uuid4()}_{filename}")
        file.save(file_path)
        
        # Generate quiz
        current_app.logger.info(f"Generating quiz from file: {filename}")
        quiz_service = QuizGenerationService()
        quiz_data = quiz_service.generate_quiz_from_file(file_path, title, num_questions)
        current_app.logger.info(f"Quiz generated successfully: {len(quiz_data['questions'])} questions")
        
        # Save to database
        quiz = Quiz(
            title=quiz_data['title'],
            description=quiz_data.get('description', ''),
            source_file_name=filename,
            source_file_type=file.content_type
        )
        db.session.add(quiz)
        db.session.flush()  # Get the quiz ID
        
        # Save questions
        for q_data in quiz_data['questions']:
            question = Question(
                quiz_id=quiz.id,
                question_text=q_data['question'],
                option_a=q_data['options'][0],
                option_b=q_data['options'][1],
                option_c=q_data['options'][2],
                option_d=q_data['options'][3],
                correct_answer=q_data['correct_answer'],
                explanation=q_data.get('explanation', '')
            )
            db.session.add(question)
        
        db.session.commit()
        
        # Clean up uploaded file
        os.remove(file_path)
        
        return jsonify({'id': quiz.id, 'title': quiz.title, 'message': 'Quiz generated successfully'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating quiz: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/quizzes/<int:quiz_id>')
def get_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    return jsonify(quiz.to_dict())

@api_bp.route('/quizzes')
def get_quizzes():
    limit = request.args.get('limit', type=int)
    query = Quiz.query.order_by(Quiz.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    quizzes = query.all()
    return jsonify([quiz.to_dict() for quiz in quizzes])

@api_bp.route('/quizzes/<int:quiz_id>/submit', methods=['POST'])
def submit_quiz(quiz_id):
    try:
        data = request.get_json()
        
        # Generate user session if not exists
        if 'user_session' not in session:
            session['user_session'] = str(uuid.uuid4())
        
        # Create quiz result
        result = QuizResult(
            quiz_id=quiz_id,
            user_session=session['user_session'],
            score_percentage=data.get('scorePercentage', 0),
            correct_answers=data.get('correctAnswers', 0),
            total_questions=data.get('totalQuestions', 0),
            time_spent_minutes=data.get('timeSpentMinutes', 0),
            user_answers=data.get('userAnswers', [])
        )
        
        db.session.add(result)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'resultId': result.id,
            'message': 'Quiz results saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting quiz: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/quizzes/results/<int:result_id>')
def get_quiz_result(result_id):
    result = QuizResult.query.get_or_404(result_id)
    return jsonify(result.to_dict())

@api_bp.route('/quizzes/<int:quiz_id>/stats')
def get_quiz_stats(quiz_id):
    results = QuizResult.query.filter_by(quiz_id=quiz_id).all()
    
    if not results:
        return jsonify({'averageScore': 0, 'attemptCount': 0})
    
    avg_score = sum(r.score_percentage for r in results) / len(results)
    
    return jsonify({
        'averageScore': round(avg_score, 2),
        'attemptCount': len(results)
    })

@api_bp.route('/chat/send', methods=['POST'])
def send_chat_message():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        chat_service = ChatService()
        result = chat_service.send_message(message, conversation_id)
        
        return jsonify({
            'success': True,
            'response': result['response'],
            'conversation_id': result['conversation_id']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/new', methods=['POST'])
def create_new_conversation():
    try:
        chat_service = ChatService()
        conversation = chat_service.get_or_create_conversation()
        
        return jsonify({
            'success': True,
            'conversation_id': conversation.id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/conversation/<int:conversation_id>/rename', methods=['POST'])
def rename_conversation(conversation_id):
    try:
        data = request.get_json()
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return jsonify({'error': 'Title is required'}), 400
        
        chat_service = ChatService()
        success = chat_service.update_conversation_title(conversation_id, new_title)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/conversation/<int:conversation_id>', methods=['DELETE'])
def delete_conversation_route(conversation_id):
    try:
        chat_service = ChatService()
        success = chat_service.delete_conversation(conversation_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/message', methods=['POST'])
def send_message():
    try:
        data = request.get_json()
        content = data.get('message', '')
        image_data = data.get('image')
        conversation_id = data.get('conversation_id')
        
        if not content and not image_data:
            return jsonify({'error': 'Message content or image is required'}), 400
        
        chat_service = ChatService()
        result = chat_service.send_message(content, conversation_id, image_data)
        
        if 'error' in result:
            return jsonify(result), 500
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/conversations', methods=['GET'])
def get_conversations():
    try:
        chat_service = ChatService()
        conversations = chat_service.get_user_conversations()
        
        conversation_data = []
        for conv in conversations:
            conversation_data.append({
                'id': conv.id,
                'title': conv.title,
                'message_count': len(conv.messages),
                'updated_at': conv.updated_at.isoformat() if conv.updated_at else conv.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'conversations': conversation_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/conversations', methods=['POST'])
def create_conversation():
    try:
        chat_service = ChatService()
        conversation = chat_service.get_or_create_conversation()
        
        return jsonify(conversation.to_dict())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/conversations/<int:conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    try:
        chat_service = ChatService()
        success = chat_service.delete_conversation(conversation_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Conversation deleted'})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/conversations/<int:conversation_id>/title', methods=['PUT'])
def update_conversation_title(conversation_id):
    try:
        data = request.get_json()
        new_title = data.get('title', '').strip()
        
        if not new_title:
            return jsonify({'error': 'Title is required'}), 400
        
        chat_service = ChatService()
        success = chat_service.update_conversation_title(conversation_id, new_title)
        
        if success:
            return jsonify({'success': True, 'message': 'Title updated'})
        else:
            return jsonify({'error': 'Conversation not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat/conversations/<int:conversation_id>/messages', methods=['GET'])
def get_conversation_messages(conversation_id):
    try:
        if 'user_session' not in session:
            return jsonify({'error': 'No active session'}), 401
        
        user_session = session['user_session']
        conversation = Conversation.query.filter_by(
            id=conversation_id,
            user_session=user_session
        ).first()
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        messages = Message.query.filter_by(
            conversation_id=conversation_id
        ).order_by(Message.timestamp.asc()).all()
        
        return jsonify([msg.to_dict() for msg in messages])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Assessment API routes
@api_bp.route('/assessments/generate/<concept>', methods=['POST'])
def generate_assessment(concept):
    """Generate assessment for a specific OOP concept"""
    try:
        data = request.get_json() if request.is_json else {}
        difficulty = data.get('difficulty', 'medium')
        question_count = data.get('question_count', 5)
        
        # Validate concept
        valid_concepts = ['encapsulation', 'inheritance', 'polymorphism', 'abstraction']
        if concept not in valid_concepts:
            return jsonify({'error': 'Invalid concept'}), 400
        
        assessment_service = AssessmentService()
        assessment_data = assessment_service.generate_assessment(concept, difficulty, question_count)
        
        return jsonify(assessment_data)
        
    except Exception as e:
        current_app.logger.error(f"Error generating assessment: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/assessments/evaluate', methods=['POST'])
def evaluate_assessment():
    """Evaluate assessment answers"""
    try:
        data = request.get_json()
        assessment_id = data.get('assessment_id')
        user_answers = data.get('answers', {})
        
        # Generate user session if not exists
        if 'user_session' not in session:
            session['user_session'] = str(uuid.uuid4())
        
        assessment_service = AssessmentService()
        result = assessment_service.evaluate_assessment(
            assessment_id, user_answers, session['user_session']
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error evaluating assessment: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/assessments/<int:assessment_id>/submit', methods=['POST'])
def submit_assessment(assessment_id):
    """Submit assessment answers for evaluation"""
    try:
        data = request.get_json()
        user_answers = data.get('answers', {})
        
        # Generate user session if not exists
        if 'user_session' not in session:
            session['user_session'] = str(uuid.uuid4())
        
        assessment_service = AssessmentService()
        result = assessment_service.evaluate_assessment(
            assessment_id, user_answers, session['user_session']
        )
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error submitting assessment: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/assessments/results/<int:result_id>')
def get_assessment_result(result_id):
    """Get detailed assessment result"""
    try:
        result = AssessmentResult.query.get_or_404(result_id)
        return jsonify(result.to_dict())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/assessments/history')
def get_assessment_history():
    """Get user's assessment history"""
    try:
        if 'user_session' not in session:
            return jsonify([])
        
        concept = request.args.get('concept')  # Optional filter by concept
        
        assessment_service = AssessmentService()
        history = assessment_service.get_assessment_history(session['user_session'], concept)
        
        return jsonify(history)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/assessments/stats/<concept>')
def get_concept_stats(concept):
    """Get statistics for a specific concept"""
    try:
        if 'user_session' not in session:
            return jsonify({'average_score': 0, 'attempt_count': 0})
        
        # Get user's results for this concept
        results = db.session.query(AssessmentResult).join(Assessment).filter(
            Assessment.concept == concept,
            AssessmentResult.user_session == session['user_session']
        ).all()
        
        if not results:
            return jsonify({'average_score': 0, 'attempt_count': 0})
        
        avg_score = sum(r.score_percentage for r in results) / len(results)
        
        return jsonify({
            'average_score': round(avg_score, 2),
            'attempt_count': len(results),
            'best_score': max(r.score_percentage for r in results),
            'latest_score': results[-1].score_percentage if results else 0
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
