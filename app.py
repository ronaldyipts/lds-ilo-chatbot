from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
import json
import os
import io
import tempfile
from werkzeug.utils import secure_filename

# Azure OpenAI
try:
    from openai import AzureOpenAI
    AZURE_OPENAI_AVAILABLE = True
except ImportError:
    AZURE_OPENAI_AVAILABLE = False
    print("Warning: Azure OpenAI library not available. Please install: pip install openai")

# File parsing libraries
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("Warning: PyPDF2 not available. PDF parsing will be disabled.")

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("Warning: python-docx not available. DOCX parsing will be disabled.")

app = Flask(__name__)

# =============================================================================
# CORS
# =============================================================================
# If you use Vite proxy in dev, you do NOT need CORS at all.
# Keep CORS only for non-proxy / production cross-origin deployments.
# Enable CORS by default to allow access via IP address
ENABLE_CORS = os.getenv("ENABLE_CORS", "1") == "1"
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

if ENABLE_CORS:
    # If set to "*", allow all origins (convenient for IP access)
    if "*" in ALLOWED_ORIGINS:
        CORS(
            app,
            resources={r"/api/*": {"origins": "*"}},
            allow_headers=["Content-Type", "Authorization"],
            methods=["GET", "POST", "OPTIONS"]
        )
    else:
        CORS(
            app,
            resources={r"/api/*": {"origins": ALLOWED_ORIGINS}},
            allow_headers=["Content-Type", "Authorization"],
            methods=["GET", "POST", "OPTIONS"]
        )

# =========================
# Config
# =========================
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview")
DEPLOYMENT_ID = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")

OPENAI_ENDPOINT = os.getenv("ENDPOINT_URL", "https://cite-icdevai04-openai-andy-usnc.openai.azure.com/")
# Ensure endpoint ends with /
if not OPENAI_ENDPOINT.endswith("/"):
    OPENAI_ENDPOINT += "/"

LDS_TOKEN = os.getenv("LDS_TOKEN")  # if needed
LARAVEL_HOST_API = os.getenv("LDS_BASE", "https://lds.cite.hku.hk/api")

SYSTEM_APIS = {
    "ILO_get_category": {
        "url": f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/types",
        "method": "POST"
    }
}

# Initialize Azure OpenAI client with API Key authentication
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
if not AZURE_OPENAI_API_KEY:
    raise RuntimeError("Missing AZURE_OPENAI_API_KEY env var. Please set it to your Azure OpenAI API key.")

azure_openai_client = None
if AZURE_OPENAI_AVAILABLE:
    try:
        azure_openai_client = AzureOpenAI(
            azure_endpoint=OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=API_VERSION,
        )
        print("Azure OpenAI client initialized with API key authentication")
    except Exception as e:
        print(f"Error: Failed to initialize Azure OpenAI client: {e}")
        raise
else:
    raise RuntimeError("Azure OpenAI library not available. Please install: pip install openai")

# Build LDS API authentication headers
# Laravel API may use different authentication methods, try multiple formats
lds_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Add authentication header - try multiple possible formats
if LDS_TOKEN:
    # Check if token already contains "Bearer" prefix
    token = LDS_TOKEN.strip()
    if token.startswith("Bearer "):
        # If already contains Bearer, use directly
        lds_headers["Authorization"] = token
    else:
        # Otherwise add Bearer prefix
        lds_headers["Authorization"] = f"Bearer {token}"

DP_DEFINITIONS = """
1. Engineering Design: For creating solutions, prototypes, coding, or building systems.
2. Scientific Investigation: For experiments, hypothesis testing, observing natural phenomena.
3. Mock Legislative Procedure: For debating laws, social issues, policy making, or reaching consensus.
4. Performance Production: For arts, music, drama, creative expression, or public speaking.
5. Writing a News Report: For journalism, factual reporting, investigating events, or media studies.
6. General Inquiry: Fallback for general research or theoretical topics that don't fit specific practices.
""".strip()

# =========================
# Chatbot JSON (per your design)
# =========================
REFUSAL_TEXT = (
    "抱歉，我專門協助學習設計和課程規劃。請詢問與您的課程相關的問題。"
)

LD_KEYWORDS = [
    "learning", "learn", "teaching", "curriculum", "lesson", "assessment", "rubric",
    "bloom", "taxonomy", "ilo", "learning outcome", "pedagogy", "instruction",
    "課程", "教學", "學習", "學習目標", "評量", "教案", "布魯姆", "課綱", "單元", "教材", 
    "設計", "教學設計", "課程設計", "教育", "學生", "老師", "教師"
]

# Common greetings that should be accepted
GREETINGS = [
    "你好", "您好", "hi", "hello", "hey", "早上好", "下午好", "晚上好",
    "good morning", "good afternoon", "good evening"
]


def is_in_scope(text: str) -> bool:
    t = (text or "").lower().strip()
    if not t:
        return True
    
    # If it's a greeting, accept
    if any(greeting in t for greeting in GREETINGS):
        return True
    
    # Check if it contains learning design related keywords
    return any(k in t for k in LD_KEYWORDS)


CHATBOT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "lds_chatbot_response",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "chat_message_reply": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "text": {"type": "string"}
                    },
                    "required": ["text"]
                },
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "action_type": {"type": "string"},
                            "target": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "context": {
                                        "type": "string",
                                        "enum": ["CourseInfo", "ILO", "DP", "PA", "CC", "Task", "Lesson"]
                                    },
                                    "context_object_id": {"type": "integer"}
                                },
                                "required": ["context"]
                            },
                            "payload": {"type": "object"},
                            "ui": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "presentation": {
                                        "type": "string",
                                        "enum": ["popup", "sidebar", "tooltip", "highlight", "inline"]
                                    },
                                    "highlight_target": {"type": "string"}
                                },
                                "required": []
                            }
                        },
                        "required": ["action_type", "target"]
                    }
                }
            }
        },
        "required": []  # Both chat_message_reply and actions are optional per specification
    }
}

# =========================
# Tools (Function Calling)
# =========================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ILO_get_category",
            "description": "Retrieve Intended Learning Outcomes category/types options from LDS system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "locale": {"type": "string", "description": "Language/locale, e.g., en, zh-HK"}
                },
                "required": []
            }
        }
    }
]


def call_lds_api(name: str, args: dict):
    api = SYSTEM_APIS.get(name)
    if not api:
        return {"error": f"Unknown API tool: {name}"}

    try:
        resp = requests.request(
            api["method"],
            api["url"],
            headers=lds_headers,
            json=args if args else {},
            timeout=(5, 30)
        )
        if 200 <= resp.status_code < 300:
            try:
                return resp.json()
            except Exception:
                return {"raw": resp.text}
        return {"error": f"LDS API error {resp.status_code}", "details": resp.text}
    except Exception as e:
        return {"error": str(e)}


