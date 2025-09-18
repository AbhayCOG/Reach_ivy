# Redis storage service
import os
import redis
import json

class StorageService:
    def __init__(self):
        self.redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

    def save_answer(self, session_id: str, question: str, answer: str):
        key = f"session:{session_id}"
        session_data = self.redis_client.get(key)
        if session_data:
            session_dict = json.loads(session_data)
        else:
            session_dict = {"qa_pairs": []}
        session_dict["qa_pairs"].append({"question": question, "answer": answer})
        self.redis_client.set(key, json.dumps(session_dict))
        return {"message": "Answer saved successfully", "session_id": session_id}

    def get_answers(self, session_id: str):
        key = f"session:{session_id}"
        session_data = self.redis_client.get(key)
        if not session_data:
            return {"session_id": session_id, "qa_pairs": [], "message": "No data found for this session"}
        session_dict = json.loads(session_data)
        qa_pairs = session_dict.get("qa_pairs", [])
        return {"qa_pairs": qa_pairs}

    def store_student_info(self, session_id: str, first_name: str, last_name: str, major: str, degree: str, university: str, short_term_goal: str, long_term_goal: str):
        key = f"student:{session_id}"
        student_info = {
            "first_name": first_name,
            "last_name": last_name,
            "major": major,
            "degree": degree,
            "university": university,
            "short_term_goal": short_term_goal,
            "long_term_goal": long_term_goal
        }
        self.redis_client.set(key, json.dumps(student_info))
        return {"message": "Student info stored successfully", "session_id": session_id}

    def get_student_info(self, session_id: str):
        key = f"student:{session_id}"
        student_data = self.redis_client.get(key)
        if not student_data:
            return {"session_id": session_id, "student_info": None, "message": "No student info found for this session"}
        student_info = json.loads(student_data)
        return {"session_id": session_id, "student_info": student_info}
