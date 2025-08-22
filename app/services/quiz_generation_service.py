import google.generativeai as genai
import json
import os
from app.services.file_processing_service import FileProcessingService
import re

class QuizGenerationService:
    """Service for generating quizzes using Google's Gemini AI"""
    
    def __init__(self):
        self.api_key = os.environ.get('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        genai.configure(api_key=self.api_key)
        # Use the flash model which is more reliable for text generation
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_quiz_from_file(self, file_path, title, num_questions=10):
        """Generate quiz from uploaded file"""
        try:
            print(f"Starting quiz generation for file: {file_path}")
            
            # Extract text from file
            text_content = FileProcessingService.extract_text_from_file(file_path)
            print(f"Extracted text length: {len(text_content) if text_content else 0} characters")
            
            if not text_content or len(text_content.strip()) < 50:
                raise ValueError("File content is too short or empty to generate meaningful questions")
            
            print(f"Content preview: {text_content[:200]}...")
            
            # Generate quiz using AI
            quiz_data = self._generate_quiz_with_ai(text_content, title, num_questions)
            
            print(f"Quiz generation completed successfully: {quiz_data['title']}")
            return quiz_data
            
        except Exception as e:
            print(f"Error in generate_quiz_from_file: {str(e)}")
            raise Exception(f"Error generating quiz: {str(e)}")
    
    def _generate_quiz_with_ai(self, text_content, title, num_questions):
        """Use Gemini AI to generate quiz questions"""
        prompt = self._create_quiz_prompt(text_content, title, num_questions)
        
        try:
            response = self.model.generate_content(prompt)
            
            if not response or not response.text:
                raise ValueError("Empty response from AI model")
            
            print(f"AI Response: {response.text[:500]}...")  # Debug log
            
            quiz_json = self._extract_json_from_response(response.text)
            
            # Validate and clean the quiz data
            validated_quiz = self._validate_quiz_data(quiz_json, title, num_questions)
            
            return validated_quiz
            
        except Exception as e:
            print(f"AI Quiz Generation Error: {str(e)}")  # Debug log
            # Instead of fallback, try a simpler approach first
            return self._generate_simple_quiz_with_ai(text_content, title, num_questions)
    
    def _create_quiz_prompt(self, content, title, num_questions):
        """Create a detailed prompt for quiz generation"""
        # Limit content to avoid token limits but ensure we have enough context
        limited_content = content[:4000] if len(content) > 4000 else content
        
        return f"""You are an expert quiz creator. Based on the following content, create {num_questions} multiple-choice questions.

CONTENT TO ANALYZE:
{limited_content}

INSTRUCTIONS:
- Create exactly {num_questions} questions based ONLY on the content above
- Each question must have 4 answer options labeled A, B, C, D
- Provide the correct answer letter (A, B, C, or D)
- Include a brief explanation for the correct answer
- Questions should test understanding of the main concepts from the content
- Avoid generic questions - make them specific to the content provided

RESPONSE FORMAT (return ONLY valid JSON):
{{
    "title": "{title}",
    "description": "Quiz generated from uploaded content",
    "questions": [
        {{
            "question": "Specific question based on the content",
            "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
            "correct_answer": "A",
            "explanation": "Brief explanation of why this answer is correct"
        }}
    ]
}}

Generate the quiz now:"""
    
    def _generate_simple_quiz_with_ai(self, text_content, title, num_questions):
        """Simpler AI quiz generation with better error handling"""
        try:
            # Create a simpler, more direct prompt
            simple_prompt = f"""Create {num_questions} quiz questions from this content:

{text_content[:2000]}

Format each question like this:
Q1: [Question text]
A) [Option A]
B) [Option B] 
C) [Option C]
D) [Option D]
Correct: [A/B/C/D]
Explanation: [Brief explanation]

Generate {num_questions} questions now:"""

            response = self.model.generate_content(simple_prompt)
            
            if response and response.text:
                print(f"Simple AI Response: {response.text[:300]}...")  # Debug
                return self._parse_simple_format(response.text, title, num_questions)
            
        except Exception as e:
            print(f"Simple AI generation failed: {str(e)}")
        
        # Final fallback
        return self._generate_content_based_fallback(text_content, title, num_questions)
    
    def _parse_simple_format(self, response_text, title, num_questions):
        """Parse the simple format response"""
        questions = []
        lines = response_text.split('\n')
        
        current_question = {}
        options = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Q') and ':' in line:
                if current_question and 'question' in current_question:
                    questions.append(current_question)
                current_question = {'question': line.split(':', 1)[1].strip()}
                options = []
            elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                options.append(line[2:].strip())
            elif line.startswith('Correct:'):
                current_question['correct_answer'] = line.split(':', 1)[1].strip().upper()
            elif line.startswith('Explanation:'):
                current_question['explanation'] = line.split(':', 1)[1].strip()
                if len(options) == 4:
                    current_question['options'] = options
                    questions.append(current_question)
                    current_question = {}
                    options = []
        
        # Add the last question if it's complete
        if current_question and 'question' in current_question and len(options) == 4:
            current_question['options'] = options
            questions.append(current_question)
        
        # Clean and validate questions
        valid_questions = []
        for q in questions[:num_questions]:
            if self._is_valid_simple_question(q):
                valid_questions.append(q)
        
        if valid_questions:
            return {
                'title': title,
                'description': 'Quiz generated from uploaded content',
                'questions': valid_questions
            }
        else:
            raise ValueError("No valid questions parsed from AI response")
    
    def _is_valid_simple_question(self, question):
        """Validate a simple format question"""
        return (isinstance(question, dict) and 
                'question' in question and question['question'].strip() and
                'options' in question and len(question['options']) == 4 and
                'correct_answer' in question and question['correct_answer'] in ['A', 'B', 'C', 'D'])
    
    def _generate_content_based_fallback(self, text_content, title, num_questions):
        """Generate fallback questions based on actual content"""
        # Extract key phrases and topics from content
        words = text_content.lower().split()
        key_concepts = []
        
        # Simple keyword extraction (you could improve this with NLP)
        for word in words:
            if len(word) > 5 and word.isalpha() and word not in ['about', 'which', 'where', 'their', 'there', 'these', 'those']:
                key_concepts.append(word.title())
        
        # Remove duplicates and take first 10
        key_concepts = list(set(key_concepts))[:10]
        
        questions = []
        for i in range(min(num_questions, len(key_concepts))):
            concept = key_concepts[i] if i < len(key_concepts) else f"Topic {i+1}"
            
            questions.append({
                'question': f'According to the content, what is mentioned about {concept}?',
                'options': [
                    f'{concept} is a key concept discussed in the material',
                    f'{concept} is briefly mentioned but not explained',
                    f'{concept} is not related to the main topic',
                    f'{concept} is used as an example only'
                ],
                'correct_answer': 'A',
                'explanation': f'Based on the content analysis, {concept} appears to be an important concept in the material.'
            })
        
        # If we don't have enough concepts, add generic content-based questions
        while len(questions) < num_questions:
            i = len(questions) + 1
            questions.append({
                'question': f'Based on the uploaded content, which statement best describes the main theme?',
                'options': [
                    'The content discusses important concepts and principles',
                    'The content is primarily narrative in nature',
                    'The content focuses on historical events only',
                    'The content is purely theoretical without examples'
                ],
                'correct_answer': 'A',
                'explanation': 'The content appears to contain educational material with key concepts.'
            })
        
        return {
            'title': title,
            'description': 'Quiz generated from content analysis (AI processing unavailable)',
            'questions': questions[:num_questions]
        }
    
    def _extract_json_from_response(self, response_text):
        """Extract JSON from AI response with improved parsing"""
        try:
            # Remove markdown formatting if present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            
            # Try to parse the entire cleaned text as JSON
            return json.loads(cleaned_text)
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Response text (first 500 chars): {response_text[:500]}")
            raise ValueError(f"No valid JSON found in AI response: {str(e)}")
        except Exception as e:
            print(f"General parsing error: {str(e)}")
            raise ValueError(f"Error parsing AI response: {str(e)}")
    
    def _validate_quiz_data(self, quiz_data, title, num_questions):
        """Validate and clean quiz data"""
        if not isinstance(quiz_data, dict):
            raise ValueError("Quiz data must be a dictionary")
        
        # Ensure required fields
        quiz_data['title'] = quiz_data.get('title', title)
        quiz_data['description'] = quiz_data.get('description', 'Generated quiz')
        
        questions = quiz_data.get('questions', [])
        if not questions:
            raise ValueError("No questions found in quiz data")
        
        # Validate each question
        validated_questions = []
        for i, q in enumerate(questions[:num_questions]):  # Limit to requested number
            try:
                validated_q = self._validate_question(q, i+1)
                validated_questions.append(validated_q)
            except Exception as e:
                print(f"Skipping invalid question {i+1}: {e}")
                continue
        
        if not validated_questions:
            raise ValueError("No valid questions found")
        
        quiz_data['questions'] = validated_questions
        return quiz_data
    
    def _validate_question(self, question, question_num):
        """Validate individual question"""
        if not isinstance(question, dict):
            raise ValueError("Question must be a dictionary")
        
        # Ensure question text
        if 'question' not in question or not question['question'].strip():
            raise ValueError("Question text is required")
        
        # Ensure options
        options = question.get('options', [])
        if not options or len(options) != 4:
            raise ValueError("Exactly 4 options are required")
        
        # Ensure all options have content
        for i, option in enumerate(options):
            if not option or not str(option).strip():
                raise ValueError(f"Option {i+1} is empty")
        
        # Validate correct answer
        correct_answer = question.get('correct_answer', '').upper()
        if correct_answer not in ['A', 'B', 'C', 'D']:
            correct_answer = 'A'  # Default to A if invalid
        
        return {
            'question': question['question'].strip(),
            'options': [str(opt).strip() for opt in options],
            'correct_answer': correct_answer,
            'explanation': question.get('explanation', 'No explanation provided').strip()
        }
    
    def _generate_fallback_quiz(self, title, num_questions):
        """Generate a fallback quiz when AI fails"""
        questions = []
        for i in range(num_questions):  # Generate requested number of questions
            questions.append({
                'question': f'Sample question {i+1} about the uploaded content',
                'options': [
                    f'Option A for question {i+1}',
                    f'Option B for question {i+1}',
                    f'Option C for question {i+1}',
                    f'Option D for question {i+1}'
                ],
                'correct_answer': 'A',
                'explanation': 'This is a sample question generated as a fallback.'
            })
        
        return {
            'title': title,
            'description': 'Sample quiz generated (AI service unavailable)',
            'questions': questions
        }