def call_openai(payload: dict):
    """使用 Azure OpenAI client 調用 API"""
    if not azure_openai_client:
        raise RuntimeError("Azure OpenAI client not initialized. Please install: pip install openai azure-identity")
    
    try:
        # Extract parameters from payload
        messages = payload.get("messages", [])
        temperature = payload.get("temperature", 0.3)
        max_tokens = payload.get("max_tokens", 600)
        response_format = payload.get("response_format")
        tools = payload.get("tools")
        tool_choice = payload.get("tool_choice")
        
        # Build request parameters
        completion_params = {
            "model": DEPLOYMENT_ID,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            completion_params["response_format"] = response_format
        if tools:
            completion_params["tools"] = tools
        if tool_choice:
            completion_params["tool_choice"] = tool_choice
        
        # Call API
        completion = azure_openai_client.chat.completions.create(**completion_params)
        
        # Convert to response format compatible with original format
        choice = completion.choices[0]
        result = {
            "choices": [{
                "message": {
                    "content": choice.message.content,
                    "tool_calls": [{
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in (choice.message.tool_calls or [])]
                }
            }]
        }
        return result
    except Exception as e:
        raise RuntimeError(f"Azure OpenAI error: {str(e)}")


def run_chat_with_optional_tools(
    messages,
    temperature=0.3,
    max_tokens=600,
    response_format=None,
    tools=None,
):
    """
    Safer 2-stage strategy:
      - Stage 1: allow tool calling WITHOUT forcing response_format (more compatible)
      - Stage 2: after tool results, enforce response_format (schema) for final output
    Also provides fallback when json_schema isn't supported.
    """

    # -------------------------
    # Stage 1 (tools allowed)
    # -------------------------
    payload1 = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload1["tools"] = tools
        payload1["tool_choice"] = "auto"

    data1 = call_openai(payload1)
    msg1 = data1["choices"][0].get("message", {})
    tool_calls = msg1.get("tool_calls", []) if tools else []

    # If no tools requested, try to enforce schema directly (with fallback)
    if not tool_calls:
        if response_format:
            try:
                payload_schema = dict(payload1)
                payload_schema["response_format"] = response_format
                data_schema = call_openai(payload_schema)
                return data_schema["choices"][0]["message"]
            except Exception:
                # Fallback
                payload_fallback = dict(payload1)
                payload_fallback["response_format"] = {"type": "json_object"}
                data_fb = call_openai(payload_fallback)
                return data_fb["choices"][0]["message"]
        return msg1

    # -------------------------
    # Execute tools
    # -------------------------
    tool_messages = []
    for tc in tool_calls:
        fn = tc["function"]["name"]
        args_str = tc["function"].get("arguments", "{}")
        try:
            args = json.loads(args_str) if args_str else {}
        except json.JSONDecodeError:
            args = {}

        result = call_lds_api(fn, args)
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": json.dumps(result, ensure_ascii=False),
        })

    # -------------------------
    # Stage 2 (final answer in schema)
    # -------------------------
    messages2 = messages + [msg1] + tool_messages
    payload2 = {
        "messages": messages2,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if response_format:
        try:
            payload2["response_format"] = response_format
            data2 = call_openai(payload2)
            return data2["choices"][0]["message"]
        except Exception:
            payload2["response_format"] = {"type": "json_object"}
            data2 = call_openai(payload2)
            return data2["choices"][0]["message"]

    data2 = call_openai(payload2)
    return data2["choices"][0]["message"]


# =========================
# Routes
# =========================
@app.route("/")
def home():
    """
    Simple health-check endpoint.
    In Vite development mode, frontend runs on http://localhost:5173,
    Flask does not need to render index.html, otherwise it will 500 due to missing templates directory.
    """
    return jsonify({"status": "ok", "message": "LDS Chatbot backend is running."})


@app.route("/api/health", methods=["GET"])
def health_check():
    """
    Check backend configuration and LDS API connection status
    """
    health_info = {
        "status": "ok",
        "backend": "running",
        "config": {
            "LARAVEL_HOST_API": LARAVEL_HOST_API,
            "LDS_TOKEN_set": bool(LDS_TOKEN),
            "AZURE_OPENAI_CLIENT_AVAILABLE": bool(azure_openai_client)
        }
    }
    
    # Test LDS API connection
    try:
        test_url = f"{LARAVEL_HOST_API}/chatbot/options/courses/subjects"
        test_resp = requests.post(
            test_url,
            headers=lds_headers,
            json={"locale": "zh_HK"},
            timeout=(5, 10)
        )
        health_info["lds_api"] = {
            "status": "connected" if 200 <= test_resp.status_code < 300 else "error",
            "status_code": test_resp.status_code,
            "url": test_url
        }
    except Exception as e:
        health_info["lds_api"] = {
            "status": "error",
            "error": str(e),
            "type": type(e).__name__
        }
    
    return jsonify(health_info)


@app.route("/api/ilo-categories", methods=["GET", "POST", "OPTIONS"])
def get_ilo_categories():
    """
    Get ILO Categories list from LDS API
    """
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        # 取得語言參數（預設 zh_HK）
        if request.method == "POST":
            data = request.json or {}
            locale = data.get("locale") or request.args.get("locale", "zh_HK")
        else:
            locale = request.args.get("locale", "zh_HK")
        
        # 呼叫 LDS API
        categories_url = f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/types"
        
        request_data = {}
        if locale:
            request_data["locale"] = locale
        
        app.logger.info(f"Calling LDS API: {categories_url} with method: POST, data: {request_data}")
        
        resp = requests.post(
            categories_url,
            headers=lds_headers,
            json=request_data if request_data else {},
            timeout=(5, 30)
        )
        
        app.logger.info(f"LDS API response status: {resp.status_code}")
        
        if 200 <= resp.status_code < 300:
            try:
                categories_data = resp.json()
                if isinstance(categories_data, list):
                    app.logger.info(f"Successfully loaded {len(categories_data)} ILO categories")
                    return jsonify(categories_data)
                else:
                    app.logger.warning(f"LDS API returned non-list data: {type(categories_data)}")
                    return jsonify({"error": "LDS API returned invalid data format", "data": categories_data}), 500
            except json.JSONDecodeError as e:
                app.logger.error(f"Failed to parse JSON response: {e}, raw: {resp.text[:200]}")
                # Ensure valid JSON is returned even if LDS API returns HTML or other formats
                return jsonify({
                    "error": "Invalid JSON response from LDS API",
                    "details": f"LDS API returned non-JSON content. Status: {resp.status_code}",
                    "raw_preview": resp.text[:200] if resp.text else "No response body"
                }), 500
        else:
            error_text = resp.text[:500] if resp.text else "No response body"
            app.logger.error(f"LDS API error {resp.status_code}: {error_text}")
            return jsonify({
                "error": f"LDS API error {resp.status_code}",
                "details": error_text,
                "url": categories_url
            }), resp.status_code
            
    except requests.exceptions.Timeout:
        app.logger.error("LDS API request timeout")
        return jsonify({"error": "Request to LDS API timed out"}), 504
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"LDS API connection error: {e}")
        return jsonify({"error": f"Failed to connect to LDS API: {str(e)}"}), 503
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


