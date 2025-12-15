from flask import Flask, render_template, request, jsonify
from flask_cors import CORS  # 建議加入 CORS 以免前端 fetch 報錯
import requests
import json
import re
import os

app = Flask(__name__)
CORS(app)  # 啟用 CORS 支援

# ================= 配置區 =================
HKU_API_KEY = os.getenv("HKU_API_KEY") 
API_VERSION = "2025-01-01-preview"
DEPLOYMENT_ID = "gpt-4.1" 
OPENAI_ENDPOINT = f"https://api.hku.hk/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview"

SYSTEM_TOKEN = os.getenv("LDS_TOKEN")  
LARAVEL_HOST_API = "https://lds.cite.hku.hk/api"

# 這裡保留原有的 API 配置，雖然你的 UI 目前是寫死的選項，但保留 Proxy 功能以備不時之需
SYSTEM_APIS = {
    "ILO_get_category":  {"url": f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/types", "method": "POST"}
}

openai_headers = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "api-key": HKU_API_KEY
}

# Define Disciplinary Practices (Context for AI)
DP_DEFINITIONS = """
1. Engineering Design: For creating solutions, prototypes, coding, or building systems.
2. Scientific Investigation: For experiments, hypothesis testing, observing natural phenomena.
3. Mock Legislative Procedure: For debating laws, social issues, policy making, or reaching consensus.
4. Performance Production: For arts, music, drama, creative expression, or public speaking.
5. Writing a News Report: For journalism, factual reporting, investigating events, or media studies.
6. General Inquiry: Fallback for general research or theoretical topics that don't fit specific practices.
"""

@app.route('/')
def home():
    return render_template('index.html')

# ==========================================
# 1. [API] General Chat (UPDATED WITH RESTRICTIONS)
# ==========================================
@app.route('/api/chat', methods=['POST'])
def chat_general():
    data = request.json
    user_msg = data.get('message', '')
    
    # Context from the form
    topic = data.get('topic', '')
    grade = data.get('grade', '')
    dp = data.get('dp', '')
    
    # --- MODIFIED SYSTEM PROMPT ---
    system_prompt = f"""
    You are an expert Learning Design (LD) Assistant.
    
    ### SCOPE OF WORK ###
    You are strictly limited to assisting with:
    1. Learning Design theories (Bloom's Taxonomy, Self-Directed Learning, etc.).
    2. Course curriculum planning and educational methodologies.
    3. The specific course details the user is filling out (Topic: {topic}, Grade: {grade}).
    4. Explaining Disciplinary Practices.
    
    ### RESTRICTIONS ###
    If the user asks about anything unrelated to education, learning design, or the course form (e.g., "What is the capital of France?", "Write a python game", "Tell me a joke", "Politics", "Cooking recipes"), you MUST refuse to answer.
    
    ### STANDARD REPLY ###
    If the query is out of scope, reply EXACTLY with this message:
    "I apologize, but I am designed to assist with Learning Design and Course Planning only. Please ask me something related to your curriculum."
    
    ### INSTRUCTIONS ###
    1. Analyze the user's input.
    2. If it is a greeting (e.g., "Hello", "Hi"), you may reply politely.
    3. If it is related to Learning Design, answer professionally.
    4. If it is unrelated, use the STANDARD REPLY provided above.
    """
    
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ],
        "temperature": 0.5, # Lower temperature to ensure it follows rules strictly
        "max_tokens": 500
    }
    
    try:
        response = requests.post(OPENAI_ENDPOINT, headers=openai_headers, json=payload)
        if response.status_code == 200:
            ai_data = response.json()
            reply_text = ai_data['choices'][0]['message']['content']
            return jsonify({"reply": reply_text})
        else:
            return jsonify({"reply": "I'm having trouble connecting to the AI brain right now."}), 500
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500


