import google.generativeai as genai
from flask import session, current_app
from app.models import Conversation, Message, InteractiveLearningSession, db
import uuid
import os
import json
import random
from datetime import datetime

class ChatService:
    def __init__(self):
        """Initialize ChatService with Google Gemini AI"""
        try:
            # Configure Google Gemini AI
            api_key = os.environ.get('GOOGLE_API_KEY')
            if api_key:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
            else:
                current_app.logger.warning("GOOGLE_API_KEY not found. AI features disabled.")
                self.model = None
        except Exception as e:
            current_app.logger.error(f"Error initializing Gemini AI: {str(e)}")
            self.model = None

    def get_or_create_conversation(self, conversation_id=None):
        """Get existing conversation or create new one"""
        try:
            # Get current user from session
            from app.auth import get_current_user
            current_user = get_current_user()
            
            if not current_user:
                raise ValueError("User not authenticated")
            
            user_id = current_user.id
            
            if conversation_id:
                # Try to get existing conversation
                conversation = Conversation.query.filter_by(
                    id=conversation_id,
                    user_id=user_id
                ).first()
                
                if conversation:
                    return conversation
            
            # Create new conversation
            conversation = Conversation(
                title=f"Chat {datetime.now().strftime('%b %d, %Y %I:%M %p')}",
                user_id=user_id
            )
            
            db.session.add(conversation)
            db.session.commit()
            
            return conversation
            
        except Exception as e:
            current_app.logger.error(f"Error getting/creating conversation: {str(e)}")
            db.session.rollback()
            return None

    def get_user_conversations(self):
        """Get all conversations for current user"""
        try:
            from app.auth import get_current_user
            current_user = get_current_user()
            
            if not current_user:
                return []
            
            conversations = Conversation.query.filter_by(
                user_id=current_user.id
            ).order_by(Conversation.updated_at.desc()).all()
            
            return conversations
            
        except Exception as e:
            current_app.logger.error(f"Error getting user conversations: {str(e)}")
            return []

    def send_message(self, content, conversation_id=None, image_data=None):
        """Send message and get AI response with interactive learning"""
        try:
            # Get or create conversation
            conversation = self.get_or_create_conversation(conversation_id)
            if not conversation:
                return {'error': 'Could not create conversation'}
            
            # Save user message
            user_message = Message(
                conversation_id=conversation.id,
                content=content,
                is_user=True,
                image_url=image_data,
                message_type='text'
            )
            db.session.add(user_message)
            
            # Generate AI response with interactive elements
            ai_response_data = self._generate_interactive_response(content, conversation.id, image_data)
            
            # Save AI message
            ai_message = Message(
                conversation_id=conversation.id,
                content=ai_response_data['content'],
                is_user=False,
                message_type=ai_response_data.get('message_type', 'text'),
                interactive_data=ai_response_data.get('interactive_data')
            )
            db.session.add(ai_message)
            
            # Create interactive learning session if applicable
            learning_session = None
            if ai_response_data.get('message_type') in ['mcq', 'true_false']:
                learning_session = InteractiveLearningSession(
                    conversation_id=conversation.id,
                    message_id=ai_message.id,
                    question_type=ai_response_data['message_type'],
                    question_data=ai_response_data['interactive_data']
                )
                db.session.add(learning_session)
            
            # Update conversation timestamp and title if it's the first message
            conversation.updated_at = datetime.utcnow()
            if len(conversation.messages) == 0:
                # Generate a title from the first message
                title = self._generate_conversation_title(content)
                conversation.title = title
            
            db.session.commit()
            
            response = {
                'user_message': user_message.to_dict(),
                'ai_message': ai_message.to_dict(),
                'conversation': conversation.to_dict()
            }
            
            if learning_session:
                response['learning_session'] = learning_session.to_dict()
            
            return response
            
        except Exception as e:
            current_app.logger.error(f"Error sending message: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}

    def answer_interactive_question(self, session_id, user_answer):
        """Process user's answer to an interactive question"""
        try:
            learning_session = InteractiveLearningSession.query.get(session_id)
            if not learning_session:
                return {'error': 'Learning session not found'}
            
            if learning_session.answered_at:
                return {'error': 'Question already answered'}
            
            # Check if answer is correct
            question_data = learning_session.question_data
            correct_answer = question_data.get('correct_answer')
            is_correct = str(user_answer).lower() == str(correct_answer).lower()
            
            # Generate explanation
            explanation = self._generate_answer_explanation(
                question_data, user_answer, is_correct
            )
            
            # Update learning session
            learning_session.user_answer = user_answer
            learning_session.is_correct = is_correct
            learning_session.explanation = explanation
            learning_session.answered_at = datetime.utcnow()
            
            # Create explanation message
            explanation_message = Message(
                conversation_id=learning_session.conversation_id,
                content=explanation,
                is_user=False,
                message_type='explanation'
            )
            db.session.add(explanation_message)
            
            # Update conversation timestamp
            conversation = learning_session.conversation
            conversation.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'is_correct': is_correct,
                'explanation': explanation,
                'explanation_message': explanation_message.to_dict(),
                'learning_session': learning_session.to_dict()
            }
            
        except Exception as e:
            current_app.logger.error(f"Error answering interactive question: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}

    def _generate_interactive_response(self, content, conversation_id, image_data=None):
        """Generate AI response with potential interactive elements"""
        try:
            if not self.model:
                return {
                    'content': "I'm sorry, but AI responses are currently unavailable. Please check the API configuration.",
                    'message_type': 'text'
                }
            
            # Get conversation context
            context = self._get_conversation_context(conversation_id)
            
            # Check if we should include interactive elements
            should_include_interactive = self._should_include_interactive(content, context)
            
            if should_include_interactive:
                return self._generate_interactive_learning_response(content, context)
            else:
                return self._generate_standard_response(content, context)
            
        except Exception as e:
            current_app.logger.error(f"Error generating interactive response: {str(e)}")
            return {
                'content': "I apologize, but I'm having trouble responding right now. Please try again in a moment.",
                'message_type': 'text'
            }

    def _should_include_interactive(self, content, context):
        """Determine if response should include interactive elements"""
        # Include interactive elements if:
        # 1. User is asking about OOP concepts
        # 2. We haven't had an interactive element in the last few messages
        # 3. Random chance to keep engagement
        
        oop_keywords = [
            'class', 'object', 'inheritance', 'polymorphism', 'encapsulation', 
            'abstraction', 'constructor', 'method', 'override', 'interface',
            'what is', 'explain', 'how does', 'difference between'
        ]
        
        content_lower = content.lower()
        has_oop_keywords = any(keyword in content_lower for keyword in oop_keywords)
        
        # Check recent messages for interactive elements
        recent_messages = context.split('\n')[-6:]  # Last 6 messages
        has_recent_interactive = any('MCQ:' in msg or 'True/False:' in msg for msg in recent_messages)
        
        # Include interactive if asking about OOP and no recent interactive elements
        return has_oop_keywords and not has_recent_interactive and random.random() < 0.7

    def _generate_interactive_learning_response(self, content, context):
        """Generate response with interactive learning elements"""
        try:
            # Decide between MCQ and True/False
            question_type = random.choice(['mcq', 'true_false'])
            
            if question_type == 'mcq':
                return self._generate_mcq_response(content, context)
            else:
                return self._generate_true_false_response(content, context)
                
        except Exception as e:
            current_app.logger.error(f"Error generating interactive learning response: {str(e)}")
            return self._generate_standard_response(content, context)

    def _generate_mcq_response(self, content, context):
        """Generate MCQ-style response"""
        prompt = f"""You are an expert OOP tutor. Based on the user's question: "{content}", provide a helpful response followed by a multiple choice question to test understanding.

        Format your response as follows:
        1. First, provide a clear explanation of the concept
        2. Then add "INTERACTIVE_MCQ:" followed by a JSON object with this structure:
        {{
            "question": "Your question here",
            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
            "correct_answer": "A",
            "topic": "relevant OOP topic"
        }}

        Context: {context}
        User question: {content}
        """
        
        response = self.model.generate_content(prompt)
        response_text = response.text if response else "Error generating response"
        
        # Parse interactive element
        if "INTERACTIVE_MCQ:" in response_text:
            parts = response_text.split("INTERACTIVE_MCQ:")
            explanation = parts[0].strip()
            
            try:
                mcq_data = json.loads(parts[1].strip())
                return {
                    'content': explanation,
                    'message_type': 'mcq',
                    'interactive_data': mcq_data
                }
            except json.JSONDecodeError:
                pass
        
        return {
            'content': response_text,
            'message_type': 'text'
        }

    def _generate_true_false_response(self, content, context):
        """Generate True/False style response"""
        prompt = f"""You are an expert OOP tutor. Based on the user's question: "{content}", provide a helpful response followed by a true/false question to test understanding.

        Format your response as follows:
        1. First, provide a clear explanation of the concept
        2. Then add "INTERACTIVE_TF:" followed by a JSON object with this structure:
        {{
            "question": "True or False: Your statement here",
            "correct_answer": "true",
            "topic": "relevant OOP topic"
        }}

        Context: {context}
        User question: {content}
        """
        
        response = self.model.generate_content(prompt)
        response_text = response.text if response else "Error generating response"
        
        # Parse interactive element
        if "INTERACTIVE_TF:" in response_text:
            parts = response_text.split("INTERACTIVE_TF:")
            explanation = parts[0].strip()
            
            try:
                tf_data = json.loads(parts[1].strip())
                return {
                    'content': explanation,
                    'message_type': 'true_false',
                    'interactive_data': tf_data
                }
            except json.JSONDecodeError:
                pass
        
        return {
            'content': response_text,
            'message_type': 'text'
        }

    def _generate_standard_response(self, content, context):
        """Generate standard text response"""
        # Prepare prompt with OOP learning context
        system_prompt = """You are an expert Object-Oriented Programming (OOP) tutor and coding assistant. 
        You specialize in teaching concepts like inheritance, polymorphism, encapsulation, and abstraction.
        
        Your responses should be:
        - Educational and encouraging
        - Include practical examples when relevant
        - Use clear, beginner-friendly explanations
        - Provide code examples in multiple languages when helpful
        - Connect concepts to real-world applications
        - Include helpful suggestions for further learning
        
        Always be helpful, patient, and supportive of the learning journey."""
        
        # Build the full prompt
        full_prompt = f"{system_prompt}\n\nConversation context:\n{context}\n\nUser message: {content}"
        
        response = self.model.generate_content(full_prompt)
        
        return {
            'content': response.text if response else "I'm sorry, I couldn't generate a response. Please try again.",
            'message_type': 'text'
        }

    def _generate_answer_explanation(self, question_data, user_answer, is_correct):
        """Generate explanation for user's answer"""
        try:
            if not self.model:
                if is_correct:
                    return "✅ Correct! Well done."
                else:
                    return f"❌ Incorrect. The correct answer is {question_data.get('correct_answer')}."
            
            prompt = f"""As an OOP tutor, provide a detailed explanation for this question and answer:

            Question: {question_data.get('question')}
            Topic: {question_data.get('topic')}
            User's Answer: {user_answer}
            Correct Answer: {question_data.get('correct_answer')}
            Is Correct: {is_correct}

            Provide:
            1. Whether the answer is correct or incorrect (use ✅ or ❌)
            2. A clear explanation of why it's correct/incorrect
            3. Additional context to help understand the concept
            4. A suggestion for further learning if incorrect

            Keep it encouraging and educational.
            """
            
            response = self.model.generate_content(prompt)
            return response.text if response else (
                "✅ Correct! Well done." if is_correct else 
                f"❌ Incorrect. The correct answer is {question_data.get('correct_answer')}."
            )
            
        except Exception as e:
            current_app.logger.error(f"Error generating explanation: {str(e)}")
            return "✅ Correct!" if is_correct else "❌ Incorrect. Please try again."

    def _get_conversation_context(self, conversation_id, max_messages=10):
        """Get recent conversation context"""
        try:
            messages = Message.query.filter_by(
                conversation_id=conversation_id
            ).order_by(Message.timestamp.desc()).limit(max_messages).all()
            
            context = []
            for message in reversed(messages):
                role = "User" if message.is_user else "Assistant"
                context.append(f"{role}: {message.content}")
            
            return "\n".join(context)
            
        except Exception as e:
            current_app.logger.error(f"Error getting conversation context: {str(e)}")
            return ""

    def _generate_conversation_title(self, first_message):
        """Generate a conversation title from the first message"""
        try:
            if not self.model:
                return f"Chat - {datetime.now().strftime('%b %d')}"
            
            prompt = f"""Generate a short, descriptive title (max 4-5 words) for a conversation that starts with this message: "{first_message[:100]}"
            
            The title should be concise and capture the main topic. Don't use quotes in the title.
            Examples: "OOP Inheritance Help", "Python Classes Question", "Polymorphism Examples"
            
            Title:"""
            
            response = self.model.generate_content(prompt)
            title = response.text.strip().replace('"', '').replace("'", "")
            
            # Ensure title is reasonable length
            if len(title) > 50:
                title = title[:47] + "..."
            
            return title if title else f"Chat - {datetime.now().strftime('%b %d')}"
            
        except Exception as e:
            current_app.logger.error(f"Error generating title: {str(e)}")
            return f"Chat - {datetime.now().strftime('%b %d')}"

    def delete_conversation(self, conversation_id):
        """Delete a conversation"""
        try:
            if 'user_session' not in session:
                return False
            
            user_session = session['user_session']
            conversation = Conversation.query.filter_by(
                id=conversation_id,
                user_session=user_session
            ).first()
            
            if conversation:
                db.session.delete(conversation)
                db.session.commit()
                return True
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error deleting conversation: {str(e)}")
            db.session.rollback()
            return False

    def update_conversation_title(self, conversation_id, new_title):
        """Update conversation title"""
        try:
            if 'user_session' not in session:
                return False
            
            user_session = session['user_session']
            conversation = Conversation.query.filter_by(
                id=conversation_id,
                user_session=user_session
            ).first()
            
            if conversation:
                conversation.title = new_title
                conversation.updated_at = datetime.utcnow()
                db.session.commit()
                return True
            
            return False
            
        except Exception as e:
            current_app.logger.error(f"Error updating conversation title: {str(e)}")
            db.session.rollback()
            return False