@app.route("/api/chatbot/patterns/intended-learning-outcomes", methods=["POST", "OPTIONS"])
def get_ilo_patterns():
    """
    Get ILO Patterns list from LDS API
    """
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        # Call LDS API
        patterns_url = f"{LARAVEL_HOST_API}/chatbot/patterns/intended-learning-outcomes"
        
        # Get request parameters (if any)
        request_data = request.json or {}
        
        app.logger.info(f"Calling LDS API: {patterns_url} with method: POST")
        
        resp = requests.post(
            patterns_url,
            headers=lds_headers,
            json=request_data if request_data else {},
            timeout=(5, 30)
        )
        
        app.logger.info(f"LDS API response status: {resp.status_code}")
        
        if 200 <= resp.status_code < 300:
            try:
                data = resp.json()
                app.logger.info(f"Successfully retrieved ILO patterns, count: {len(data) if isinstance(data, list) else 'N/A'}")
                return jsonify(data)
            except ValueError as e:
                app.logger.error(f"Failed to parse JSON response: {e}")
                app.logger.error(f"Response text: {resp.text[:500]}")
                return jsonify({"error": "無法解析 LDS API 回應", "details": str(e)}), 500
        else:
            error_text = resp.text[:500] if resp.text else "No error message"
            app.logger.error(f"LDS API error: HTTP {resp.status_code}, {error_text}")
            try:
                error_data = resp.json()
                return jsonify({"error": error_data.get("message", f"HTTP {resp.status_code}"), "details": error_data}), resp.status_code
            except:
                return jsonify({"error": f"HTTP {resp.status_code}", "details": error_text}), resp.status_code
    
    except requests.exceptions.Timeout:
        app.logger.error("LDS API timeout")
        return jsonify({"error": "LDS API 請求超時", "details": "請稍後再試"}), 504
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"LDS API connection error: {e}")
        return jsonify({"error": "無法連接到 LDS API", "details": str(e)}), 503
    except Exception as e:
        app.logger.error(f"Unexpected error in get_ilo_patterns: {e}", exc_info=True)
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


@app.route("/api/bloom-taxonomy-levels", methods=["GET", "POST", "OPTIONS"])
def get_bloom_taxonomy_levels():
    """
    Get Bloom Taxonomy Levels list from LDS API
    """
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        # 取得語言參數（預設 zh_HK）
        if request.method == "POST":
            data = request.json or {}
            locale = data.get("locale") or request.args.get("locale", "zh_HK")
        else:
            locale = request.args.get("locale", "zh_HK")
        
        # 呼叫 LDS API
        bloom_url = f"{LARAVEL_HOST_API}/chatbot/options/intended-learning-outcomes/bloom-taxonomy-levels"
        
        request_data = {}
        if locale:
            request_data["locale"] = locale
        
        app.logger.info(f"Calling LDS API: {bloom_url} with method: POST, data: {request_data}")
        
        resp = requests.post(
            bloom_url,
            headers=lds_headers,
            json=request_data if request_data else {},
            timeout=(5, 30)
        )
        
        app.logger.info(f"LDS API response status: {resp.status_code}")
        
        if 200 <= resp.status_code < 300:
            try:
                bloom_data = resp.json()
                if isinstance(bloom_data, list):
                    app.logger.info(f"Successfully loaded {len(bloom_data)} bloom taxonomy levels")
                    return jsonify(bloom_data)
                else:
                    app.logger.warning(f"LDS API returned non-list data: {type(bloom_data)}")
                    return jsonify({"error": "LDS API returned invalid data format", "data": bloom_data}), 500
            except json.JSONDecodeError as e:
                app.logger.error(f"Failed to parse JSON response: {e}, raw: {resp.text[:200]}")
                # Ensure valid JSON is returned even if LDS API returns HTML or other formats
                return jsonify({
                    "error": "Invalid JSON response from LDS API",
                    "details": f"LDS API returned non-JSON content. Status: {resp.status_code}",
                    "raw_preview": resp.text[:200] if resp.text else "No response body"
                }), 500
        else:
            error_text = resp.text[:500] if resp.text else "No response body"
            app.logger.error(f"LDS API error {resp.status_code}: {error_text}")
            return jsonify({
                "error": f"LDS API error {resp.status_code}",
                "details": error_text,
                "url": bloom_url
            }), resp.status_code
            
    except requests.exceptions.Timeout:
        app.logger.error("LDS API request timeout")
        return jsonify({"error": "Request to LDS API timed out"}), 504
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"LDS API connection error: {e}")
        return jsonify({"error": f"Failed to connect to LDS API: {str(e)}"}), 503
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


@app.route("/api/grade-levels", methods=["GET", "POST", "OPTIONS"])
def get_grade_levels():
    """
    Get grade levels list from LDS API
    """
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        # 取得語言參數（預設 zh_HK）
        if request.method == "POST":
            data = request.json or {}
            locale = data.get("locale") or request.args.get("locale", "zh_HK")
        else:
            locale = request.args.get("locale", "zh_HK")
        
        # 呼叫 LDS API
        grade_levels_url = f"{LARAVEL_HOST_API}/chatbot/options/courses/grade-levels"
        
        # 準備請求 body
        request_data = {}
        if locale:
            request_data["locale"] = locale
        
        app.logger.info(f"Calling LDS API: {grade_levels_url} with method: POST, data: {request_data}")
        
        resp = requests.post(
            grade_levels_url,
            headers=lds_headers,
            json=request_data if request_data else {},
            timeout=(5, 30)
        )
        
        app.logger.info(f"LDS API response status: {resp.status_code}")
        
        if 200 <= resp.status_code < 300:
            try:
                grade_levels_data = resp.json()
                if isinstance(grade_levels_data, list):
                    app.logger.info(f"Successfully loaded {len(grade_levels_data)} grade levels")
                    return jsonify(grade_levels_data)
                else:
                    app.logger.warning(f"LDS API returned non-list data: {type(grade_levels_data)}")
                    return jsonify({"error": "LDS API returned invalid data format", "data": grade_levels_data}), 500
            except json.JSONDecodeError as e:
                app.logger.error(f"Failed to parse JSON response: {e}, raw: {resp.text[:200]}")
                # Ensure valid JSON is returned even if LDS API returns HTML or other formats
                return jsonify({
                    "error": "Invalid JSON response from LDS API",
                    "details": f"LDS API returned non-JSON content. Status: {resp.status_code}",
                    "raw_preview": resp.text[:200] if resp.text else "No response body"
                }), 500
        else:
            error_text = resp.text[:500] if resp.text else "No response body"
            app.logger.error(f"LDS API error {resp.status_code}: {error_text}")
            return jsonify({
                "error": f"LDS API error {resp.status_code}",
                "details": error_text,
                "url": grade_levels_url
            }), resp.status_code
            
    except requests.exceptions.Timeout:
        app.logger.error("LDS API request timeout")
        return jsonify({"error": "Request to LDS API timed out"}), 504
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"LDS API connection error: {e}")
        return jsonify({"error": f"Failed to connect to LDS API: {str(e)}"}), 503
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


