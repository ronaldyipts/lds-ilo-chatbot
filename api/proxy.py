import json
import requests
import os

SYSTEM_TOKEN = os.getenv("LDS_TOKEN")
LARAVEL_HOST_API = "https://lds.cite.hku.hk/api"

SYSTEM_APIS = {
    "get_subjects":      f"{LARAVEL_HOST_API}/chatbot/options/courses/subjects",
    "get_grade_levels":  f"{LARAVEL_HOST_API}/chatbot/options/courses/grade-levels",
    "ILO_get_bt_levels": f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/bloom-taxonomy-levels",
    "ILO_get_bt_verbs":  f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/bloom-taxonomy-verbs",
    "ILO_get_category":  f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/types"
}

HEADERS = {
    "Authorization": f"Bearer {SYSTEM_TOKEN}",
    "Content-Type": "application/json"
}

def handler(request):
    api_key = request.query.get("api")
    if not api_key or api_key not in SYSTEM_APIS:
        return {"error": "Unknown API"}, 400

    try:
        url = SYSTEM_APIS[api_key]
        r = requests.post(url, headers=HEADERS, json={})
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500