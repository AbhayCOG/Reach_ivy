# API endpoints for FastAPI app
from fastapi import APIRouter, WebSocket, Request
from app.models.schemas import EssayPrompt, EssayRequest
from app.services.audio import AudioService
from app.services.llm import LLMService
from app.services.stt import STTService
from app.services.storage import StorageService
import re
import json
import uuid

router = APIRouter()
audio_service = AudioService()
llm_service = LLMService()
stt_service = STTService()
storage_service = StorageService()

@router.get("/")
async def health_check():
    return {"message": "Welcome to the FastAPI application! It is running smoothly."}

@router.post("/store_student_info")
async def store_student_info(payload: Request):
    id = str(uuid.uuid4())
    data = await payload.json()
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    major = data.get("major")
    degree = data.get("degree")
    university = data.get("university")
    short_term_goal = data.get("short_term_goal")
    long_term_goal = data.get("long_term_goal")
    storage_service.store_student_info(id, first_name, last_name, major, degree, university, short_term_goal, long_term_goal)
    return {"session_id": id}

@router.post("/generate_questions")
async def get_questions(essay_prompt: EssayPrompt):
    # id = str(uuid.uuid4())
    id = essay_prompt.session_id
    topic = essay_prompt.topic
    student_info = storage_service.get_student_info(id)
    prompt = f"""
    You also have 20+ years of experience as a college admissions counselor, trained in asking the right brainstorming questions to help students uncover strong, personal stories.
    The student is applying to college and needs to write an essay on the topic:
    "{topic}"
    The student info is:
    {student_info.get("student_info", {})}
    TASK:
    - Generate EXACTLY 5 thoughtful, open-ended questions.
    - Each question must encourage the student to share personal stories, values, experiences, challenges, skills, or future goals.
    - Keep questions short, simple, and conversational (suitable for a voice interaction).
    - Avoid yes/no questions.
    - OUTPUT FORMAT: Return ONLY a valid JSON array of 5 strings, nothing else. Do NOT wrap in code blocks.
    """
    raw_response = await llm_service.call_gemini_api(prompt)
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw_response.strip(), flags=re.MULTILINE).strip()
    try:
        questions_list = json.loads(cleaned)
        if not (isinstance(questions_list, list) and len(questions_list) == 5 and all(isinstance(q, str) for q in questions_list)):
            raise ValueError("Invalid format from LLM")
    except Exception:
        return {"questions_raw": raw_response, "error": "Could not parse JSON array"}
    questions = {}
    for i, question in enumerate(questions_list):
        question_audio = audio_service.generate_audio(question)
        questions[f"q{i+1}"] = {"text": question, "audio": question_audio}
    return {"questions": questions}

@router.websocket("/stt/answer")
async def websocket_endpoint(websocket: WebSocket):
    await stt_service.transcribe_audio(websocket)

@router.post("/save_answer")
async def save_answer(payload: Request):
    data = await payload.json()
    session_id = data.get("session_id")
    question = data.get("question")
    answer = data.get("answer")
    return storage_service.save_answer(session_id, question, answer)


@router.get("/get_answers/{session_id}")
async def get_answers(session_id: str):
    return storage_service.get_answers(session_id)

# New endpoint to get student info
@router.get("/get_student_info/{session_id}")
async def get_student_info(session_id: str):
    return storage_service.get_student_info(session_id)

@router.post("/generate_essay")
async def generate_essay(req: EssayRequest):
    qa_pairs = storage_service.get_answers(req.session_id)
    qa_pairs = qa_pairs.get("qa_pairs", [])
    student_info = storage_service.get_student_info(req.session_id)
    prompt = f"""
You are a top essay strategist with deep expertise in admissions essays to top global universities. 
You help students develop powerful essay narratives that showcase their individuality, strengths, and fit with the college.

The student is applying to college and needs to write an essay on the topic:
"{req.topic}"

The student has answered the following brainstorming questions:
{qa_pairs}

The student's info is:
{student_info.get("student_info", {})}

TASK:
1. Do NOT write the full essay.
2. Instead, create a detailed **essay strategy and structure** that the student can use to write their own essay.
3. Break down the essay into sections with word count guidance:
   - Introduction (hook + connection to topic)
   - Body Paragraph 1 (story/experience + reflection)
   - Body Paragraph 2 (another story/lesson + values)
   - Body Paragraph 3 (future goals, connection to college)
   - Conclusion (growth, tying back to topic)
4. For each section, suggest what content/ideas from the student’s answers should be included, but leave the actual writing to the student.
5. Ensure the outline feels personal, authentic, and reflective.
6. OUTPUT: Only return the structured outline with headings, sub-points, and suggested word counts.
"""

    raw_response = await llm_service.call_gemini_api(prompt)
    essay_audio = audio_service.generate_audio(raw_response)
    return {"essay": raw_response, "essay_audio": essay_audio}


@router.post("/evaluate_essay")
async def evaluate_essay(payload: Request):
    data = await payload.json()
    essay = data.get("essay")
    topic = data.get("topic")
    session_id = data.get("session_id")
    student_info = storage_service.get_student_info(session_id)
    qa_pairs = storage_service.get_answers(session_id)
    prompt = f"""
You are a top essay coach with deep expertise in admissions essays to top global universities.
Your task is to evaluate the student's essay draft and give constructive, specific feedback.

Essay Topic:
"{topic}"

Student Essay:
{essay}

Student Info (for context):
{student_info.get("student_info", {})}

Brainstormed Content (student's answers to prep questions):
{qa_pairs}

Evaluation Criteria:
1. Clarity, coherence, and logical flow of ideas
2. Depth of personal reflection and authenticity
3. Effective use of life stories, values, and experiences
4. Connection to the essay topic and the college’s values
5. Overall impact, originality, and persuasiveness

TASK:
1. Give a detailed evaluation of the essay based on the above criteria.
2. Identify strong parts of the essay (what works well).
3. Point out weak or missing elements — e.g., unclear reflection, lack of depth, missing connection to student’s goals, underdeveloped conclusion.
4. Suggest **specific improvements** (e.g., "expand on X story", "show more reflection on Y", "connect Z to future goals").
5. Ensure the tone is constructive, respectful, and encouraging.
6. OUTPUT: Only return the evaluation text, no explanations or formatting.
"""
    raw_response = await llm_service.call_gemini_api(prompt)
    evaluation_audio = audio_service.generate_audio(raw_response)
    return {"evaluation": raw_response, "evaluation_audio": evaluation_audio}