@app.route("/api/subjects", methods=["GET", "POST", "OPTIONS"])
def get_subjects():
    """
    Get subjects list from LDS API
    Note: LDS API may require POST method (similar to ILO_get_category)
    """
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        # Get language parameter (default zh_HK)
        # Support getting from query string (GET) or request body (POST)
        if request.method == "POST":
            data = request.json or {}
            locale = data.get("locale") or request.args.get("locale", "zh_HK")
        else:
            locale = request.args.get("locale", "zh_HK")
        
        # 呼叫 LDS API
        subjects_url = f"{LARAVEL_HOST_API}/chatbot/options/courses/subjects"
        
        # Prepare request body (POST) or params (GET)
        request_data = {}
        if locale:
            request_data["locale"] = locale
        
        # Log request information (for debugging)
        app.logger.info(f"=== Calling LDS API: {subjects_url} ===")
        app.logger.info(f"Method: POST")
        app.logger.info(f"Request data: {request_data}")
        app.logger.info(f"Request headers: {list(lds_headers.keys())}")
        app.logger.info(f"LDS_TOKEN set: {bool(LDS_TOKEN)}")
        if LDS_TOKEN:
            # Only log first few characters of token, not full token (security consideration)
            app.logger.info(f"LDS_TOKEN preview: {LDS_TOKEN[:10]}... (length: {len(LDS_TOKEN)})")
            if "Authorization" in lds_headers:
                auth_header = lds_headers["Authorization"]
                app.logger.info(f"Authorization header format: {auth_header[:30]}... (length: {len(auth_header)})")
        app.logger.info(f"LARAVEL_HOST_API: {LARAVEL_HOST_API}")
        
        # Try using POST (because other chatbot/options endpoints use POST)
        resp = requests.post(
            subjects_url,
            headers=lds_headers,
            json=request_data if request_data else {},
            timeout=(5, 30)
        )
        
        app.logger.info(f"LDS API response status: {resp.status_code}")
        
        if 200 <= resp.status_code < 300:
            try:
                subjects_data = resp.json()
                # Ensure returned data is an array
                if isinstance(subjects_data, list):
                    app.logger.info(f"Successfully loaded {len(subjects_data)} subjects")
                    return jsonify(subjects_data)
                else:
                    app.logger.warning(f"LDS API returned non-list data: {type(subjects_data)}, data: {subjects_data}")
                    return jsonify({
                        "error": "LDS API returned invalid data format", 
                        "data": subjects_data,
                        "expected": "array",
                        "received": type(subjects_data).__name__
                    }), 500
            except json.JSONDecodeError as e:
                app.logger.error(f"Failed to parse JSON response: {e}, raw: {resp.text[:200]}")
                # Ensure valid JSON is returned even if LDS API returns HTML or other formats
                return jsonify({
                    "error": "Invalid JSON response from LDS API",
                    "details": f"LDS API returned non-JSON content. Status: {resp.status_code}",
                    "raw_preview": resp.text[:200] if resp.text else "No response body",
                    "url": subjects_url
                }), 500
        else:
            error_text = resp.text[:500] if resp.text else "No response body"
            app.logger.error(f"LDS API error {resp.status_code}: {error_text}")
            app.logger.error(f"Request URL: {subjects_url}")
            app.logger.error(f"Request headers: {list(lds_headers.keys())}")
            app.logger.error(f"LDS_TOKEN set: {bool(LDS_TOKEN)}")
            if LDS_TOKEN:
                app.logger.error(f"LDS_TOKEN preview: {LDS_TOKEN[:10]}... (length: {len(LDS_TOKEN)})")
                if "Authorization" in lds_headers:
                    auth_header = lds_headers["Authorization"]
                    app.logger.error(f"Authorization header sent: {auth_header[:50]}...")
            
            # If 401, provide more detailed error message
            if resp.status_code == 401:
                app.logger.error("⚠️ 認證失敗 (401 Unauthenticated)")
                app.logger.error("可能的原因：")
                app.logger.error("  1. LDS_TOKEN 已過期或無效")
                app.logger.error("  2. LDS_TOKEN 格式不正確（可能需要不同的格式）")
                app.logger.error("  3. LDS API 需要不同的認證方式（例如：不使用 Bearer 前綴）")
                app.logger.error("  4. 請檢查 LDS_TOKEN 環境變數是否正確設置")
            
            return jsonify({
                "error": f"LDS API error {resp.status_code}",
                "details": error_text,
                "url": subjects_url,
                "status_code": resp.status_code,
                "auth_issue": resp.status_code == 401
            }), resp.status_code
            
    except requests.exceptions.Timeout:
        app.logger.error("LDS API request timeout")
        return jsonify({"error": "Request to LDS API timed out"}), 504
    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"LDS API connection error: {e}")
        return jsonify({"error": f"Failed to connect to LDS API: {str(e)}"}), 503
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


