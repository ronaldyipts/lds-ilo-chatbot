import json
import requests
import os

HKU_API_KEY = os.getenv("HKU_API_KEY")
API_VERSION = "2025-01-01-preview"
OPENAI_ENDPOINT = "https://api.hku.hk/openai/deployments/gpt-4.1/chat/completions?api-version=2025-01-01-preview"

SYSTEM_TOKEN = os.getenv("LDS_TOKEN")
LARAVEL_HOST_API = "https://lds.cite.hku.hk/api"

CATEGORY_API = f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/types"

HEADERS_OPENAI = {
    "Content-Type": "application/json",
    "api-key": HKU_API_KEY
}

HEADERS_LDS = {
    "Authorization": f"Bearer {SYSTEM_TOKEN}",
    "Content-Type": "application/json"
}

def handler(request):
    data = request.json()

    topic = data.get('topic')
    description = data.get('description')
    subject = data.get('subject')
    grade = data.get('grade')
    bt_level = data.get('bt_level')
    verb = data.get('verb')

    # 取得 categories
    try:
        r = requests.post(CATEGORY_API, headers=HEADERS_LDS, json={})
        valid_categories = [item["name"] for item in r.json()]
    except:
        valid_categories = ["Knowledge", "Skills", "Values and Attitudes"]

    categories_str = ", ".join(valid_categories)

    system_prompt = f"""
You generate 3 ILOs.

Category must be one of [{categories_str}].
Bloom's level = {bt_level}.
Verb = {verb}. Every ILO starts with {verb}.
Return strict JSON list.
"""

    user_prompt = f"""
Course: {topic}
Description: {description}
Subject: {subject}
Grade: {grade}
Verb: {verb}
Bloom level: {bt_level}
"""

    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7
    }

    try:
        r = requests.post(OPENAI_ENDPOINT, headers=HEADERS_OPENAI, json=payload)
        raw = r.json()
        content = raw["choices"][0]["message"]["content"]
        clean = content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
        return parsed
    except Exception as e:
        return {"error": str(e)}, 500