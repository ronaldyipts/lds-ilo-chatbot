from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)

# ================= 配置區 =================
HKU_API_KEY = "87c447b07aa84539881d2c4e76267f2c" 
API_VERSION = "2025-01-01-preview"
DEPLOYMENT_ID = "gpt-4.1" 
OPENAI_ENDPOINT = f"https://api.hku.hk/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview"

SYSTEM_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI3IiwianRpIjoiYjVhOTM4NWM1NzRmMmM3Y2VlYmYzYWJhYjkyMGViNzVmNjE3YWE3NDNjNTQ1OWU1NzgxOTZmYTJmMGUwNzg5YzZkNzY1YzRkYTNhNDFmMzAiLCJpYXQiOjE3NjUxNzkzODkuMDkxNzY3LCJuYmYiOjE3NjUxNzkzODkuMDkxNzcsImV4cCI6MTc2NjA0MzM4OS4wODQ4NDksInN1YiI6IiIsInNjb3BlcyI6WyJjaGF0Ym90Il19.b42PAsu3iRQZcDaFfsoYVsBphfBVcnGY6B_2_TA582uBOcQfWl1pcLb2-IqP4oEwOFbvpvV9YI9KFiVzR2ldFatlSbdAHw0twZp5GzfCP8-Kez6Bx5_3YvxwQ7b_eVoqhkd5oDBLjWBGlxiXVH3-Y24tGnbfTlCPc0a3iOdWZ091qM6UlXM-PjkrPDSYTP1oll0tixaaKBiI_blgtNUg3XqGU2uBhFVpDu8hZzghPmkX5fl9vsbsfg50I_jwXvNU9vs-oMu63t5-YEDdYjvqhR1Rq_j7g9N3rq_apXpfWvR2qG6G3WkQHgw8D_upHZx9biLR9Z8fvxyz0Gbt3dZfXz1Qqsju9KxrdJReW432rZ-xVtx679HE9GREILjLvY6F0N7lLhQCP194vDNDMUilwC5QmGETABjbD2cJQ8XXUCDh9zF3dwrYL64AY8AtEsDtilaysTqowHRiu_Chnn-FNAU_Di4F0aTcbwNEaMCclGPvKU9J28c6JiYIIlpf-BDSO_QSvZ397BPQAaiLRXoOHLtg68_UubX0m1GcG6XelWMxpqb2MLBnWf6rXMOVimaKtB9rO_gdCE5rVNte74aHRfgFu9MtLwDYeu1fJHocTMVf9nSkvnikbVxNA_SDcR_Wu8TC70zyz-AJCfePrQD1ub7V32pzaMAA1G-w-DZfleo" 
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

@app.route('/proxy/<api_key>', methods=['GET'])
def proxy_api(api_key):
    try:
        api_config = SYSTEM_APIS.get(api_key)
        if not api_config: return jsonify({"error": "Unknown API"}), 400
        
        response = requests.post(api_config["url"], headers=system_headers, json={})
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": "System API Failed", "details": response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/generate_ilos', methods=['POST'])
def generate_ilos():
    data = request.json
    
    print("=======================================")
    print("【DEBUG】後端收到資料：")
    print(json.dumps(data, indent=4, ensure_ascii=False))
    print("=======================================")

    topic = data.get('topic', 'N/A')
    description = data.get('description', 'N/A')
    subject = data.get('subject', 'N/A')
    grade = data.get('grade', 'N/A')
    bt_level = data.get('bt_level', 'Understanding')
    verb = data.get('verb', 'explain')

    try:
        cat_api = SYSTEM_APIS["ILO_get_category"]
        cat_response = requests.post(cat_api["url"], headers=system_headers, json={})
        valid_categories = ["Knowledge", "Skills", "Values and Attitudes"]
        if cat_response.status_code == 200:
            valid_categories = [item['name'] for item in cat_response.json()]
    except:
        valid_categories = ["Knowledge", "Skills", "Values and Attitudes"]
    
    categories_str = ", ".join(valid_categories)

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
    app.run(host='0.0.0.0', port=5000, debug=True)