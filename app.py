import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import uuid
import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from langgraph.types import Command
from pyngrok import ngrok

from graph import app_rag

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

def format_answer(answer: str) -> str:
    parts = str(answer).split('**')
    formatted = ''.join(
        f'<strong>{p}</strong>' if i % 2 else p
        for i, p in enumerate(parts)
    )
    return formatted.replace("* ", "- ").replace("\n", "<br>")

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json(silent=True) or {}
    print("REQ /ask:", data)  

    question   = (data.get('question') or '').strip()
    history    = data.get('history', [])
    thread_id  = data.get('thread_id') or str(uuid.uuid4())

    resume_present = 'resume' in data
    resume_payload = data.get('resume', None)

    config = {"configurable": {"thread_id": thread_id}}

    try:
        if resume_present:
            print(f"RESUME payload: {resume_payload!r} | thread_id: {thread_id}")
            result = app_rag.invoke(Command(resume=resume_payload), config=config)
        else:
            if not question:
                print("BAD REQUEST → thiếu 'question' và không có 'resume'")
                return jsonify({
                    "status": "ERROR",
                    "thread_id": thread_id,
                    "message": "Vui lòng cung cấp một câu hỏi.",
                    "history": history
                }), 400

            print(f"NEW TURN | thread_id: {thread_id} | question: {question!r}")
            initial_state = {"question": question, "history": history, "web_search_count": 0}
            result = app_rag.invoke(initial_state, config=config)

        interrupts = result.get("__interrupt__", None)
        if interrupts:
            payloads = [it.value for it in interrupts]
            print("INTERRUPTED → chờ người dùng:", payloads)
            return jsonify({
                "status": "INTERRUPTED",
                "thread_id": thread_id,
                "interrupts": payloads
            })

        answer = result.get('generation', 'Xin lỗi, tôi không thể tạo ra câu trả lời thỏa đáng.')
        formatted_answer = format_answer(answer)
        new_history = result.get("history", history)
        if len(new_history) > 3:
            new_history = new_history[-3:]

        preview = (str(answer) if isinstance(answer, str) else str(answer))[:120]
        print(f"COMPLETE | thread_id: {thread_id} | answer[:120]: {preview}")

        return jsonify({
            "status": "OK",
            "thread_id": thread_id,
            "answer": formatted_answer,
            "history": new_history
        })

    except Exception as e:
        msg = str(e)
        if "429" in msg or "ResourceExhausted" in msg or "rate limit" in msg.lower():
            print("RATE LIMIT hit:", msg)
            return jsonify({
                "status": "RATE_LIMIT",
                "thread_id": thread_id,
                "message": "LLM đang quá tải (429). Vui lòng chờ 60–90 giây rồi thử lại."
            }), 429

        print("SERVER ERROR:", msg)
        return jsonify({
            "status": "ERROR",
            "thread_id": thread_id,
            "message": "Đã xảy ra lỗi trong quá trình xử lý.",
            "history": history
        }), 500

@app.get("/_public_url")
def get_public_url():
    """Cho FE hỏi URL công khai (nếu đang dùng ngrok)."""
    return jsonify({"public_url": app.config.get("PUBLIC_URL")})

if __name__ == '__main__':
    PORT = int(os.getenv("PORT", "5000"))
    try:
        public_url = ngrok.connect(PORT).public_url
        app.config["PUBLIC_URL"] = public_url
        print(f"Flask public URL: {public_url}")
    except Exception as e:
        print(f"Không thể tạo ngrok: {e}")
        app.config["PUBLIC_URL"] = f"http://localhost:{PORT}"
        print(f"Chạy local: {app.config['PUBLIC_URL']}")
    app.run(host='0.0.0.0', port=PORT)