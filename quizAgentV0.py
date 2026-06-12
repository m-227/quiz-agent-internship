import streamlit as st
from faster_whisper import WhisperModel
from openai import OpenAI
import json
import os
import tempfile
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
# ---- Backend Functions ----

def transcribe_video(file_path):
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    segments, info = model.transcribe(file_path, beam_size=1)
    transcript = ""
    for segment in segments:
        transcript += segment.text
    return transcript

def generate_concepts(transcript):
    prompt = f"""
Return ONLY valid JSON.
Format:
{{
  "concepts": ["concept 1", "concept 2", "concept 3", "concept 4", "concept 5"]
}}
Extract the 5 most important concepts from this lecture.
Transcript:
{transcript}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    content = response.choices[0].message.content
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)["concepts"]

def generate_questions(transcript, concepts):
    prompt = f"""
Return ONLY valid JSON. Do NOT modify or reword concepts.
[
  {{
    "concept": "One of the provided concepts exactly (copy verbatim)",
    "question": "Question text",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "Option A",
    "explanation": "Why this answer is correct"
  }}
]
Generate 5 MCQs from the transcript using these concepts. Every question MUST include "concept".
Use ONLY these concepts:
{concepts}
Transcript:
{transcript}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    content = response.choices[0].message.content
    content = content.replace("```json", "").replace("```", "").strip()
    return json.loads(content)

def regenerate_question(transcript, old_question):
    prompt = f"""
Generate ONE new MCQ from this transcript.
The question MUST be about this concept ONLY: "{old_question["concept"]}"
Do NOT repeat this question: {old_question["question"]}
Return ONLY valid JSON:
{{
  "question": "...",
  "options": ["A","B","C","D"],
  "correct_answer": "...",
  "explanation": "..."
}}
Transcript:
{transcript}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt}
        ]
    )
    content = response.choices[0].message.content
    content = content.replace("```json", "").replace("```", "").strip()
    q = json.loads(content)
    q["concept"] = old_question["concept"]
    return q

def get_google_creds():
    SCOPES = [
        "https://www.googleapis.com/auth/forms.body",
        "https://www.googleapis.com/auth/forms.body.readonly",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/script.projects",
        "https://www.googleapis.com/auth/gmail.send"
    ]
    flow = InstalledAppFlow.from_client_secrets_file(
       "credentials.json",
        SCOPES
    )
    return flow.run_local_server(port=0)

def create_google_form(questions):
    creds = get_google_creds()
    forms_service = build("forms", "v1", credentials=creds)

    form = forms_service.forms().create(
        body={"info": {"title": "AI Generated Quiz"}}
    ).execute()
    form_id = form["formId"]

    requests = []
    requests.append({
        "createItem": {
            "item": {
                "title": "Your Email Address",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": 0}
        }
    })
    for i, q in enumerate(questions):
        requests.append({
            "createItem": {
                "item": {
                    "title": q["question"],
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [{"value": option} for option in q["options"]]
                            }
                        }
                    }
                },
                "location": {"index": i + 1}
            }
        })
    forms_service.forms().batchUpdate(
        formId=form_id, body={"requests": requests}
    ).execute()

    # create answer key sheet
    sheets_service = build("sheets", "v4", credentials=creds)
    sheet = sheets_service.spreadsheets().create(
        body={"properties": {"title": "AI Generated Quiz - Answer Key (PRIVATE)"}}
    ).execute()
    sheet_id = sheet["spreadsheetId"]

    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": "AnswerKey", "hidden": True}}}]}
    ).execute()

    answer_key_data = [
        [q["question"] for q in questions],
        [q["correct_answer"] for q in questions],
        [q["explanation"] for q in questions],
        [q.get("concept", "") for q in questions]
    ]
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="AnswerKey!A1",
        valueInputOption="RAW",
        body={"values": answer_key_data}
    ).execute()

    # write visible answer key for instructor
    visible_data = [["Concept", "Question", "Correct Answer", "Explanation"]]
    for q in questions:
        visible_data.append([
            q.get("concept", ""),
            q["question"],
            q["correct_answer"],
            q["explanation"]
        ])
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Sheet1!A1",
        valueInputOption="RAW",
        body={"values": visible_data}
    ).execute()

    attach_appscript_to_sheet(sheet_id, creds)

    return {
        "form_id": form_id,
        "sheet_id": sheet_id,
        "edit_url": f"https://docs.google.com/forms/d/{form_id}/edit",
        "student_url": f"https://docs.google.com/forms/d/{form_id}/viewform",
        "answer_sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}",
        "correct_answers": {q["question"]: q["correct_answer"] for q in questions}
    }

def attach_appscript_to_sheet(sheet_id, creds):
    script_service = build("script", "v1", credentials=creds)
    script_project = script_service.projects().create(
        body={"title": "Quiz Grader", "parentId": sheet_id}
    ).execute()
    script_id = script_project["scriptId"]
    code = """