# ==========================================
# 2. [API] Suggest Disciplinary Practice
# ==========================================
@app.route('/api/suggest_dp', methods=['POST'])
def suggest_dp():
    data = request.json
    
    topic = data.get('topic') if data.get('topic') else "General Topic"
    description = data.get('description') if data.get('description') else "No description provided."
    subject = data.get('subject') if data.get('subject') else "General Studies"

    system_prompt = f"""
    You are an expert curriculum consultant. 
    Your task is to analyze the course details and recommend the SINGLE most suitable 'Disciplinary Practice'.
    
    ### DEFINITIONS ###
    {DP_DEFINITIONS}

    ### RULES ###
    1. If the topic is scientific (biology, physics, nature), choose "Scientific Investigation".
    2. If the topic is about building, coding, or making products, choose "Engineering Design".
    3. If the topic is about laws, debates, or society, choose "Mock Legislative Procedure".
    4. If the topic is arts, drama, or speaking, choose "Performance Production".
    5. If the topic is journalism or reporting, choose "Writing a News Report".
    6. **CRITICAL**: If the topic is vague, generic, or strictly theoretical (e.g., "History", "Math theory"), choose "General Inquiry".

    Return strict JSON format:
    {{
        "recommended_dp": "Name of Practice",
        "reason": "Brief reason."
    }}
    """

    user_prompt = f"""
    Analyze this course:
    - Subject: {subject}
    - Topic: {topic}
    - Description: {description}
    
    Select the best Disciplinary Practice.
    """

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 200
    }

    return call_openai_json(payload)

# ==========================================
# 3. [API] Generate ILOs
# ==========================================
@app.route('/api/generate_ilos', methods=['POST'])
def generate_ilos():
    data = request.json
    
    topic = data.get('topic', 'N/A')
    description = data.get('description', '')
    subject = data.get('subject', '') 
    grade = data.get('grade', 'Secondary School')
    bloom_level = data.get('bloom_level', 'Understand')
    action_verb = data.get('action_verb', '') 
    disciplinary_practice = data.get('disciplinary_practice', 'General Inquiry')

    system_prompt = f"""
    You are an expert curriculum developer.
    
    ### CONTEXT ###
    The user is designing a course using the '{disciplinary_practice}' framework.
    
    ### INSTRUCTIONS ###
    1. Generate 3 Intended Learning Outcomes (ILOs).
    2. **Bloom's Level**: Must match '{bloom_level}'.
    3. **Action Verb**: {f"Start with '{action_verb}'" if action_verb else "Choose an appropriate verb for this level"}.
    4. **Disciplinary Context**: The ILOs must reflect the specific nature of {disciplinary_practice}.
    5. Return a JSON LIST of objects.
    
    ### OUTPUT FORMAT ###
    [
        {{
            "statement": "Explain the principles of..."
        }},
        {{
            "statement": "Demonstrate how to..."
        }}
    ]
    """
    
    user_prompt = f"""
    Topic: {topic}
    Description: {description}
    Subject: {subject}
    Grade: {grade}
    """

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 800
    }
    
    return call_openai_json(payload)

# ==========================================
# Helper: OpenAI Call (Expects JSON)
# ==========================================
def call_openai_json(payload):
    try:
        response = requests.post(OPENAI_ENDPOINT, headers=openai_headers, json=payload)
        
        if response.status_code == 200:
            ai_data = response.json()
            if 'choices' not in ai_data or len(ai_data['choices']) == 0:
                 return jsonify({"error": "No content from AI"}), 500

            raw_content = ai_data['choices'][0]['message']['content']
            # Clean Markdown
            clean_content = re.sub(r'```json\s*|\s*```', '', raw_content).strip()
            
            try:
                parsed_json = json.loads(clean_content)
                return jsonify(parsed_json)
            except json.JSONDecodeError:
                return jsonify({"error": "AI format error", "raw": clean_content}), 500
        else:
            return jsonify({"error": f"OpenAI Error: {response.status_code}", "details": response.text}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)