def generate_suggested_questions(user_message, bot_reply, conversation_history):
    """
    Generate 3 suggestions to help users know how to continue the conversation with the chatbot
    These suggestions are presented in the user's tone when speaking to the chatbot (e.g., "I want to understand...", "My goal is...")
    These suggestions are not restricted by the system prompt because they are suggested by the bot
    Generate relevant suggestions based on the bot's response content
    """
    try:
        # Build conversation context summary
        context_summary = ""
        if conversation_history:
            # Get recent 3 rounds of conversation (user and bot)
            recent_messages = conversation_history[-6:] if len(conversation_history) >= 6 else conversation_history
            context_parts = []
            for msg in recent_messages:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if content:
                    context_parts.append(f"{'用戶' if role == 'user' else '機器人'}: {content[:100]}")
            if context_parts:
                context_summary = "\n".join(context_parts[-4:])  # Only take the most recent 4
        
        # Analyze bot response content type
        bot_reply_lower = bot_reply.lower()
        is_guiding = any(keyword in bot_reply_lower for keyword in ["希望", "您想", "可以", "建議", "例如", "什麼"])
        is_providing_suggestions = any(keyword in bot_reply_lower for keyword in ["學習目標", "教學活動", "評量", "建議", "可以"])
        is_asking_question = "?" in bot_reply or "？" in bot_reply
        
        # Build more detailed prompt
        prompt = f"""你是一個教學設計助手，需要根據機器人的回應生成3個建議，幫助使用者知道如何繼續與聊天機器人對話。

**當前對話：**
使用者剛才說：{user_message[:150]}

機器人回應：
{bot_reply[:400]}

**對話歷史：**
{context_summary if context_summary else "這是對話的開始"}

**任務：**
根據機器人的回應內容，生成3個簡短、具體的建議（每個不超過25字）。這些建議應該：
1. 以「使用者對聊天機器人說話」的語氣呈現（例如：「我想了解...」、「我的目標是...」、「我考慮...」）
2. 不是直接的問題，而是使用者可以對聊天機器人說的話
3. 與機器人回應的內容直接相關，幫助使用者知道如何繼續對話
4. 如果是引導性回應，建議應該幫助使用者明確表達需求
5. 如果是提供建議的回應，建議應該幫助使用者細化或調整
6. 建議應該具體、可操作，避免過於抽象
7. 使用繁體中文

**回應類型分析：**
- 機器人是否在引導思考：{'是' if is_guiding else '否'}
- 機器人是否提供建議：{'是' if is_providing_suggestions else '否'}
- 機器人是否在提問：{'是' if is_asking_question else '否'}

**範例：**
- 好的建議：「我想了解目標應該偏重知識還是技能」、「我的課程希望涵蓋數學領域」、「我考慮使用專題報告作為評量方式」
- 不好的建議：「請問您的目標偏重知識還是技能？」（這是問題，不是使用者說的話）

請以 JSON 格式返回，格式如下：
{{"questions": ["建議1（使用者可以說的話）", "建議2（使用者可以說的話）", "建議3（使用者可以說的話）"]}}

只返回 JSON，不要其他文字。"""
        
        messages = [
            {
                "role": "system", 
                "content": "你是一個教學設計助手，專門生成建議，幫助使用者知道如何繼續與聊天機器人對話。你必須返回有效的 JSON 格式，包含 'questions' 字段，值為包含3個建議的數組。每個建議應該：1) 以使用者對聊天機器人說話的語氣呈現（例如「我想了解...」、「我的目標是...」），2) 不是直接的問題，而是使用者可以說的話，3) 簡短（不超過25字）、具體、可操作。"
            },
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "messages": messages,
            "temperature": 0.8,  # Slightly increase temperature for more diverse questions
            "max_tokens": 200,  # Increase token limit for better questions
            "response_format": {"type": "json_object"}
        }
        
        # Use Azure OpenAI client
        if not azure_openai_client:
            # If client not initialized, return default questions
            return [
                "我想進一步細化這些學習目標",
                "我想了解如何設計對應的教學活動",
                "我想知道需要考慮哪些評量方式"
            ]
        
        try:
            completion = azure_openai_client.chat.completions.create(
                model=DEPLOYMENT_ID,
                messages=messages,
                temperature=0.8,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            content = completion.choices[0].message.content
            
            try:
                # Try to parse JSON
                parsed = json.loads(content)
                # May be {"questions": [...]} or directly an array
                if isinstance(parsed, dict):
                    questions = parsed.get("questions", parsed.get("suggested_questions", []))
                elif isinstance(parsed, list):
                    questions = parsed
                else:
                    questions = []
                
                # Ensure 3 questions are returned
                if isinstance(questions, list) and len(questions) >= 3:
                    return questions[:3]
                elif isinstance(questions, list) and len(questions) > 0:
                    # If less than 3, pad
                    while len(questions) < 3:
                        questions.append("")
                    return questions[:3]
            except:
                # If parsing fails, try to extract from text
                import re
                questions = re.findall(r'["\']([^"\']+)["\']', content)
                if len(questions) >= 3:
                    return questions[:3]
        except Exception as e:
            app.logger.error(f"Error calling Azure OpenAI for suggested questions: {e}")
            # Return default suggestions
            return [
                "我想進一步細化這些學習目標",
                "我想了解如何設計對應的教學活動",
                "我想知道需要考慮哪些評量方式"
            ]
        
        # If generation fails, return default suggestions (in user's tone)
        return [
            "我想進一步細化這些學習目標",
            "我想了解如何設計對應的教學活動",
            "我想知道需要考慮哪些評量方式"
        ]
    except Exception as e:
        app.logger.error(f"Error generating suggested questions: {e}")
        # 返回默認建議（以用戶語氣）
        return [
            "我想進一步細化這些學習目標",
            "我想了解如何設計對應的教學活動",
            "我想知道需要考慮哪些評量方式"
        ]


@app.route("/api/chat", methods=["POST", "OPTIONS"])
def chat_general():
    """
    Returns:
    {
      "chat_message_reply": {"text": "..."},
      "actions": [...]
    }
    """
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.json or {}
    user_msg = (data.get("message") or "").strip()
    
    # If it's a BOT-suggested question, skip scope check and accept directly
    is_suggested_question = data.get("is_suggested_question", False)
    
    if not is_suggested_question and not is_in_scope(user_msg):
        return jsonify({"chat_message_reply": {"text": REFUSAL_TEXT}, "actions": []})

    # Optional context
    topic = (data.get("topic") or "").strip()
    grade = (data.get("grade") or "").strip()
    dp = (data.get("dp") or "").strip()
    pa = (data.get("pa") or "").strip()

    context_lines = []
    if topic:
        context_lines.append(f"Topic: {topic}")
    if grade:
        context_lines.append(f"Grade: {grade}")
    if dp:
        context_lines.append(f"DP: {dp}")
    if pa:
        context_lines.append(f"PA: {pa}")
    context_block = ("\n".join(context_lines) + "\n\n") if context_lines else ""

    # Socratic Nudge Engine: detect user intent
    # Only provide direct answers when user explicitly requests "don't ask", "give direct answer", etc.
    # Other cases (including "give me", "help me write", etc.) should use Socratic guidance
    explicit_direct_answer_keywords = ["不要問了", "直接給答案", "直接寫", "不要引導", "直接回答", "別問了", "直接提供"]
    user_wants_direct_answer = any(keyword in user_msg for keyword in explicit_direct_answer_keywords)
    
    # Get conversation history (if any)
    conversation_history = data.get("conversation_history", [])
    last_user_response_length = 0
    conversation_rounds = 0  # Number of conversation rounds
    user_has_provided_details = False  # Whether user has provided detailed information
    
    if conversation_history:
        # Count conversation rounds and user response detail level
        user_messages = [msg for msg in conversation_history if msg.get("role") == "user"]
        conversation_rounds = len(user_messages)
        
        # Get last user response length and content
        if user_messages:
            last_user_msg = user_messages[-1].get("content", "")
            last_user_response_length = len(last_user_msg)
            
            # Detect if user has provided sufficient detailed information
            # Key indicators:
            # 1. Response length exceeds 50 characters
            # 2. Contains specific teaching elements (e.g., grade, subject, topic, Bloom level, etc.)
            detail_keywords = ["年級", "科目", "主題", "學生", "課程", "單元", "記憶", "理解", "應用", "分析", "評估", "創造", 
                             "bloom", "taxonomy", "評量", "活動", "目標", "學習"]
            has_detail_keywords = any(keyword in last_user_msg.lower() for keyword in detail_keywords)
            
            # If response exceeds 50 characters and contains keywords, or response exceeds 100 characters, consider sufficient information provided
            if (last_user_response_length > 50 and has_detail_keywords) or last_user_response_length > 100:
                user_has_provided_details = True
            
            # If conversation has been 3+ rounds and last response exceeds 30 characters, also consider information sufficient
            if conversation_rounds >= 3 and last_user_response_length > 30:
                user_has_provided_details = True
    
    # Dynamic scaffolding: judge confusion level based on response brevity
    # Response less than 10 characters = high confusion, need more detailed guidance
    # Response 10-30 characters = medium confusion, need medium guidance
    # Response more than 30 characters = low confusion, can provide concise guidance
    if last_user_response_length < 10:
        scaffolding_level = "high"  # High scaffolding: provide very detailed guidance
    elif last_user_response_length < 30:
        scaffolding_level = "medium"  # Medium scaffolding: provide medium detailed guidance
    else:
        scaffolding_level = "low"  # Low scaffolding: provide concise guidance
    
    # Build Socratic guidance system prompt
    socratic_instruction = ""
    if not user_wants_direct_answer:
        # Determine if should switch to suggestion mode
        should_provide_suggestion = user_has_provided_details
        
        if should_provide_suggestion:
            # User has provided sufficient information, provide suggestions directly
            socratic_instruction = (
                "\n\n【智能判斷：提供建議模式】\n"
                "使用者已經提供了足夠的教學需求信息（包括年級、科目、主題、學習目標類型等）。\n"
                "現在應該直接提供具體的學習目標建議或範例，而不是繼續引導。\n"
                "1. 根據使用者提供的信息，生成具體的學習目標（ILO）\n"
                "2. 可以按照不同類別（學科知識、學科技能、共通能力、價值觀與態度）提供建議\n"
                "3. 確保學習目標清晰、可測量、符合 Bloom's Taxonomy\n"
                "4. 提供後可以詢問是否需要進一步細化或調整\n"
            )
        else:
            # Continue using Socratic guidance
            socratic_instruction = (
                "\n\n【重要：蘇格拉底式引導原則】\n"
                "你是一位採用蘇格拉底式教學法的教育者。你的目標不是直接給答案，而是通過反問來引導使用者思考。\n"
                "1. 當使用者提出問題時，不要直接回答，而是反問引導性問題。\n"
                "2. 例如：當使用者問「幫我寫一個教學目標」時，不要直接寫，而是反問：「您希望學生在課後能展現什麼具體行為？是『記憶』還是『應用』？」\n"
                "3. 根據使用者的回答簡短程度調整引導細緻度：\n"
            )
            
            if scaffolding_level == "high":
                socratic_instruction += (
                    "   - 使用者回答很簡短（少於10字），表示可能很迷惘，需要提供非常詳細的引導：\n"
                    "     提供多個具體選項、舉例說明、分步驟引導。\n"
                )
            elif scaffolding_level == "medium":
                socratic_instruction += (
                    "   - 使用者回答中等長度（10-30字），提供中等詳細的引導：\n"
                    "     提供2-3個選項，簡要說明。\n"
                )
            else:
                socratic_instruction += (
                    "   - 使用者回答較長（超過30字），表示有一定理解，提供簡潔的引導：\n"
                    "     提出1-2個關鍵問題即可。\n"
                )
            
            socratic_instruction += (
                "4. 即使使用者說「給我」、「幫我寫」等，也要先引導思考，不要直接給答案。\n"
                "5. 只有在使用者明確要求「直接給答案」、「直接寫」、「不要問了」、「別問了」等情況下，才提供直接答案。\n"
                "6. 引導問題應該具體、有針對性，幫助使用者思考學習設計的核心要素。\n"
                "7. 【重要】當使用者已經提供了足夠的詳細信息（如：年級、科目、主題、學習目標類型等），且回答超過50字或對話已進行3輪以上時，應該直接提供具體的學習目標建議，而不是繼續引導。\n"
            )
    else:
        socratic_instruction = (
            "\n\n【注意】\n"
            "使用者明確要求直接答案（說了「不要問了」、「直接給答案」等），可以提供具體的建議或範例。"
        )
    
    system_msg = (
        "你是一位專業的學習設計助手，專門協助教師進行課程規劃和教學設計。"
        "請用中文回答，提供專業、實用、詳細的建議。"
        "必須返回符合 JSON schema 格式的回應，包含 chat_message_reply.text 欄位。"
        "即使是不確定的問題，也要提供有用的回應，不要返回空內容。"
        "請確保回應完整、詳細且深入，不要中途截斷。"
        "如果回應較長，請確保所有要點都已完整表達，並提供具體的範例和說明。"
        "回應應該充分、詳細，涵蓋所有相關的方面，幫助用戶深入理解。"
        + socratic_instruction
    )
    
    # Build conversation history (if any)
    messages = [{"role": "system", "content": system_msg}]
    
    # Add conversation history (most recent 5 rounds, avoid too long)
    if conversation_history:
        recent_history = conversation_history[-5:]  # Only take most recent 5 rounds
        for msg in recent_history:
            role = msg.get("role")
            content = msg.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})
    
    # Add current user message
    messages.append({"role": "user", "content": context_block + user_msg})

    try:
        msg = run_chat_with_optional_tools(
            messages,
            temperature=0.3,
            max_tokens=3000,  # Increase token limit to support more detailed and complete responses
            response_format=CHATBOT_SCHEMA,
            tools=TOOLS,
        )

        content = msg.get("content", "{}")

        # Robust parse + repair
        try:
            obj = json.loads(content) if content else {}
        except Exception:
            obj = {}

        # Ensure chat_message_reply exists (optional per spec, but we provide default for compatibility)
        if "chat_message_reply" not in obj or not isinstance(obj["chat_message_reply"], dict):
            obj["chat_message_reply"] = {"text": ""}
        if "text" not in obj["chat_message_reply"]:
            obj["chat_message_reply"]["text"] = ""
        
        # If response is empty, provide default response
        if not obj["chat_message_reply"]["text"] or obj["chat_message_reply"]["text"].strip() == "":
            # Provide default response based on user message
            user_msg_lower = user_msg.lower()
            if any(g in user_msg_lower for g in ["你好", "hello", "hi", "您好"]):
                obj["chat_message_reply"]["text"] = "你好！我是學習設計助手，可以協助您進行課程規劃、教學設計、學習目標制定等。請告訴我您需要什麼幫助？"
            elif any(k in user_msg_lower for k in ["教學設計", "課程設計", "設計", "如何"]):
                obj["chat_message_reply"]["text"] = "關於教學設計，我可以協助您：\n1. 制定學習目標（ILO）\n2. 設計教學活動\n3. 規劃評量方式\n4. 應用 Bloom's Taxonomy\n\n請告訴我您具體想了解哪個方面？"
            else:
                obj["chat_message_reply"]["text"] = "我理解您的問題。作為學習設計助手，我可以協助您進行課程規劃、教學設計、學習目標制定等。請提供更多細節，我會盡力幫助您。"
        
        # Ensure actions exists (optional per spec, but we provide default empty array)
        if "actions" not in obj or not isinstance(obj["actions"], list):
            obj["actions"] = []
        
        # Generate suggested follow-up questions (using AI generation, not restricted by system prompt)
        suggested_questions = generate_suggested_questions(
            user_msg, 
            obj["chat_message_reply"]["text"],
            conversation_history
        )
        if suggested_questions:
            obj["suggested_questions"] = suggested_questions

        return jsonify(obj)

    except Exception as e:
        # Write detailed error to log, and return simplified error message in response for frontend debugging
        app.logger.exception(e)
        return jsonify({
            "chat_message_reply": {
                "text": f"伺服器錯誤（暫供除錯）：{str(e)}"
            },
            "actions": []
        }), 500


