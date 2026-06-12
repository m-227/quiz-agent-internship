# Quiz Agent 🎓🤖

An AI-powered quiz generation and grading system that converts lecture videos into structured quizzes using speech-to-text and large language models.

Quiz Agent allows instructors to:

- Upload lecture videos/audio files
- Automatically transcribe lectures
- Extract important concepts
- Generate multiple-choice questions using AI
- Review and edit generated questions
- Create Google Forms automatically
- Collect student responses
- Grade submissions automatically
- Send personalized feedback emails to students

---

## Demo Workflow

```
Lecture Video
      |
      v
Speech-to-Text (Whisper)
      |
      v
Lecture Transcript
      |
      v
Concept Extraction (GPT-4o-mini)
      |
      v
AI Generated Quiz
      |
      v
Google Form + Answer Key
      |
      v
Student Responses
      |
      v
Automatic Grading + Email Feedback
```

---

# Features

## 1. Lecture Transcription

Upload:

- MP4 videos
- MP3 audio files
- WAV audio files

The application converts lectures into text using:

- OpenAI Whisper API
- Faster Whisper (local transcription option)

---

## 2. AI Concept Extraction

The system identifies the five most important concepts from the lecture.

Example:

Input:

```
A lecture explaining neural networks, activation functions, backpropagation,
gradient descent, and optimization.
```

Output:

```
[
 "Neural networks",
 "Activation functions",
 "Backpropagation",
 "Gradient descent",
 "Optimization"
]
```

---

## 3. AI Question Generation

Using GPT-4o-mini, Quiz Agent generates:

- Multiple-choice questions
- Four answer options
- Correct answer
- Explanation
- Associated concept

Example:

```json
{
 "concept": "Gradient Descent",
 "question": "What does gradient descent optimize?",
 "options": [
    "The model architecture",
    "The loss function",
    "The dataset size",
    "The activation function"
 ],
 "correct_answer": "The loss function",
 "explanation": "Gradient descent minimizes the loss function by updating model parameters."
}
```

---

## 4. Question Editing

Before publishing the quiz, instructors can:

- Modify questions
- Change answer choices
- Update explanations
- Regenerate individual questions

---

## 5. Google Forms Integration

Quiz Agent automatically creates:

- Student-facing Google Form
- Private answer key spreadsheet

The generated form contains:

- Student email collection
- Quiz questions
- Multiple-choice options

---

## 6. Automated Grading

After students submit:

- Responses are collected from Google Sheets
- Answers are compared against the generated answer key
- Scores are calculated
- Performance statistics are generated

Statistics include:

- Average score
- Highest score
- Lowest score
- Number of students

---

## 7. Email Feedback System

Students receive personalized emails containing:

- Their score
- Question-by-question breakdown
- Correct answers
- Explanations
- Class statistics

Example:

```
Hi!

Your score: 4/5

Question:
What is gradient descent?

Your answer:
Backpropagation

Correct answer:
Optimization algorithm

Explanation:
Gradient descent updates parameters to minimize the loss function.

Keep it up!
```

---

# Tech Stack

## Frontend

- Streamlit

## AI Models

- OpenAI GPT-4o-mini
- OpenAI Whisper
- Faster Whisper

## APIs

- Google Forms API
- Google Sheets API
- Google Gmail API
- Google Apps Script API

## Languages

- Python
- JavaScript (Google Apps Script)

---

# Project Structure

```
Quiz-Agent/
│
├── app.py
│   └── Basic quiz generation prototype
│
├── quizagentv0.py
│   └── Full Quiz Agent application
│
├── task1.py
│   └── OpenAI API testing script
│
├── requirements.txt
│
├── .gitignore
│
└── README.md
```

---

# Installation

## 1. Clone Repository

```bash
git clone https://github.com/<your-username>/<repository-name>.git

cd Quiz-Agent
```

---

## 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate:

### Mac/Linux

```bash
source venv/bin/activate
```

### Windows

```bash
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Setup

Create a `.env` file:

```
OPENAI_API_KEY=your_openai_api_key
```

The following files are required for Google API authentication:

```
credentials.json
token.json
```

These files should **never be uploaded to GitHub**.

They are ignored using:

```
.gitignore
```

---

# Google API Setup

Enable the following Google APIs:

- Google Forms API
- Google Sheets API
- Gmail API
- Google Apps Script API
- Google Drive API

Create OAuth credentials:

1. Go to Google Cloud Console
2. Create a project
3. Enable required APIs
4. Create OAuth Desktop Client credentials
5. Download:

```
credentials.json
```

Place it in the project directory.

---

# Running the Application

Start Streamlit:

```bash
streamlit run quizagentv0.py
```

The application opens at:

```
http://localhost:8501
```

---

# Application Workflow

## Create Quiz Tab

1. Upload lecture video
2. Generate transcript
3. Extract concepts
4. Review concepts
5. Generate questions
6. Edit questions
7. Create Google Form

---

## Conduct Quiz Tab

1. Share generated Google Form link
2. Students submit answers
3. Responses are stored automatically

---

## Grade Quiz Tab

1. Enter:
   - Answer key spreadsheet ID
   - Student response spreadsheet ID

2. Generate grades

3. Review results

4. Send personalized emails

---

# Architecture

```
                 +----------------+
                 | Lecture Upload |
                 +-------+--------+
                         |
                         v
                +----------------+
                | Whisper Model  |
                +-------+--------+
                        |
                        v
                +---------------+
                | Transcript    |
                +-------+-------+
                        |
                        v
              +-------------------+
              | GPT-4o-mini       |
              | Concept Extraction|
              +---------+---------+
                        |
                        v
              +-------------------+
              | Question Generator|
              +---------+---------+
                        |
                        v
              +-------------------+
              | Google Forms API |
              +---------+---------+
                        |
                        v
              +-------------------+
              | Auto Grading      |
              | Gmail Feedback    |
              +-------------------+
```

---

# Future Improvements

Possible extensions:

- Support for PDF/text lecture notes
- Difficulty-based question generation
- Retrieval-Augmented Generation (RAG)
- Student performance analytics dashboard
- Automatic quiz difficulty estimation
- Support for multiple languages
- Better hallucination detection
- Teacher authentication

---

# Limitations

- AI-generated questions may require instructor review
- Whisper transcription quality depends on audio quality
- Google API authentication requires manual setup
- Generated quizzes depend on the quality of the lecture material

---

# Security

Sensitive files are excluded from version control:

```
.env
credentials.json
token.json
```

Never expose:

- OpenAI API keys
- Google OAuth credentials
- Student data

---

# License

MIT License

---

# Author

Created as an AI-powered educational automation project using LLMs, speech recognition, and cloud APIs.