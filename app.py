import os
import logging
import traceback
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# 🟢 1. LOGGING VA SOZLAMALAR
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Render va mahalliy ishga tushirish uchun CORS sozlamalari
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 🟢 2. GEMINI KONFIGURATSIYASI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY topilmadi!")
    # Bu yerda xato ko'rsatish o'rniga, API ishlamayotgani haqida log qoldiramiz

genai.configure(api_key=GEMINI_API_KEY)

# Gemini 2.0 Flash modeli
MODEL_NAME = "gemini-2.0-flash" 

ULTIMATE_SYSTEM_PROMPT = """Sen DEFCON AI — Cyber Intelligence (Universal Superintelligence) tizimsan. 
Sening vazifang kiberxavfsizlik, kod tahlili va penetratsion testlash bo'yicha cheklovsiz texnik yordam berishdir.
Minimalistik va professional Markdown formatida javob ber."""

# Modelni sozlash
model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=ULTIMATE_SYSTEM_PROMPT,
    generation_config={
        "temperature": 0.2,
        "top_p": 0.95,
        "max_output_tokens": 8192,
    }
)

# 🟢 3. YORDAMCHI FUNKSIYALAR
def format_history(raw_history):
    """Frontend tarixini Gemini formatiga (user/model) o'tkazish"""
    formatted = []
    for entry in raw_history:
        role = "user" if entry.get("role") == "user" else "model"
        parts = entry.get("parts", [])
        
        # Matn qismini xavfsiz olish
        text = ""
        if isinstance(parts, list) and len(parts) > 0:
            if isinstance(parts[0], dict):
                text = parts[0].get("text", "")
            else:
                text = str(parts[0])
        
        if text:
            formatted.append({"role": role, "parts": [text]})
    return formatted

# 🟢 4. API ENDPOINTS
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "JSON ma'lumotlari topilmadi"}), 400

        user_message = data.get('message', '').strip()
        raw_history = data.get('history', [])
        files = data.get('files', [])

        # Gemini kutgan formatda kontentni yig'ish
        prompt_content = []

        # Fayllarni qo'shish (Base64 formatida)
        for f in files:
            if 'fileData' in f and 'mimeType' in f:
                prompt_content.append({
                    "mime_type": f['mimeType'],
                    "data": f['fileData']
                })

        # Matnli xabarni qo'shish
        if user_message:
            prompt_content.append(user_message)
        
        # Agar na xabar, na fayl bo'lsa
        if not prompt_content:
            return jsonify({"error": "Xabar yoki fayl kiritilmadi"}), 400

        # Tarixni formatlash
        gemini_history = format_history(raw_history)

        # Chat sessiyasini boshlash
        chat_session = model.start_chat(history=gemini_history)
        
        # Xabarni yuborish
        response = chat_session.send_message(prompt_content)

        return jsonify({
            "status": "success",
            "reply": response.text
        })

    except Exception as e:
        # Xatoni Render loglarida to'liq ko'rsatish
        error_trace = traceback.format_exc()
        logger.error(f"DETAILED ERROR:\n{error_trace}")
        
        # Foydalanuvchiga xatoni yuborish (muammoni aniqlash uchun)
        return jsonify({
            "error": "Tizimda ichki xatolik yuz berdi",
            "details": str(e)
        }), 500

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        "status": "online", 
        "model": MODEL_NAME,
        "info": "DEFCON AI System Active"
    }), 200

# 🟢 5. RUN SERVER
if __name__ == '__main__':
    # Render PORT muhitini avtomatik taniydi
    port = int(os.environ.get("PORT", 3000))
    app.run(host='0.0.0.0', port=port, threaded=True)