@app.route("/api/suggest_dp", methods=["POST"])
def suggest_dp():
    data = request.json or {}

    topic = data.get("topic") or "General Topic"
    description = data.get("description") or "No description provided."
    subject = data.get("subject") or "General Studies"

    system_prompt = (
        "Pick the single best Disciplinary Practice and explain briefly. "
        "Use the provided definitions. Output must match the JSON schema."
    )

    user_prompt = f"""Definitions:
{DP_DEFINITIONS}

Course:
Subject: {subject}
Topic: {topic}
Description: {description}
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "dp_recommendation",
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "recommended_dp": {"type": "string"},
                    "reason": {"type": "string"}
                },
                "required": ["recommended_dp", "reason"]
            }
        }
    }

    try:
        msg = run_chat_with_optional_tools(
            messages,
            temperature=0.1,
            max_tokens=180,
            response_format=schema,
            tools=None
        )
        return jsonify(json.loads(msg.get("content", "{}")))
    except Exception:
        try:
            msg = run_chat_with_optional_tools(
                messages,
                temperature=0.1,
                max_tokens=180,
                response_format={"type": "json_object"},
                tools=None
            )
            return jsonify(json.loads(msg.get("content", "{}")))
        except Exception as e2:
            app.logger.exception(e2)
            return jsonify({"error": str(e2)}), 500


@app.route("/api/generate_ilos", methods=["POST"])
def generate_ilos():
    data = request.json or {}

    topic = data.get("topic", "N/A")
    description = data.get("description", "")
    subject = data.get("subject", "")
    grade = data.get("grade", "Secondary School")
    bloom_level = data.get("bloom_level", "Understand")
    action_verb = (data.get("action_verb") or "").strip()
    disciplinary_practice = data.get("disciplinary_practice", "General Inquiry")

    system_prompt = (
        "You are an educational consultant helping teachers create Intended Learning Outcomes (ILOs). "
        "Generate exactly 3 ILOs that align with the provided educational context and Bloom's Taxonomy level. "
        "Each ILO should be clear, measurable, and appropriate for the specified grade level and subject. "
        "Please format your response as a JSON array with exactly 3 objects, each containing a 'statement' field."
    )

    verb_instruction = f"Please begin each ILO statement with the action verb: '{action_verb}'." if action_verb else ""
    user_prompt = f"""Please help create 3 Intended Learning Outcomes (ILOs) for the following educational context:

