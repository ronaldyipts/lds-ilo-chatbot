import json
import os
import requests

SYSTEM_TOKEN = os.getenv("LDS_TOKEN")
LARAVEL_HOST_API = "https://lds.cite.hku.hk/api"

SYSTEM_APIS = {
    "get_subjects":      f"{LARAVEL_HOST_API}/chatbot/options/courses/subjects",
    "get_grade_levels":  f"{LARAVEL_HOST_API}/chatbot/options/courses/grade-levels",
    "ILO_get_bt_levels": f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/bloom-taxonomy-levels",
    "ILO_get_bt_verbs":  f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/bloom-taxonomy-verbs",
    "ILO_get_category":  f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/types"
}

system_headers = {
    "Authorization": f"Bearer {SYSTEM_TOKEN}",
    "Content-Type": "application/json"
}

def handler(request):
    key = request.query.get("api")

    if key not in SYSTEM_APIS:
        return {"statusCode": 400, "body": json.dumps({"error": "Unknown API"})}

    r = requests.post(SYSTEM_APIS[key], headers=system_headers, json={})
    return {"statusCode": r.status_code, "body": r.text}