function onFormSubmit(e) {
  var values = e.values;
  var email = values[1];
  var total = values.length - 2;
  if (!email || email == "") return;
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var answerSheet = ss.getSheetByName("AnswerKey");
  var questions = answerSheet.getRange(1, 1, 1, total).getValues()[0];
  var correctAnswers = answerSheet.getRange(2, 1, 1, total).getValues()[0];
  var explanations = answerSheet.getRange(3, 1, 1, total).getValues()[0];
  var concepts = answerSheet.getRange(4, 1, 1, total).getValues()[0];
  var score = 0;
  var breakdown = "";
  for (var i = 0; i < total; i++) {
    var studentAnswer = values[i + 2];
    var correct = correctAnswers[i];
    var isCorrect = studentAnswer.trim() == correct.trim();
    if (isCorrect) score++;
    breakdown += "\\n---\\n";
    breakdown += "Concept: " + concepts[i] + "\\n";
    breakdown += "Q: " + questions[i] + "\\n";
    breakdown += (isCorrect ? "✅" : "❌") + " Your answer: " + studentAnswer + "\\n";
    if (!isCorrect) breakdown += "Correct answer: " + correct + "\\n";
    breakdown += "Explanation: " + explanations[i] + "\\n";
  }
  var subject = "Your Quiz Results: " + score + "/" + total;
  var body = "Hi!\\n\\nYour score: " + score + "/" + total + "\\n\\nFull breakdown:" + breakdown + "\\n\\nKeep it up!";
  GmailApp.sendEmail(email, subject, body);
}

function setupTrigger() {
  var triggers = ScriptApp.getProjectTriggers();
  for (var i = 0; i < triggers.length; i++) {
    ScriptApp.deleteTrigger(triggers[i]);
  }
  ScriptApp.newTrigger("onFormSubmit")
    .forSpreadsheet(SpreadsheetApp.getActiveSpreadsheet())
    .onFormSubmit()
    .create();
}
"""
    script_service.projects().updateContent(
        scriptId=script_id,
        body={
            "files": [
                {"name": "Code", "type": "SERVER_JS", "source": code},
                {"name": "appsscript", "type": "JSON", "source": '{"timeZone":"America/New_York","exceptionLogging":"STACKDRIVER","runtimeVersion":"V8"}'}
            ]
        }
    ).execute()
    #script_service.scripts().run(
        #scriptId=script_id,
        #body={"function": "setupTrigger"}
   # ).execute()

def grade_quiz(answer_sheet_id, responses_sheet_id):
    creds = get_google_creds()
    sheets_service = build("sheets", "v4", credentials=creds)

    # get answer key
    answer_key = sheets_service.spreadsheets().values().get(
        spreadsheetId=answer_sheet_id,
        range="AnswerKey!A1:Z4"
    ).execute().get("values", [])

    questions = answer_key[0]
    correct_answers = answer_key[1]
    explanations = answer_key[2]
    concepts = answer_key[3]

    # get student responses
    responses = sheets_service.spreadsheets().values().get(
        spreadsheetId=responses_sheet_id,
        range="Form Responses 1!A1:Z1000"
    ).execute().get("values", [])

    headers = responses[0]
    student_rows = responses[1:]

    results = []
    score_summary = []

    for row in student_rows:
        if len(row) < 2:
            continue
        timestamp = row[0]
        email = row[1]
        student_answers = row[2:]

        score = 0
        breakdown = []
        for i, q in enumerate(questions):
            if i >= len(student_answers):
                break
            student_ans = student_answers[i].strip()
            correct_ans = correct_answers[i].strip()
            is_correct = student_ans == correct_ans
            if is_correct:
                score += 1
            breakdown.append({
                "concept": concepts[i],
                "question": q,
                "student_answer": student_ans,
                "correct_answer": correct_ans,
                "is_correct": is_correct,
                "explanation": explanations[i]
            })

        results.append({
            "email": email,
            "score": score,
            "total": len(questions),
            "breakdown": breakdown
        })
        score_summary.append(score)

    # aggregate statistics
    if score_summary:
        avg = sum(score_summary) / len(score_summary)
        high = max(score_summary)
        low = min(score_summary)
    else:
        avg = high = low = 0

    aggregate = {
        "total_students": len(score_summary),
        "average": round(avg, 2),
        "highest": high,
        "lowest": low
    }

    return results, aggregate

def send_grade_emails(results, aggregate, creds):
    gmail_service = build("gmail", "v1", credentials=creds)
    import base64
    from email.mime.text import MIMEText

    for student in results:
        breakdown_text = ""
        for b in student["breakdown"]:
            breakdown_text += f"\n---\n"
            breakdown_text += f"Concept: {b['concept']}\n"
            breakdown_text += f"Q: {b['question']}\n"
            breakdown_text += f"{'✅' if b['is_correct'] else '❌'} Your answer: {b['student_answer']}\n"
            if not b["is_correct"]:
                breakdown_text += f"Correct answer: {b['correct_answer']}\n"
            breakdown_text += f"Explanation: {b['explanation']}\n"

        body = f"""Hi!

