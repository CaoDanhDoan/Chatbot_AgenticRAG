from flask import Flask, request, jsonify
from flask_cors import CORS
from graph import app_rag
from IPython.display import Image, display
import warnings
from pyngrok import ngrok

warnings.filterwarnings("ignore", category=FutureWarning)
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
def format_answer(answer: str):
    parts = str(answer).split('**')
    formatted_answer_parts = []
    is_bold = False
    for i, part in enumerate(parts):
        if i % 2 == 1:
            formatted_answer_parts.append(f'<strong>{part}</strong>')
        else:
            formatted_answer_parts.append(part)
    formatted_answer = ''.join(formatted_answer_parts)
    formatted_answer = formatted_answer.replace("* ", "- ")
    return formatted_answer.replace("\n", "<br>")
@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    question = data.get('question', '').strip()
    history = data.get('history', [])
    if not question:
        return jsonify({'answer': 'Vui lòng cung cấp một câu hỏi.', 'history': history}), 400
    try:
        initial_state = {
            "question": question,
            "history": history,
            "web_search_count": 0
        }
        result = app_rag.invoke(initial_state)
        answer = result.get('generation', 'Xin lỗi, tôi không thể tạo ra câu trả lời thỏa đáng.')
        formatted_answer = format_answer(answer)
        new_history = result.get("history", history)
        if len(new_history) > 5:
            new_history = new_history[-5:]
        return jsonify({'answer': formatted_answer, 'history': new_history})
    except Exception as e:
        print(f"Lỗi khi xử lý câu hỏi: {e}")
        return jsonify({'answer': 'Đã xảy ra lỗi trong quá trình xử lý. Vui lòng thử lại sau.', 'history': history}), 500

if __name__ == '__main__':
    # try:
    #     graph_image_data = app_rag.get_graph().draw_mermaid_png()
    #     display(Image(graph_image_data))
    # except Exception as e:
    #     print(f"Lỗi khi hiển thị đồ thị: {e}")
    try:
        public_url = ngrok.connect(5000).public_url
        print(f"Flask public URL: {public_url}")
        app.run(port=5000)
    except Exception as e:
        print(f"Không thể tạo ngrok: {e}")
        app.run(host='0.0.0.0', port=5000)
