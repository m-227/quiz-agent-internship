import streamlit as st
from openai import OpenAI
import tempfile
import os


client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
st.title("Quiz Agent")

# initialise session state
if "quiz" not in st.session_state:
    st.session_state.quiz = None
if "full_text" not in st.session_state:
    st.session_state.full_text = None

# Step 1: Upload MP4
uploaded_file = st.file_uploader("Upload a video or audio file", type=["mp4", "mp3", "wav"])

if uploaded_file and st.button("Generate Quiz"):

    # save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    # Step 2: Transcribe with Whisper
    with st.spinner("Transcribing audio..."):
        with open(tmp_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        st.session_state.full_text = transcript.text
        os.remove(tmp_path)

    # Step 3: Generate quiz
    with st.spinner("Generating quiz..."):
        prompt = f"""
        Do not use any markdown formatting, stars, dashes, or bullet points in your response. Use plain text only.
        You are an educational assistant. Given the transcript below, do the following:
        1. Summarize 5 key concepts from the transcript
        2. For each concept, generate one Yes/No question that tests it
        3. Provide the answer (Yes or No) and explain why
        Format your response exactly like this for each concept:
        Concept: ...
        Question: ...
        Answer: Yes/No
        Why: ...
        Transcript:
        {st.session_state.full_text}
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful educational assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        st.session_state.quiz = response.choices[0].message.content

# show quiz and grading if quiz exists
if st.session_state.quiz:
    st.subheader("Transcript")
    st.text_area("", st.session_state.full_text or "", height=200)

    st.subheader("Generated Quiz")
    st.text_area("Review and edit the quiz below:", st.session_state.quiz, height=400)

    st.subheader("Enter Your Answers")

    # extract correct answers
    correct_answers = {}
    question_count = 0
    for line in st.session_state.quiz.split("\n"):
        if line.startswith("Answer:"):
            question_count += 1
            answer = line.replace("Answer:", "").strip()
            correct_answers[f"Q{question_count}"] = answer

    # show dropdowns
    student_answers = {}
    for q in correct_answers:
        student_answers[q] = st.selectbox(f"{q}:", ["Yes", "No"], key=q)

    if st.button("Submit Answers"):
        st.subheader("Results")
        total_score = 0
        for q in correct_answers:
            correct = correct_answers[q].lower()
            student = student_answers[q].lower()
            score = 1 if student == correct else 0
            total_score += score
            if score == 1:
                st.success(f"{q}: Correct")
            else:
                st.error(f"{q}: Incorrect — correct answer was {correct_answers[q]}")
        st.write(f"**Total Score: {total_score} out of {len(correct_answers)}**")