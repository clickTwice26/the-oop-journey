import google.generativeai as genai
from flask import current_app
from app.models import Assessment, AssessmentResult, db
import json
import os
from datetime import datetime

class AssessmentService:
    def __init__(self):
        """Initialize AssessmentService with Google Gemini AI"""
        try:
            api_key = os.environ.get('GOOGLE_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            else:
                current_app.logger.warning("GOOGLE_API_KEY not found. AI assessment features disabled.")
                self.model = None
        except Exception as e:
            current_app.logger.error(f"Error initializing Gemini AI for assessments: {str(e)}")
            self.model = None

    def generate_assessment(self, concept, difficulty='medium', question_count=5):
        """Generate assessment questions for a specific OOP concept"""
        try:
            if not self.model:
                return self._get_fallback_assessment(concept, difficulty, question_count)
            
            # Define prompts for different concepts
            concept_prompts = {
                'encapsulation': {
                    'description': 'data hiding, private/public access modifiers, getters/setters, information hiding principles',
                    'focus': 'access control, data security, interface design'
                },
                'inheritance': {
                    'description': 'class hierarchies, parent-child relationships, method overriding, super keyword',
                    'focus': 'code reuse, hierarchical relationships, method inheritance'
                },
                'polymorphism': {
                    'description': 'method overloading, method overriding, runtime vs compile-time polymorphism, interfaces',
                    'focus': 'flexibility, dynamic behavior, interface implementation'
                },
                'abstraction': {
                    'description': 'abstract classes, interfaces, hiding implementation details, essential features',
                    'focus': 'simplification, essential vs non-essential features, interface design'
                }
            }
            
            concept_info = concept_prompts.get(concept, concept_prompts['encapsulation'])
            
            # Create assessment generation prompt
            prompt = f"""Generate a {difficulty} difficulty assessment for the Object-Oriented Programming concept: {concept.upper()}

Concept Focus: {concept_info['description']}
Key Areas: {concept_info['focus']}
Difficulty: {difficulty}
Number of questions: {question_count}

Requirements:
1. Create exactly {question_count} multiple-choice questions
2. Each question should have 4 options (A, B, C, D)
3. Include clear explanations for correct answers
4. Questions should test both theoretical understanding and practical application
5. Include code examples where relevant
6. Vary question types: definition, application, code analysis, scenario-based

For {difficulty} difficulty:
- Easy: Basic definitions and simple concepts
- Medium: Application scenarios and moderate code analysis
- Hard: Complex scenarios, edge cases, and advanced implementations

Return the response in this exact JSON format:
{{
    "concept": "{concept}",
    "difficulty": "{difficulty}",
    "total_questions": {question_count},
    "questions": [
        {{
            "id": 1,
            "question": "Question text here",
            "options": {{
                "A": "Option A text",
                "B": "Option B text", 
                "C": "Option C text",
                "D": "Option D text"
            }},
            "correct_answer": "A",
            "explanation": "Detailed explanation of why this answer is correct",
            "category": "theory|application|code_analysis|scenario"
        }}
    ]
}}

Generate the assessment now:"""

            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                return self._get_fallback_assessment(concept, difficulty, question_count)
            
            # Try to parse JSON response
            try:
                # Clean the response text - remove markdown formatting if present
                response_text = response.text.strip()
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                assessment_data = json.loads(response_text.strip())
                
                # Validate the response structure
                if not self._validate_assessment_data(assessment_data):
                    current_app.logger.warning("Invalid assessment data structure, using fallback")
                    return self._get_fallback_assessment(concept, difficulty, question_count)
                
                # Save to database
                assessment = Assessment(
                    concept=concept,
                    difficulty=difficulty,
                    questions=assessment_data['questions'],
                    assessment_metadata={
                        'generated_at': datetime.utcnow().isoformat(),
                        'total_questions': len(assessment_data['questions']),
                        'ai_generated': True
                    }
                )
                
                db.session.add(assessment)
                db.session.commit()
                
                # Return the assessment with ID
                result = assessment_data.copy()
                result['id'] = assessment.id
                return result
                
            except json.JSONDecodeError as e:
                current_app.logger.error(f"JSON parsing error: {str(e)}")
                return self._get_fallback_assessment(concept, difficulty, question_count)
            
        except Exception as e:
            current_app.logger.error(f"Error generating assessment: {str(e)}")
            return self._get_fallback_assessment(concept, difficulty, question_count)

    def _validate_assessment_data(self, data):
        """Validate assessment data structure"""
        try:
            required_fields = ['concept', 'difficulty', 'questions']
            for field in required_fields:
                if field not in data:
                    return False
            
            if not isinstance(data['questions'], list) or len(data['questions']) == 0:
                return False
            
            for question in data['questions']:
                required_q_fields = ['question', 'options', 'correct_answer', 'explanation']
                for field in required_q_fields:
                    if field not in question:
                        return False
                
                if not isinstance(question['options'], dict):
                    return False
                
                required_options = ['A', 'B', 'C', 'D']
                for option in required_options:
                    if option not in question['options']:
                        return False
                
                if question['correct_answer'] not in required_options:
                    return False
            
            return True
            
        except Exception:
            return False

    def _get_fallback_assessment(self, concept, difficulty, question_count):
        """Generate fallback assessment when AI is unavailable"""
        
        fallback_questions = {
            'encapsulation': [
                {
                    "id": 1,
                    "question": "What is encapsulation in Object-Oriented Programming?",
                    "options": {
                        "A": "A way to hide data and methods within a class",
                        "B": "A method to create multiple classes",
                        "C": "A technique for inheritance",
                        "D": "A way to implement polymorphism"
                    },
                    "correct_answer": "A",
                    "explanation": "Encapsulation is the principle of hiding internal data and methods of a class, exposing only what is necessary through public interfaces.",
                    "category": "theory"
                },
                {
                    "id": 2,
                    "question": "Which access modifier provides the highest level of encapsulation?",
                    "options": {
                        "A": "public",
                        "B": "protected", 
                        "C": "private",
                        "D": "default"
                    },
                    "correct_answer": "C",
                    "explanation": "Private access modifier provides the highest level of encapsulation as it restricts access to the member only within the same class.",
                    "category": "application"
                }
            ],
            'inheritance': [
                {
                    "id": 1,
                    "question": "What is inheritance in OOP?",
                    "options": {
                        "A": "A mechanism where a class acquires properties of another class",
                        "B": "A way to hide data",
                        "C": "A method overloading technique",
                        "D": "A way to create interfaces"
                    },
                    "correct_answer": "A",
                    "explanation": "Inheritance is a fundamental OOP concept where a class (child/derived) inherits properties and methods from another class (parent/base).",
                    "category": "theory"
                },
                {
                    "id": 2,
                    "question": "Which keyword is used to inherit from a parent class in Java?",
                    "options": {
                        "A": "inherits",
                        "B": "extends",
                        "C": "implements",
                        "D": "derives"
                    },
                    "correct_answer": "B",
                    "explanation": "In Java, the 'extends' keyword is used to inherit from a parent class, establishing an inheritance relationship.",
                    "category": "application"
                }
            ],
            'polymorphism': [
                {
                    "id": 1,
                    "question": "What is polymorphism in OOP?",
                    "options": {
                        "A": "Having multiple forms or behaviors",
                        "B": "Creating multiple classes",
                        "C": "Hiding implementation details",
                        "D": "Inheriting from multiple classes"
                    },
                    "correct_answer": "A",
                    "explanation": "Polymorphism allows objects of different types to be treated as instances of the same type, enabling multiple forms or behaviors.",
                    "category": "theory"
                },
                {
                    "id": 2,
                    "question": "What is method overriding?",
                    "options": {
                        "A": "Creating multiple methods with same name but different parameters",
                        "B": "Providing a specific implementation for a method in a subclass",
                        "C": "Hiding a method from the parent class",
                        "D": "Creating abstract methods"
                    },
                    "correct_answer": "B",
                    "explanation": "Method overriding occurs when a subclass provides a specific implementation for a method that is already defined in its parent class.",
                    "category": "application"
                }
            ],
            'abstraction': [
                {
                    "id": 1,
                    "question": "What is abstraction in OOP?",
                    "options": {
                        "A": "Hiding complex implementation details and showing only essential features",
                        "B": "Creating multiple instances of a class",
                        "C": "Inheriting from a parent class",
                        "D": "Overloading methods"
                    },
                    "correct_answer": "A",
                    "explanation": "Abstraction is the principle of hiding complex implementation details while exposing only the essential features and functionality.",
                    "category": "theory"
                },
                {
                    "id": 2,
                    "question": "Which of these is an example of abstraction?",
                    "options": {
                        "A": "Using a car without knowing how the engine works",
                        "B": "Creating a new car model",
                        "C": "Painting a car",
                        "D": "Buying a car"
                    },
                    "correct_answer": "A",
                    "explanation": "Abstraction is like using a car interface (steering wheel, pedals) without needing to understand the complex engine mechanics underneath.",
                    "category": "scenario"
                }
            ]
        }
        
        # Get questions for the concept
        concept_questions = fallback_questions.get(concept, fallback_questions['encapsulation'])
        
        # Limit to requested question count
        selected_questions = concept_questions[:question_count]
        
        # Add more questions if needed (repeat with variations)
        while len(selected_questions) < question_count:
            base_question = concept_questions[len(selected_questions) % len(concept_questions)]
            new_question = base_question.copy()
            new_question['id'] = len(selected_questions) + 1
            selected_questions.append(new_question)
        
        # Save to database
        try:
            assessment = Assessment(
                concept=concept,
                difficulty=difficulty,
                questions=selected_questions,
                assessment_metadata={
                    'generated_at': datetime.utcnow().isoformat(),
                    'total_questions': len(selected_questions),
                    'ai_generated': False,
                    'fallback': True
                }
            )
            
            db.session.add(assessment)
            db.session.commit()
            
            return {
                'id': assessment.id,
                'concept': concept,
                'difficulty': difficulty,
                'total_questions': len(selected_questions),
                'questions': selected_questions
            }
            
        except Exception as e:
            current_app.logger.error(f"Error saving fallback assessment: {str(e)}")
            db.session.rollback()
            
            # Return without saving if database error
            return {
                'id': None,
                'concept': concept,
                'difficulty': difficulty,
                'total_questions': len(selected_questions),
                'questions': selected_questions
            }

    def evaluate_assessment(self, assessment_id, user_answers, user_session):
        """Evaluate user's assessment answers"""
        try:
            # Get the assessment
            assessment = Assessment.query.get(assessment_id)
            if not assessment:
                return {'error': 'Assessment not found'}
            
            questions = assessment.questions
            total_questions = len(questions)
            correct_count = 0
            detailed_results = []
            
            # Evaluate each answer
            for i, question in enumerate(questions):
                question_id = str(question.get('id', i + 1))
                user_answer = user_answers.get(question_id)
                correct_answer = question['correct_answer']
                
                is_correct = user_answer == correct_answer
                if is_correct:
                    correct_count += 1
                
                detailed_results.append({
                    'question_id': question_id,
                    'question': question['question'],
                    'user_answer': user_answer,
                    'correct_answer': correct_answer,
                    'is_correct': is_correct,
                    'explanation': question.get('explanation', ''),
                    'options': question['options']
                })
            
            # Calculate score
            score_percentage = (correct_count / total_questions) * 100
            
            # Generate AI feedback
            ai_feedback = self._generate_ai_feedback(assessment.concept, score_percentage, detailed_results)
            
            # Save result to database
            result = AssessmentResult(
                assessment_id=assessment_id,
                user_session=user_session,
                score_percentage=score_percentage,
                user_answers=user_answers,
                ai_feedback=ai_feedback
            )
            
            db.session.add(result)
            db.session.commit()
            
            return {
                'result_id': result.id,
                'score_percentage': score_percentage,
                'correct_answers': correct_count,
                'total_questions': total_questions,
                'detailed_results': detailed_results,
                'ai_feedback': ai_feedback,
                'concept': assessment.concept,
                'difficulty': assessment.difficulty
            }
            
        except Exception as e:
            current_app.logger.error(f"Error evaluating assessment: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}

    def _generate_ai_feedback(self, concept, score_percentage, detailed_results):
        """Generate personalized AI feedback"""
        try:
            if not self.model:
                return self._get_fallback_feedback(concept, score_percentage)
            
            # Analyze performance
            incorrect_answers = [r for r in detailed_results if not r['is_correct']]
            correct_answers = [r for r in detailed_results if r['is_correct']]
            
            # Build feedback prompt
            prompt = f"""Generate personalized feedback for a student who just completed an assessment on {concept.upper()}.

Assessment Results:
- Score: {score_percentage:.1f}%
- Correct: {len(correct_answers)}/{len(detailed_results)} questions
- Concept: {concept}

Incorrect Answers Analysis:
{self._format_incorrect_answers(incorrect_answers)}

Provide feedback that includes:
1. Overall performance assessment
2. Specific areas that need improvement (based on incorrect answers)
3. Encouraging words and positive reinforcement
4. 2-3 specific study recommendations
5. Next steps for learning

Keep the tone encouraging, constructive, and educational. Limit to 200-300 words.

Format as JSON:
{{
    "overall_assessment": "Brief overall performance summary",
    "strengths": ["strength1", "strength2"],
    "areas_for_improvement": ["area1", "area2"],
    "study_recommendations": ["recommendation1", "recommendation2", "recommendation3"],
    "encouragement": "Encouraging message for continued learning",
    "next_steps": "Suggested next learning steps"
}}"""

            response = self.model.generate_content(prompt)
            
            if response and response.text:
                try:
                    # Clean and parse JSON
                    response_text = response.text.strip()
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]
                    
                    feedback = json.loads(response_text.strip())
                    return feedback
                except json.JSONDecodeError:
                    current_app.logger.warning("Could not parse AI feedback JSON, using fallback")
                    return self._get_fallback_feedback(concept, score_percentage)
            
            return self._get_fallback_feedback(concept, score_percentage)
            
        except Exception as e:
            current_app.logger.error(f"Error generating AI feedback: {str(e)}")
            return self._get_fallback_feedback(concept, score_percentage)

    def _format_incorrect_answers(self, incorrect_answers):
        """Format incorrect answers for AI analysis"""
        if not incorrect_answers:
            return "All answers were correct!"
        
        formatted = []
        for answer in incorrect_answers[:3]:  # Limit to first 3 for prompt size
            formatted.append(f"Q: {answer['question'][:100]}... | User answered: {answer['user_answer']} | Correct: {answer['correct_answer']}")
        
        return "\n".join(formatted)

    def _get_fallback_feedback(self, concept, score_percentage):
        """Generate fallback feedback when AI is unavailable"""
        
        if score_percentage >= 90:
            performance = "Excellent"
            encouragement = "Outstanding work! You have mastered this concept."
        elif score_percentage >= 70:
            performance = "Good"
            encouragement = "Great job! You have a solid understanding with room for minor improvements."
        elif score_percentage >= 50:
            performance = "Fair"
            encouragement = "You're on the right track! Focus on the areas you missed and keep practicing."
        else:
            performance = "Needs Improvement"
            encouragement = "Don't be discouraged! This is a learning opportunity to strengthen your understanding."
        
        concept_tips = {
            'encapsulation': [
                "Review access modifiers (private, public, protected)",
                "Practice implementing getters and setters",
                "Study real-world examples of data hiding"
            ],
            'inheritance': [
                "Practice creating class hierarchies",
                "Study method overriding vs overloading",
                "Review the 'super' keyword usage"
            ],
            'polymorphism': [
                "Study runtime vs compile-time polymorphism",
                "Practice method overriding and interfaces",
                "Review abstract classes and methods"
            ],
            'abstraction': [
                "Study abstract classes vs interfaces",
                "Practice identifying essential vs non-essential features",
                "Review real-world abstraction examples"
            ]
        }
        
        return {
            "overall_assessment": f"{performance} performance with {score_percentage:.1f}% score",
            "strengths": ["Attempted all questions", "Shows understanding of basic concepts"],
            "areas_for_improvement": ["Review incorrect answers", f"Focus on {concept} fundamentals"],
            "study_recommendations": concept_tips.get(concept, concept_tips['encapsulation']),
            "encouragement": encouragement,
            "next_steps": f"Continue practicing {concept} concepts and take the assessment again to track improvement"
        }

    def get_assessment_history(self, user_session, concept=None):
        """Get user's assessment history"""
        try:
            query = db.session.query(AssessmentResult).join(Assessment)
            query = query.filter(AssessmentResult.user_session == user_session)
            
            if concept:
                query = query.filter(Assessment.concept == concept)
            
            results = query.order_by(AssessmentResult.completed_at.desc()).all()
            
            history = []
            for result in results:
                history.append({
                    'id': result.id,
                    'assessment_id': result.assessment_id,
                    'concept': result.assessment.concept,
                    'difficulty': result.assessment.difficulty,
                    'score_percentage': result.score_percentage,
                    'completed_at': result.completed_at.isoformat(),
                    'ai_feedback': result.ai_feedback
                })
            
            return history
            
        except Exception as e:
            current_app.logger.error(f"Error getting assessment history: {str(e)}")
            return []