Your score: {student['score']}/{student['total']}

Full breakdown:
{breakdown_text}

Class Statistics:
- Average score: {aggregate['average']}/{student['total']}
- Highest score: {aggregate['highest']}/{student['total']}
- Lowest score: {aggregate['lowest']}/{student['total']}
- Total students: {aggregate['total_students']}

Keep it up!"""

        message = MIMEText(body)
        message["to"] = student["email"]
        message["subject"] = f"Your Quiz Results: {student['score']}/{student['total']}"
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        gmail_service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()

# ---- Streamlit UI ----

st.set_page_config(page_title="Quiz Agent", layout="wide")
st.title("Quiz Agent")

# session state
for key in ["transcript", "concepts", "questions", "form_result"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ---- TABS ----
# ---- TABS ----
tab1, tab2, tab3 = st.tabs(["Create Quiz", "Conduct Quiz", "Grade Quiz"])

# ==============================
# TAB 1: CREATE QUIZ
# ==============================
with tab1:
    st.header("Create Quiz")
    st.write("Upload your lecture video and generate a quiz for your students.")

    uploaded_file = st.file_uploader("Upload lecture (MP4/MP3/WAV)", type=["mp4", "mp3", "wav"])

    if uploaded_file and st.button("Transcribe Video"):
        with open("temp_audio.mp4", "wb") as f:
            f.write(uploaded_file.read())
        with st.spinner("Transcribing... this may take a minute"):
            st.session_state.transcript = transcribe_video("temp_audio.mp4")
            os.remove("temp_audio.mp4")
        st.success("Transcription complete!")

    if st.session_state.transcript:
        st.subheader("Transcript")
        st.text_area("", st.session_state.transcript, height=150)

        if st.button("Extract Concepts"):
            with st.spinner("Extracting key concepts..."):
                st.session_state.concepts = generate_concepts(st.session_state.transcript)

    if st.session_state.concepts:
        st.subheader("Review Concepts")
        st.write("Edit, remove, or keep these concepts before generating the quiz.")
        edited_concepts = []
        for i, concept in enumerate(st.session_state.concepts):
            edited = st.text_input(f"Concept {i+1}", value=concept, key=f"concept_{i}")
            edited_concepts.append(edited)

        if st.button("Generate Quiz Questions"):
            with st.spinner("Generating questions..."):
                st.session_state.questions = generate_questions(
                    st.session_state.transcript, edited_concepts
                )

    if st.session_state.questions:
        st.subheader("Review Questions")
        st.write("Edit questions directly or regenerate them.")

        for i, q in enumerate(st.session_state.questions):
            with st.expander(f"Q{i+1}: {q['question']}"):
                new_question = st.text_input("Question", value=q["question"], key=f"q_text_{i}")
                new_options = []
                for j, opt in enumerate(q["options"]):
                    new_opt = st.text_input(f"Option {j+1}", value=opt, key=f"opt_{i}_{j}")
                    new_options.append(new_opt)
                new_correct = st.selectbox("Correct Answer", new_options,
                    index=new_options.index(q["correct_answer"]) if q["correct_answer"] in new_options else 0,
                    key=f"correct_{i}")
                new_explanation = st.text_area("Explanation", value=q["explanation"], key=f"exp_{i}")

                if st.button(f"Save Q{i+1} edits", key=f"save_{i}"):
                    st.session_state.questions[i]["question"] = new_question
                    st.session_state.questions[i]["options"] = new_options
                    st.session_state.questions[i]["correct_answer"] = new_correct
                    st.session_state.questions[i]["explanation"] = new_explanation
                    st.success("Saved!")

                if st.button(f"Regenerate Q{i+1}", key=f"regen_{i}"):
                    with st.spinner("Regenerating..."):
                        st.session_state.questions[i] = regenerate_question(
                            st.session_state.transcript, q
                        )
                    st.rerun()

        if st.button("Create Google Form + Answer Sheet"):
            with st.spinner("Creating Google Form and Answer Sheet..."):
                st.session_state.form_result = create_google_form(st.session_state.questions)
            st.success("Done!")
            st.write(f"**Student Form URL:** {st.session_state.form_result['student_url']}")
            st.write(f"**Answer Sheet (keep private):** {st.session_state.form_result['answer_sheet_url']}")

# ==============================
# TAB 2: CONDUCT QUIZ
# ==============================
with tab2:
    st.header("Conduct Quiz")
    st.write("Share the quiz link with your students and collect their responses.")

    if st.session_state.form_result:
        st.success("Quiz is ready to share!")
        st.write("**Share this link with students:**")
        st.code(st.session_state.form_result["student_url"])
        st.write("Students will submit their answers via Google Form. Responses are automatically collected in a Google Sheet.")
        st.write("Once all students have submitted, move to the **Grade Quiz** tab.")
    else:
        st.info("No quiz created yet. Go to the Create Quiz tab first.")

# ==============================
# TAB 3: GRADE QUIZ
# ==============================
with tab3:
    st.header("Grade Quiz")
    st.write("Input the Google Sheet IDs to grade all student responses.")

    answer_sheet_id = st.text_input("Answer Key Sheet ID (from Create Quiz):")
    responses_sheet_id = st.text_input("Student Responses Sheet ID (from Google Form):")

    if answer_sheet_id and responses_sheet_id and st.button("Grade All Students"):
        with st.spinner("Grading..."):
            results, aggregate = grade_quiz(answer_sheet_id, responses_sheet_id)
            st.session_state["results"] = results
            st.session_state["aggregate"] = aggregate

    if "results" in st.session_state and st.session_state["results"]:
        results = st.session_state["results"]
        aggregate = st.session_state["aggregate"]

        st.subheader("Aggregate Statistics")
        st.write("Edit these values if needed before sending emails.")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            aggregate["total_students"] = st.number_input("Total Students",
                value=aggregate["total_students"], step=1)
        with col2:
            aggregate["average"] = st.number_input("Average Score",
                value=float(aggregate["average"]), step=0.1)
        with col3:
            aggregate["highest"] = st.number_input("Highest Score",
                value=aggregate["highest"], step=1)
        with col4:
            aggregate["lowest"] = st.number_input("Lowest Score",
                value=aggregate["lowest"], step=1)

        st.subheader("Individual Results")
        st.write("Edit scores or explanations before sending.")
        for s_idx, student in enumerate(results):
            with st.expander(f"{student['email']} — {student['score']}/{student['total']}"):
                results[s_idx]["score"] = st.number_input(
                    "Score", value=student["score"],
                    min_value=0, max_value=student["total"],
                    key=f"score_{s_idx}"
                )
                for b_idx, b in enumerate(student["breakdown"]):
                    st.write(f"**{b['question']}**")
                    st.write(f"Student answer: {b['student_answer']} | Correct: {b['correct_answer']}")
                    results[s_idx]["breakdown"][b_idx]["is_correct"] = st.checkbox(
                        "Mark as correct",
                        value=b["is_correct"],
                        key=f"correct_{s_idx}_{b_idx}"
                    )
                    results[s_idx]["breakdown"][b_idx]["explanation"] = st.text_area(
                        "Explanation",
                        value=b["explanation"],
                        key=f"explanation_{s_idx}_{b_idx}"
                    )
                    st.divider()

        if st.button("Send Grade Emails to All Students"):
            with st.spinner("Sending emails..."):
                creds = get_google_creds()
                send_grade_emails(results, aggregate, creds)
            st.success("Emails sent to all students!")