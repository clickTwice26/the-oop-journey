import google.generativeai as genai
from flask import session, current_app
from app.models import Conversation, Message, db
import uuid
import os
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
        """Send message and get AI response"""
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
                image_url=image_data
            )
            db.session.add(user_message)
            
            # Generate AI response
            ai_response = self._generate_ai_response(content, conversation.id, image_data)
            
            # Save AI message
            ai_message = Message(
                conversation_id=conversation.id,
                content=ai_response,
                is_user=False
            )
            db.session.add(ai_message)
            
            # Update conversation timestamp and title if it's the first message
            conversation.updated_at = datetime.utcnow()
            if len(conversation.messages) == 0:
                # Generate a title from the first message
                title = self._generate_conversation_title(content)
                conversation.title = title
            
            db.session.commit()
            
            return {
                'user_message': user_message.to_dict(),
                'ai_message': ai_message.to_dict(),
                'conversation': conversation.to_dict()
            }
            
        except Exception as e:
            current_app.logger.error(f"Error sending message: {str(e)}")
            db.session.rollback()
            return {'error': str(e)}

    def _generate_ai_response(self, content, conversation_id, image_data=None):
        """Generate AI response using Gemini"""
        try:
            if not self.model:
                return "I'm sorry, but AI responses are currently unavailable. Please check the API configuration."
            
            # Get conversation context
            context = self._get_conversation_context(conversation_id)
            
            # Prepare prompt with OOP learning context
            system_prompt = """You are an expert Object-Oriented Programming (OOP) tutor and coding assistant. 
            You specialize in teaching concepts like inheritance, polymorphism, encapsulation, and abstraction.
            
            Your responses should be:
            - Educational and encouraging
            - Include practical examples when relevant
            - Use clear, beginner-friendly explanations
            - Provide code examples in multiple languages when helpful
            - Connect concepts to real-world applications
            
            Always be helpful, patient, and supportive of the learning journey."""
            
            # Build the full prompt
            full_prompt = f"{system_prompt}\n\nConversation context:\n{context}\n\nUser message: {content}"
            
            if image_data:
                # Handle image input (for future implementation)
                response = self.model.generate_content([full_prompt])
            else:
                response = self.model.generate_content(full_prompt)
            
            return response.text if response else "I'm sorry, I couldn't generate a response. Please try again."
            
        except Exception as e:
            current_app.logger.error(f"Error generating AI response: {str(e)}")
            return "I apologize, but I'm having trouble responding right now. Please try again in a moment."

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