Educational Context:
- Topic: {topic}
- Subject: {subject}
- Grade Level: {grade}
- Bloom's Taxonomy Level: {bloom_level}
- Disciplinary Practice: {disciplinary_practice}
{'- Action Verb: ' + action_verb if action_verb else ''}

{verb_instruction}

Please ensure each ILO:
1. Is appropriate for the specified grade level
2. Aligns with the Bloom's Taxonomy level provided
3. Is clear and measurable
4. Relates to the topic and subject area

{description if description else ''}
""".strip()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "ilos",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "statement": {"type": "string"}
                    },
                    "required": ["statement"]
                },
                "minItems": 3,
                "maxItems": 3
            }
        }
    }

    try:
        msg = run_chat_with_optional_tools(
            messages,
            temperature=0.2,
            max_tokens=320,
            response_format=schema,
            tools=None
        )
        content = msg.get("content", "[]")
        app.logger.info(f"ILO generation response content: {content[:200]}")
        
        try:
            ilos_data = json.loads(content) if content else []
        except json.JSONDecodeError as e:
            app.logger.error(f"Failed to parse ILO JSON: {e}, content: {content[:500]}")
            ilos_data = []
        
        # Ensure returned data is an array
        if isinstance(ilos_data, list):
            # Validate that each element in array has statement field
            validated_ilos = []
            for ilo in ilos_data:
                if isinstance(ilo, dict):
                    statement = ilo.get("statement") or ilo.get("text") or ilo.get("content") or ""
                    if statement:
                        validated_ilos.append({"statement": statement})
                elif isinstance(ilo, str):
                    validated_ilos.append({"statement": ilo})
            
            if validated_ilos:
                app.logger.info(f"Successfully generated {len(validated_ilos)} ILOs")
                return jsonify(validated_ilos)
            else:
                app.logger.warning("No valid ILOs found in list")
                return jsonify({"error": "No valid ILOs generated", "raw": ilos_data}), 500
        elif isinstance(ilos_data, dict):
            # Try to extract array from object (support multiple key names, including case variants)
            ilos_list = None
            for key in ["ilos", "ILOs", "data", "results", "statements"]:
                if key in ilos_data:
                    ilos_list = ilos_data[key]
                    break
            
            if isinstance(ilos_list, list) and ilos_list:
                validated_ilos = []
                for ilo in ilos_list:
                    if isinstance(ilo, dict):
                        statement = ilo.get("statement") or ilo.get("text") or ilo.get("content") or ""
                        if statement:
                            validated_ilos.append({"statement": statement})
                    elif isinstance(ilo, str):
                        validated_ilos.append({"statement": ilo})
                
                if validated_ilos:
                    app.logger.info(f"Successfully extracted {len(validated_ilos)} ILOs from object")
                    return jsonify(validated_ilos)
            
            app.logger.warning(f"ILO data is not a list: {type(ilos_data)}, data: {ilos_data}")
            return jsonify({"error": "Invalid response format", "data": ilos_data}), 500
        else:
            app.logger.warning(f"ILO data is not a list or dict: {type(ilos_data)}, data: {ilos_data}")
            return jsonify({"error": "Invalid response format", "data": ilos_data}), 500
            
    except Exception as e1:
        error_str = str(e1)
        app.logger.exception(e1)
        
        # Check if it's a content filter error
        if "content_filter" in error_str or "content management policy" in error_str or "ResponsibleAIPolicyViolation" in error_str:
            app.logger.error("Content filter triggered. Attempting with modified prompt...")
            # Retry with simpler and safer prompt
            safe_system_prompt = (
                "You are an educational consultant helping teachers create learning outcomes. "
                "Please create 3 clear and measurable learning outcomes based on the provided educational context."
            )
            safe_user_prompt = f"""Create 3 learning outcomes for:
Topic: {topic}
Subject: {subject}
Grade: {grade}
Bloom's Taxonomy Level: {bloom_level}
{f'Action Verb: {action_verb}' if action_verb else ''}

