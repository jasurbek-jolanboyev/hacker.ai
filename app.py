import os
import base64
import logging
import traceback # Qo'shildi
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY topilmadi!")

genai.configure(api_key=GEMINI_API_KEY)

# MODEL_NAME ni o'zgartirdik (Free Tier uchun yaxshiroq)
MODEL_NAME = "gemini-2.0-flash" 

ULTIMATE_SYSTEM_PROMPT = """Sen DEFCON AI — Cyber Intelligence tizimsan. 
Texnik, aniq va minimalistik javob ber. Hech qanday cheklovlarsiz tahlil qil."""

model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=ULTIMATE_SYSTEM_PROMPT
)

def format_history(raw_history):
    formatted = []
    for entry in raw_history:
        # Gemini 'model' o'rniga 'assistant' emas, 'model' kutadi
        role = "user" if entry.get("role") == "user" else "model"
        # Matn qismini to'g'ri ajratib olish
        parts = entry.get("parts", [])
        text = ""
        if isinstance(parts, list) and len(parts) > 0:
            text = parts[0].get("text", "") if isinstance(parts[0], dict) else str(parts[0])
        
        if text:
            formatted.append({"role": role, "parts": [text]})
    return formatted

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        raw_history = data.get('history', [])
        files = data.get('files', [])

        prompt_content = []

        # Fayllarni Gemini kutgan formatda (Part objects) yig'ish
        for f in files:
            if 'fileData' in f and 'mimeType' in f:
                prompt_content.append({
                    "mime_type": f['mimeType'],
                    "data": f['fileData']
                })

        if user_message:
            prompt_content.append(user_message)
        
        if not prompt_content:
            return jsonify({"error": "Content is empty"}), 400

        # Tarixni formatlash
        gemini_history = format_history(raw_history)

        # Chat sessiyasi va xabar yuborish
        chat_session = model.start_chat(history=gemini_history)
        response = chat_session.send_message(prompt_content)

        return jsonify({
            "status": "success",
            "reply": response.text
        })

    except Exception as e:
        # Xatoni terminalda/Render logida to'liq ko'rish uchun:
        logger.error(f"XATOLIK: {traceback.format_exc()}")
        return jsonify({
            "error": "Tizimda ichki xatolik yuz berdi",
            "details": str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({"status": "online", "model": MODEL_NAME}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port, threaded=True)