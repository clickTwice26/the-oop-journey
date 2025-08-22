# QuizPilot - AI-Powered Quiz Generation Platform

A modern web application built with Flask that transforms study materials into interactive quizzes using AI technology.

## Features

- **AI-Powered Quiz Generation**: Upload PDFs, images, presentations, or documents and let AI create personalized quizzes
- **Interactive Quiz Taking**: Clean, modern interface for taking quizzes with progress tracking
- **Quiz Review System**: Review answers with explanations and performance analytics
- **File Processing**: Support for multiple file formats (PDF, DOCX, PPTX, images, text)
- **Progress Tracking**: Monitor learning progress with detailed statistics
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Technology Stack

- **Backend**: Python Flask with SQLAlchemy
- **Frontend**: Jinja2 templates with Tailwind CSS
- **AI Integration**: Google Gemini API for quiz generation
- **Database**: SQLite (development) / PostgreSQL (production)
- **File Processing**: PyPDF2, python-docx, python-pptx, Pillow

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Clone or navigate to the project directory**
   ```bash
   cd quizpilot_beta
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Copy the `.env` file and update the required values:
   ```bash
   cp .env .env.local
   ```
   
   Update the following variables in `.env.local`:
   ```
   SECRET_KEY=your-secure-secret-key-here
   GOOGLE_API_KEY=your-google-api-key-here
   ```

5. **Initialize the database**
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

   The application will be available at `http://localhost:5000`

## Configuration

### Environment Variables

- `FLASK_APP`: Application entry point (default: `app.py`)
- `FLASK_ENV`: Environment mode (`development` or `production`)
- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_URL`: Database connection string
- `GOOGLE_API_KEY`: Google Gemini API key for AI quiz generation
- `UPLOAD_FOLDER`: Directory for uploaded files (default: `uploads`)
- `MAX_CONTENT_LENGTH`: Maximum file upload size in bytes

### Getting a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add the key to your `.env.local` file

## Project Structure

```
quizpilot_beta/
├── app.py                 # Flask application entry point
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables template
├── .gitignore           # Git ignore rules
├── app/
│   ├── __init__.py      # App package initialization
│   ├── models.py        # Database models
│   ├── routes.py        # Application routes
│   ├── services/        # Business logic services
│   │   ├── __init__.py
│   │   ├── quiz_generation_service.py
│   │   └── file_processing_service.py
│   ├── templates/       # Jinja2 templates
│   │   ├── base.html
│   │   ├── index.html
│   │   └── quiz-generator.html
│   └── static/          # Static files (CSS, JS, images)
├── uploads/             # File upload directory
└── migrations/          # Database migrations
```

## Usage

### Creating a Quiz

1. Navigate to the Quiz Generator page
2. Upload your study material (PDF, DOCX, PPTX, images, or text files)
3. Set a quiz title and select the number of questions
4. Click "Generate Quiz" and wait for AI processing
5. Take the quiz immediately or save it for later

### Taking a Quiz

1. Go to "My Quizzes" to see all created quizzes
2. Click "Take Quiz" on any quiz
3. Answer questions with multiple-choice options
4. Submit your answers to see results

### Reviewing Results

1. After completing a quiz, click "Review Answers"
2. See correct answers, explanations, and your performance
3. Track your progress over time

## API Endpoints

### Quiz Management
- `POST /api/quizzes/generate` - Generate quiz from uploaded file
- `GET /api/quizzes` - List all quizzes
- `GET /api/quizzes/<id>` - Get specific quiz
- `POST /api/quizzes/<id>/submit` - Submit quiz answers
- `GET /api/quizzes/results/<id>` - Get quiz results
- `GET /api/quizzes/<id>/stats` - Get quiz statistics

### Chat System
- `POST /api/chat/message` - Send message to AI chat

## Development

### Running in Development Mode

```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

### Database Migrations

```bash
# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade
```

### Adding New Features

1. Add database models in `app/models.py`
2. Create routes in `app/routes.py`
3. Add business logic in `app/services/`
4. Create templates in `app/templates/`
5. Add static files in `app/static/`

## Deployment

### Production Setup

1. Set `FLASK_ENV=production` in environment variables
2. Use a production WSGI server like Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 app:app
   ```
3. Set up a reverse proxy (Nginx)
4. Use PostgreSQL for the database
5. Configure proper logging and monitoring

### Environment Variables for Production

```
FLASK_ENV=production
SECRET_KEY=your-strong-production-secret-key
DATABASE_URL=postgresql://user:password@localhost/quizpilot
GOOGLE_API_KEY=your-google-api-key
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, email support@quizpilot.com or open an issue on GitHub.

## Acknowledgments

- Google Gemini AI for intelligent quiz generation
- Tailwind CSS for beautiful, responsive design
- Flask community for excellent documentation and tools
