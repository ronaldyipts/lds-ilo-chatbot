from flask import Flask, render_template, request, jsonify
import requests
import json
import os

app = Flask(__name__)

# ================= 配置區 =================

# 1. HKU OpenAI 設定
HKU_API_KEY = os.getenv("HKU_API_KEY")  # 請填入
API_VERSION = "2025-01-01-preview"
DEPLOYMENT_ID = "gpt-4.1"
OPENAI_ENDPOINT = "https://api.hku.hk/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview"

# 2. System (LDS) 設定
SYSTEM_TOKEN = os.getenv("LDS_TOKEN") # 請填入
LARAVEL_HOST_API = "https://lds.cite.hku.hk/api"

SYSTEM_APIS = {
    "get_subjects":      {"url": f"{LARAVEL_HOST_API}/chatbot/options/courses/subjects", "method": "POST"},
    "get_grade_levels":  {"url": f"{LARAVEL_HOST_API}/chatbot/options/courses/grade-levels", "method": "POST"},
    "ILO_get_bt_levels": {"url": f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/bloom-taxonomy-levels", "method": "POST"},
    "ILO_get_bt_verbs":  {"url": f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/bloom-taxonomy-verbs", "method": "POST"},
    "ILO_get_category":  {"url": f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/types", "method": "POST"}
}

openai_headers = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "api-key": HKU_API_KEY
}

system_headers = {
    "Authorization": f"Bearer {SYSTEM_TOKEN}",
    "Content-Type": "application/json"
}

@app.route('/')
def home():
    return render_template('index.html')

# --- Proxy API 供前端呼叫選項 (Step 3-6) ---
@app.route('/proxy/<api_key>', methods=['GET'])
def proxy_api(api_key):
    try:
        api_config = SYSTEM_APIS.get(api_key)
        if not api_config: return jsonify({"error": "Unknown API"}), 400
        
        # 統一使用 POST 獲取系統選項
        response = requests.post(api_config["url"], headers=system_headers, json={})
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "System API Failed", "details": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- 主要生成邏輯 (Step 7) ---
@app.route('/generate_ilos', methods=['POST'])
def generate_ilos():
    # 1. 接收前端資料
    data = request.json
    
    # [修正 3] 加入 Debug Print，請看你的 Terminal 視窗確認資料
    print("=======================================")
    print("【DEBUG】後端收到前端資料：")
    print(json.dumps(data, indent=4, ensure_ascii=False))
    print("=======================================")

    topic = data.get('topic', 'N/A')
    description = data.get('description', 'N/A')
    subject = data.get('subject', 'N/A')
    grade = data.get('grade', 'N/A')
    bt_level = data.get('bt_level', 'Understanding') # User 選的層次
    verb = data.get('verb', 'explain')               # User 選的動詞

    # 獲取 Categories (這部分讓 AI 自動判斷，或從系統抓取)
    try:
        cat_api = SYSTEM_APIS["ILO_get_category"]
        cat_response = requests.post(cat_api["url"], headers=system_headers, json={})
        valid_categories = ["Knowledge", "Skills", "Values and Attitudes"]
        if cat_response.status_code == 200:
            valid_categories = [item['name'] for item in cat_response.json()]
    except:
        valid_categories = ["Knowledge", "Skills", "Values and Attitudes"]
    
    categories_str = ", ".join(valid_categories)

    # 構建 System Prompt
    # [優化] 既然使用者已經選了 Verb，我們就強制 AI 用那個 Verb，不需要再抓整個動詞表
    system_prompt = f"""
    You are an expert curriculum developer. 
    Your task is to generate 3 Intended Learning Outcomes (ILOs) based strictly on the user's input.

    ### CONSTRAINTS ###
    1. **Category**: Must be chosen from: [{categories_str}].
    2. **Bloom's Level**: The user selected '{bt_level}'. Ensure the outcome matches this complexity.
    3. **Verb**: The user explicitly selected '{verb}'. **You MUST start every ILO statement with the word '{verb}'**.

    ### OUTPUT FORMAT (Strict JSON) ###
    Return a LIST of objects.
    Example:
    [
        {{
            "category": "{valid_categories[0]}", 
            "bt_level": "{bt_level}",
            "verb": "{verb}",
            "statement": "{verb} the importance of..."
        }}
    ]
    """
    
    user_prompt = f"""
    Context:
    - Course Name: {topic}
    - Description: {description}
    - Subject: {subject}
    - Grade: {grade}
    
    Task: Create 3 variations of ILOs using the verb '{verb}' (Cognitive Level: {bt_level}).
    Make sure the content is relevant to the Course Description provided.
    """

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(OPENAI_ENDPOINT, headers=openai_headers, json=payload)
        if response.status_code == 200:
            ai_data = response.json()
            raw_content = ai_data['choices'][0]['message']['content']
            # 清理 Markdown
            clean_content = raw_content.replace("```json", "").replace("```", "").strip()
            try:
                parsed_ilos = json.loads(clean_content)
                return jsonify(parsed_ilos)
            except json.JSONDecodeError:
                return jsonify({"error": "AI format error", "raw": raw_content})
        else:
            return jsonify({"error": f"OpenAI Error: {response.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # 重啟伺服器後，請注意看終端機的 Output
    app.run(debug=True, port=5000)