Please format as JSON array with 3 objects, each with a 'statement' field."""
            
            try:
                safe_messages = [
                    {"role": "system", "content": safe_system_prompt},
                    {"role": "user", "content": safe_user_prompt}
                ]
                msg = run_chat_with_optional_tools(
                    safe_messages,
                    temperature=0.2,
                    max_tokens=320,
                    response_format={"type": "json_object"},
                    tools=None
                )
                content = msg.get("content", "{}")
                app.logger.info(f"Safe prompt ILO generation response content: {content[:200]}")
                
                # Process retry result
                try:
                    ilos_data = json.loads(content) if content else []
                    # If returned is an object, try to extract array
                    if isinstance(ilos_data, dict):
                        # Try to extract array from common keys
                        ilos_data = ilos_data.get("ilos", ilos_data.get("data", ilos_data.get("statements", [])))
                    
                    if isinstance(ilos_data, list):
                        validated_ilos = []
                        for ilo in ilos_data:
                            if isinstance(ilo, dict):
                                statement = ilo.get("statement") or ilo.get("text") or ilo.get("content") or ""
                                if statement:
                                    validated_ilos.append({"statement": statement})
                            elif isinstance(ilo, str):
                                validated_ilos.append({"statement": ilo})
                        
                        if validated_ilos:
                            app.logger.info(f"Successfully generated {len(validated_ilos)} ILOs (safe prompt)")
                            return jsonify(validated_ilos)
                
                except json.JSONDecodeError as e3:
                    app.logger.error(f"Failed to parse safe prompt ILO JSON: {e3}, content: {content[:500]}")
                
                # If retry still fails, return error
                return jsonify({
                    "error": "內容過濾錯誤：請嘗試修改輸入內容或稍後再試",
                    "details": "Azure OpenAI 的內容過濾系統阻止了此請求。請確保輸入內容符合教育用途規範。"
                }), 400
                
            except Exception as e2:
                app.logger.exception(e2)
                return jsonify({
                    "error": "內容過濾錯誤：請嘗試修改輸入內容或稍後再試",
                    "details": "Azure OpenAI 的內容過濾系統阻止了此請求。請確保輸入內容符合教育用途規範。"
                }), 400
        
        try:
            msg = run_chat_with_optional_tools(
                messages,
                temperature=0.2,
                max_tokens=320,
                response_format={"type": "json_object"},
                tools=None
            )
            content = msg.get("content", "{}")
            app.logger.info(f"Fallback ILO generation response content: {content[:200]}")
            
            try:
                ilos_data = json.loads(content) if content else []
                # 如果返回的是對象，嘗試提取數組
                if isinstance(ilos_data, dict):
                    # 嘗試從常見的鍵中提取數組
                    ilos_data = ilos_data.get("ilos", ilos_data.get("data", []))
                
                if isinstance(ilos_data, list):
                    validated_ilos = []
                    for ilo in ilos_data:
                        if isinstance(ilo, dict):
                            statement = ilo.get("statement") or ilo.get("text") or ilo.get("content") or ""
                            if statement:
                                validated_ilos.append({"statement": statement})
                        elif isinstance(ilo, str):
                            validated_ilos.append({"statement": ilo})
                    
                    if validated_ilos:
                        app.logger.info(f"Successfully generated {len(validated_ilos)} ILOs (fallback)")
                        return jsonify(validated_ilos)
                    else:
                        app.logger.warning("No valid ILOs found in fallback list")
                        return jsonify({"error": "No valid ILOs generated", "raw": ilos_data}), 500
                elif isinstance(ilos_data, dict):
                    # Try to extract array from object (support multiple key names, including case variants)
                    ilos_list = None
                    for key in ["ilos", "ILOs", "data", "results", "statements"]:
                        if key in ilos_data:
                            ilos_list = ilos_data[key]
                            break
                    
                    if isinstance(ilos_list, list) and ilos_list:
                        validated_ilos = []
                        for ilo in ilos_list:
                            if isinstance(ilo, dict):
                                statement = ilo.get("statement") or ilo.get("text") or ilo.get("content") or ""
                                if statement:
                                    validated_ilos.append({"statement": statement})
                            elif isinstance(ilo, str):
                                validated_ilos.append({"statement": ilo})
                        
                        if validated_ilos:
                            app.logger.info(f"Successfully extracted {len(validated_ilos)} ILOs from fallback object")
                            return jsonify(validated_ilos)
                
                app.logger.warning(f"Fallback ILO data is not a list: {type(ilos_data)}")
                return jsonify({"error": "Invalid response format", "data": ilos_data}), 500
            except json.JSONDecodeError as e:
                app.logger.error(f"Failed to parse fallback ILO JSON: {e}")
                return jsonify({"error": f"Failed to parse response: {str(e)}"}), 500
                
        except Exception as e2:
            app.logger.exception(e2)
            return jsonify({"error": str(e2)}), 500


def extract_text_from_file(file, filename):
    """
    Extract text content from uploaded file
    Supports PDF, DOCX, TXT formats
    """
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if file_ext == 'pdf':
        if not PDF_AVAILABLE:
            return None, "PDF 解析庫未安裝。請運行以下命令安裝：pip install PyPDF2"
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text, None
        except Exception as e:
            return None, f"PDF 解析錯誤: {str(e)}"
    
    elif file_ext in ['doc', 'docx']:
        if not DOCX_AVAILABLE:
            return None, "DOCX 解析庫未安裝。請運行以下命令安裝：pip install python-docx"
        try:
            doc = Document(file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text, None
        except Exception as e:
            return None, f"DOCX 解析錯誤: {str(e)}"
    
    elif file_ext == 'txt':
        try:
            file.seek(0)
            text = file.read().decode('utf-8', errors='ignore')
            return text, None
        except Exception as e:
            return None, f"TXT 讀取錯誤: {str(e)}"
    
    else:
        return None, f"不支援的文件格式: {file_ext}"


@app.route("/api/analyze-document", methods=["POST", "OPTIONS"])
def analyze_document():
    """
    Analyze uploaded teaching document and provide suggestions
    """
    if request.method == "OPTIONS":
        return ("", 204)

    try:
        # Check if file exists
        if 'file' not in request.files:
            return jsonify({"error": "沒有上傳文件"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "文件為空"}), 400

        # Get optional parameters
        user_message = request.form.get("message", "").strip()
        subject = request.form.get("subject", "").strip()
        grade = request.form.get("grade", "").strip()
        topic = request.form.get("topic", "").strip()

        # Extract file content
        filename = secure_filename(file.filename)
        file.seek(0)  # Ensure file pointer is at the beginning
        
        text_content, error = extract_text_from_file(file, filename)
        
        if error:
            # Provide more detailed error message
            error_msg = error
            if "未安裝" in error:
                error_msg += "\n\n請在終端運行以下命令安裝所需庫：\npip install -r requirements.txt\n\n或者單獨安裝：\npip install PyPDF2 python-docx"
            return jsonify({"error": error_msg}), 400
        
        if not text_content or len(text_content.strip()) < 10:
            return jsonify({"error": "文件內容過少或無法提取文字"}), 400

        # Limit file content length (avoid exceeding token limit)
        max_length = 10000  # Approximately 2500-3000 tokens
        if len(text_content) > max_length:
            text_content = text_content[:max_length] + "\n\n...（內容已截斷）"

        # Build analysis prompt
        context_parts = []
        if subject:
            context_parts.append(f"科目：{subject}")
        if grade:
            context_parts.append(f"年級：{grade}")
        if topic:
            context_parts.append(f"課題：{topic}")
        context_block = "\n".join(context_parts) + "\n\n" if context_parts else ""

        user_prompt = user_message if user_message else "請分析這個教學文件並提供改進建議"
        
        system_prompt = (
            "你是一位教育設計專家。請仔細分析用戶提供的教學文件，"
            "並提供專業的改進建議。重點關注：\n"
            "1. 學習目標（ILO）的清晰度和可測量性\n"
            "2. 教學活動的設計是否有效\n"
            "3. 評量方式是否與學習目標對齊\n"
            "4. 是否符合 Bloom's Taxonomy\n"
            "5. 整體教學設計的優缺點\n\n"
            "請用中文回答，提供具體、可操作的建議。"
        )

        full_user_content = f"""{context_block}文件名稱：{filename}

文件內容：
{text_content}

用戶問題：{user_prompt}
""".strip()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_user_content}
        ]

        # Call OpenAI API
        payload = {
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 1000
        }

        # Use Azure OpenAI client
        if not azure_openai_client:
            return jsonify({"error": "Azure OpenAI client not initialized"}), 500
        
        try:
            completion = azure_openai_client.chat.completions.create(
                model=DEPLOYMENT_ID,
                messages=messages,
                temperature=0.5,
                max_tokens=1500
            )
            analysis_text = completion.choices[0].message.content
        except Exception as e:
            app.logger.error(f"Azure OpenAI API error: {e}")
            return jsonify({"error": f"AI 分析失敗：{str(e)}"}), 500

        return jsonify({
            "analysis": analysis_text,
            "filename": filename,
            "actions": []  # Can add actions based on analysis results
        })

    except Exception as e:
        app.logger.exception(e)
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=False)
    print(f"\nBackend server running at: http://{host}:{port}")
    print(f"If host is 0.0.0.0, you can access via:")
    print(f"  - http://localhost:{port}")
    print(f"  - http://127.0.0.1:{port}")
    print(f"  - http://<your-ip-address>:{port}")