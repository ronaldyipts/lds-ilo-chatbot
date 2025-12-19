import React, { useEffect, useMemo, useRef, useState } from "react";

function getApiBaseUrl() {
  // 1) If using Vite proxy (recommended), return empty string, fetch("/api/...") will use proxy
  // 2) You can also set VITE_API_BASE_URL="http://localhost:5000" in .env
  const envBase = import.meta.env.VITE_API_BASE_URL;
  if (typeof envBase === "string" && envBase.trim()) return envBase.trim();

  // Default same-origin
  return "";
}

function extractReplyText(data) {
  const t = data?.chat_message_reply?.text;
  return (typeof t === "string") ? t : "";
}

function buildOptionsDebugText(resp) {
  const allow = resp.headers.get("allow") || resp.headers.get("Allow") || "";
  const acao = resp.headers.get("access-control-allow-origin") || "";
  const acam = resp.headers.get("access-control-allow-methods") || "";
  const acah = resp.headers.get("access-control-allow-headers") || "";

  const lines = [
    `OPTIONS /api/chat → HTTP ${resp.status} ${resp.statusText || ""}`.trim(),
    allow ? `Allow: ${allow}` : null,
    acao ? `Access-Control-Allow-Origin: ${acao}` : null,
    acam ? `Access-Control-Allow-Methods: ${acam}` : null,
    acah ? `Access-Control-Allow-Headers: ${acah}` : null
  ].filter(Boolean);

  return lines.join("\n");
}

// Get subject name based on language code
function getSubjectName(subject, locale = "zh_HK") {
  if (!subject || !subject.translation || !Array.isArray(subject.translation)) {
    return subject?.name || "";
  }
  
  // Priority order: zh_HK > en_US > zh_CN > first available
  const preferredOrder = [locale, "zh_HK", "en_US", "zh_CN"];
  
  for (const langCode of preferredOrder) {
    // Find all translations matching the lang_code
    const matchingTranslations = subject.translation.filter(t => t.lang_code === langCode);
    if (matchingTranslations.length > 0) {
      // If multiple matches, select the one with latest updated_at (if available)
      if (matchingTranslations.length > 1 && matchingTranslations[0].updated_at) {
        const sorted = matchingTranslations.sort((a, b) => {
          const dateA = new Date(a.updated_at || 0);
          const dateB = new Date(b.updated_at || 0);
          return dateB - dateA; // Descending order, latest first
        });
        if (sorted[0].name) {
          return sorted[0].name;
        }
      } else if (matchingTranslations[0].name) {
        return matchingTranslations[0].name;
      }
    }
  }
  
  // If none found, return first available
  if (subject.translation.length > 0 && subject.translation[0].name) {
    return subject.translation[0].name;
  }
  
  return subject.name || "";
}

// Get grade level name based on language code (same logic as subject)
function getGradeLevelName(gradeLevel, locale = "zh_HK") {
  if (!gradeLevel || !gradeLevel.translation || !Array.isArray(gradeLevel.translation)) {
    return gradeLevel?.name || "";
  }
  
  // Priority order: zh_HK > en_US > zh_CN > first available
  const preferredOrder = [locale, "zh_HK", "en_US", "zh_CN"];
  
  for (const langCode of preferredOrder) {
    const translation = gradeLevel.translation.find(t => t.lang_code === langCode);
    if (translation && translation.name) {
      return translation.name;
    }
  }
  
  // If none found, return first available
  if (gradeLevel.translation.length > 0 && gradeLevel.translation[0].name) {
    return gradeLevel.translation[0].name;
  }
  
  return gradeLevel.name || "";
}

// Get Bloom Taxonomy Level name based on language code
function getBloomLevelName(level, locale = "zh_HK") {
  if (!level || !level.translation || !Array.isArray(level.translation)) {
    return level?.name || "";
  }
  
  const preferredOrder = [locale, "zh_HK", "en_US", "zh_CN"];
  
  for (const langCode of preferredOrder) {
    const translation = level.translation.find(t => t.lang_code === langCode);
    if (translation && translation.name) {
      return translation.name;
    }
  }
  
  if (level.translation.length > 0 && level.translation[0].name) {
    return level.translation[0].name;
  }
  
  return level.name || "";
}

// Get Verb name based on language code
function getVerbName(verb, locale = "zh_HK") {
  if (!verb || !verb.translation || !Array.isArray(verb.translation)) {
    return verb?.name || "";
  }
  
  const preferredOrder = [locale, "zh_HK", "en_US", "zh_CN"];
  
  for (const langCode of preferredOrder) {
    const translation = verb.translation.find(t => t.lang_code === langCode);
    if (translation && translation.name) {
      return translation.name;
    }
  }
  
  if (verb.translation.length > 0 && verb.translation[0].name) {
    return verb.translation[0].name;
  }
  
  return verb.name || "";
}

// Get ILO Pattern Statement based on language code
function getPatternStatement(pattern, locale = "zh_HK") {
  if (!pattern || !pattern.translation || !Array.isArray(pattern.translation)) {
    return pattern?.statement || "";
  }
  
  const preferredOrder = [locale, "zh_HK", "en_US", "zh_CN"];
  
  for (const langCode of preferredOrder) {
    const translation = pattern.translation.find(t => t.lang_code === langCode);
    if (translation && translation.statement) {
      return translation.statement;
    }
  }
  
  if (pattern.translation.length > 0 && pattern.translation[0].statement) {
    return pattern.translation[0].statement;
  }
  
  return pattern.statement || "";
}

export default function App() {
  const API_BASE_URL = useMemo(() => getApiBaseUrl(), []);
  
  // Chat-related state
  const [isTyping, setIsTyping] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState([]);
  const greetedRef = useRef(false);
  
  // Subject-related state
  const [subjects, setSubjects] = useState([]);
  const [selectedSubjectId, setSelectedSubjectId] = useState(null);
  const [isLoadingSubjects, setIsLoadingSubjects] = useState(false);
  
  // Grade level-related state
  const [gradeLevels, setGradeLevels] = useState([]);
  const [selectedGradeLevelId, setSelectedGradeLevelId] = useState(null);
  const [isLoadingGradeLevels, setIsLoadingGradeLevels] = useState(false);
  
  // Topic-related state
  const [topic, setTopic] = useState("");
  
  // ILO Category-related state
  const [iloCategories, setIloCategories] = useState([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);
  const [isLoadingCategories, setIsLoadingCategories] = useState(false);
  
  // ILO Patterns-related state
  const [iloPatterns, setIloPatterns] = useState([]);
  const [isLoadingPatterns, setIsLoadingPatterns] = useState(false);
  const [showTemplatesForCategory, setShowTemplatesForCategory] = useState(null); // Category ID to show templates for
  const [actionTemplates, setActionTemplates] = useState(null); // Template data from action {patterns, presentation, context}
  
  // Bloom Taxonomy-related state
  const [bloomLevels, setBloomLevels] = useState([]);
  const [selectedBloomLevelId, setSelectedBloomLevelId] = useState(null);
  const [isLoadingBloomLevels, setIsLoadingBloomLevels] = useState(false);
  const [availableVerbs, setAvailableVerbs] = useState([]);
  const [selectedVerbId, setSelectedVerbId] = useState(null);
  const [isGeneratingILOs, setIsGeneratingILOs] = useState(false);

  // TAB-related state
  const [activeTab, setActiveTab] = useState("chatbot"); // "chatbot" or "generate-ilo"

  // File upload-related state
  const [uploadedFile, setUploadedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const fileInputRef = useRef(null);

  const bodyRef = useRef(null);
  const inputRef = useRef(null);

  const hintText = "你可以問：學習目標（ILO）寫法、Bloom's Taxonomy、評量設計、教學活動建議等。";

  // Compatible function to generate unique ID
  function generateId() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
      return crypto.randomUUID();
    }
    // Fallback: use timestamp and random number
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  function addMessage(role, text, ilos = null, suggestedQuestions = null) {
    setMessages(prev => [...prev, { 
      id: generateId(), 
      role, 
      text: text || "",
      ilos: ilos || undefined,
      suggestedQuestions: suggestedQuestions || undefined
    }]);
  }

  // Greet on load
  useEffect(() => {
    // focus
    setTimeout(() => inputRef.current?.focus(), 50);

    if (!greetedRef.current) {
      addMessage("bot", "你好，我是 Learning Design 助手。\n\n💡 建議：為了提供更精準的協助，請先在上方填寫課題、科目和年級資訊。完成後，你可以告訴我想設計什麼課題或學習目標，我會根據這些資訊為你提供更貼切的建議。");
      greetedRef.current = true;
    }
  }, []);

  // Auto scroll to bottom
  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, isTyping]);

  // Auto-grow textarea
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  }, [inputValue]);

  // Load subjects list
  useEffect(() => {
    let cancelled = false;

    async function loadSubjects() {
      setIsLoadingSubjects(true);
      try {
        const url = `${API_BASE_URL}/api/subjects?locale=zh_HK`;
        console.log("Loading subjects from:", url);
        console.log("API_BASE_URL value:", API_BASE_URL);
        
        // Try using POST (because LDS API chatbot/options endpoints usually use POST)
        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ locale: "zh_HK" })
        });

        if (cancelled) return;

        console.log("Subjects API response status:", resp.status, resp.statusText);

        let data;
        try {
          const text = await resp.text();
          console.log("Raw response text (first 200 chars):", text.substring(0, 200));
          data = JSON.parse(text);
        } catch (err) {
          console.error("Failed to parse JSON:", err);
          console.error("Response status:", resp.status);
          console.error("Response headers:", Object.fromEntries(resp.headers.entries()));
          data = { error: "無法解析 JSON 回應", details: err.message };
        }

        console.log("Subjects API response data:", data);

        if (resp.ok) {
          if (Array.isArray(data)) {
            console.log(`Successfully loaded ${data.length} subjects`);
            setSubjects(data);
            // Default to select first subject (if none currently selected)
            setSelectedSubjectId(prev => {
              if (prev === null && data.length > 0) {
                return data[0].id;
              }
              return prev;
            });
          } else {
            console.error("Subjects API returned non-array:", data);
            // If returned is not an array, might be error message
            if (data.error) {
              console.error("LDS API error:", data.error, data.details);
              setSubjects([]); // Ensure set to empty array
            } else {
              console.error("Unknown data format:", typeof data, data);
              setSubjects([]); // Unknown format, set to empty array
            }
          }
        } else {
          // Backend returned error
          const errorMsg = data.error || `HTTP ${resp.status}`;
          const errorDetails = data.details || "";
          console.error("Failed to load subjects:", errorMsg, errorDetails);
          console.error("Full error response:", data);
          setSubjects([]); // Set to empty array on error
          
          // If 503 or connection error, might be LDS API issue
          if (resp.status === 503 || resp.status === 504 || errorMsg.includes("connect") || errorMsg.includes("timeout")) {
            console.error("⚠️ LDS API 連接問題，請檢查：");
            console.error("  1. LDS_BASE 環境變數是否正確設置");
            console.error("  2. LDS_TOKEN 環境變數是否正確設置（如果需要）");
            console.error("  3. LDS API 服務器是否可訪問");
          }
        }
      } catch (err) {
        if (cancelled) return;
        console.error("Error loading subjects:", err);
        console.error("Error details:", err.message, err.stack);
        setSubjects([]); // Set to empty array on network error
      } finally {
        if (!cancelled) {
          setIsLoadingSubjects(false);
        }
      }
    }

    loadSubjects();
    return () => { cancelled = true; };
  }, [API_BASE_URL]);

  // Load grade levels list
  useEffect(() => {
    let cancelled = false;

    async function loadGradeLevels() {
      setIsLoadingGradeLevels(true);
      try {
        const url = `${API_BASE_URL}/api/grade-levels?locale=zh_HK`;
        console.log("Loading grade levels from:", url);
        console.log("API_BASE_URL value:", API_BASE_URL);
        
        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ locale: "zh_HK" })
        });

        if (cancelled) return;

        console.log("Grade levels API response status:", resp.status, resp.statusText);

        let data;
        try {
          const text = await resp.text();
          console.log("Raw response text (first 200 chars):", text.substring(0, 200));
          data = JSON.parse(text);
        } catch (err) {
          console.error("Failed to parse JSON:", err);
          console.error("Response status:", resp.status);
          console.error("Response headers:", Object.fromEntries(resp.headers.entries()));
          data = { error: "無法解析 JSON 回應", details: err.message };
        }

        console.log("Grade levels API response data:", data);

        if (resp.ok) {
          if (Array.isArray(data)) {
            console.log(`Successfully loaded ${data.length} grade levels`);
            setGradeLevels(data);
            // Default to select first grade level (if none currently selected)
            setSelectedGradeLevelId(prev => {
              if (prev === null && data.length > 0) {
                return data[0].id;
              }
              return prev;
            });
          } else {
            console.error("Grade levels API returned non-array:", data);
            if (data.error) {
              console.error("LDS API error:", data.error, data.details);
            }
            setGradeLevels([]); // Ensure set to empty array
          }
        } else {
          const errorMsg = data.error || `HTTP ${resp.status}`;
          const errorDetails = data.details || "";
          console.error("Failed to load grade levels:", errorMsg, errorDetails);
          console.error("Full error response:", data);
          setGradeLevels([]); // 錯誤時設置為空數組
          
          // 如果是 503 或連接錯誤，可能是 LDS API 問題
          if (resp.status === 503 || resp.status === 504 || errorMsg.includes("connect") || errorMsg.includes("timeout")) {
            console.error("⚠️ LDS API 連接問題，請檢查：");
            console.error("  1. LDS_BASE 環境變數是否正確設置");
            console.error("  2. LDS_TOKEN 環境變數是否正確設置（如果需要）");
            console.error("  3. LDS API 服務器是否可訪問");
          }
        }
      } catch (err) {
        if (cancelled) return;
        console.error("Error loading grade levels:", err);
        console.error("Error details:", err.message, err.stack);
        setGradeLevels([]); // Set to empty array on network error
      } finally {
        if (!cancelled) {
          setIsLoadingGradeLevels(false);
        }
      }
    }

    loadGradeLevels();
    return () => { cancelled = true; };
  }, [API_BASE_URL]);

  // Load ILO Categories
  useEffect(() => {
    let cancelled = false;

    async function loadIloCategories() {
      setIsLoadingCategories(true);
      try {
        const url = `${API_BASE_URL}/api/ilo-categories?locale=zh_HK`;
        console.log("Loading ILO categories from:", url);
        console.log("API_BASE_URL value:", API_BASE_URL);
        
        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ locale: "zh_HK" })
        });

        if (cancelled) return;

        console.log("ILO categories API response status:", resp.status, resp.statusText);

        let data;
        try {
          const text = await resp.text();
          console.log("Raw response text (first 200 chars):", text.substring(0, 200));
          data = JSON.parse(text);
        } catch (err) {
          console.error("Failed to parse JSON:", err);
          console.error("Response status:", resp.status);
          console.error("Response headers:", Object.fromEntries(resp.headers.entries()));
          data = { error: "無法解析 JSON 回應", details: err.message };
        }

        console.log("ILO categories API response data:", data);

        if (resp.ok) {
          if (Array.isArray(data)) {
            console.log(`Successfully loaded ${data.length} ILO categories`);
            setIloCategories(data);
          } else {
            console.error("ILO categories API returned non-array:", data);
            if (data.error) {
              console.error("LDS API error:", data.error, data.details);
            }
            setIloCategories([]); // 確保設置為空數組
          }
        } else {
          const errorMsg = data.error || `HTTP ${resp.status}`;
          const errorDetails = data.details || "";
          console.error("Failed to load ILO categories:", errorMsg, errorDetails);
          console.error("Full error response:", data);
          setIloCategories([]); // 錯誤時設置為空數組
          
          // 如果是 503 或連接錯誤，可能是 LDS API 問題
          if (resp.status === 503 || resp.status === 504 || errorMsg.includes("connect") || errorMsg.includes("timeout")) {
            console.error("⚠️ LDS API 連接問題，請檢查：");
            console.error("  1. LDS_BASE 環境變數是否正確設置");
            console.error("  2. LDS_TOKEN 環境變數是否正確設置（如果需要）");
            console.error("  3. LDS API 服務器是否可訪問");
          }
        }
      } catch (err) {
        if (cancelled) return;
        console.error("Error loading ILO categories:", err);
        console.error("Error details:", err.message, err.stack);
        setIloCategories([]); // Set to empty array on network error
      } finally {
        if (!cancelled) {
          setIsLoadingCategories(false);
        }
      }
    }

    loadIloCategories();
    return () => { cancelled = true; };
  }, [API_BASE_URL]);

  // Load ILO Patterns
  useEffect(() => {
    let cancelled = false;

    async function loadIloPatterns() {
      setIsLoadingPatterns(true);
      try {
        const url = `${API_BASE_URL}/api/chatbot/patterns/intended-learning-outcomes`;
        console.log("Loading ILO patterns from:", url);
        
        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}) // POST request needs body
        });

        if (cancelled) return;

        console.log("ILO patterns API response status:", resp.status, resp.statusText);

        let data;
        try {
          const text = await resp.text();
          console.log("Raw response text (first 500 chars):", text.substring(0, 500));
          data = JSON.parse(text);
        } catch (err) {
          console.error("Failed to parse JSON:", err);
          console.error("Response status:", resp.status);
          data = { error: "無法解析 JSON 回應", details: err.message };
        }

        console.log("ILO patterns API response data:", data);

        if (resp.ok) {
          if (Array.isArray(data)) {
            console.log(`Successfully loaded ${data.length} ILO patterns`);
            setIloPatterns(data);
          } else {
            console.error("ILO patterns API returned non-array:", data);
            if (data.error) {
              console.error("LDS API error:", data.error, data.details);
            }
            setIloPatterns([]);
          }
        } else {
          const errorMsg = data.error || `HTTP ${resp.status}`;
          const errorDetails = data.details || "";
          console.error("Failed to load ILO patterns:", errorMsg, errorDetails);
          console.error("Full error response:", data);
          setIloPatterns([]);
        }
      } catch (err) {
        if (cancelled) return;
        console.error("Error loading ILO patterns:", err);
        console.error("Error details:", err.message, err.stack);
        setIloPatterns([]);
      } finally {
        if (!cancelled) {
          setIsLoadingPatterns(false);
        }
      }
    }

    loadIloPatterns();
    return () => { cancelled = true; };
  }, [API_BASE_URL]);

  // Load Bloom Taxonomy Levels
  useEffect(() => {
    let cancelled = false;

    async function loadBloomLevels() {
      setIsLoadingBloomLevels(true);
      try {
        const url = `${API_BASE_URL}/api/bloom-taxonomy-levels?locale=zh_HK`;
        console.log("Loading bloom taxonomy levels from:", url);
        console.log("API_BASE_URL value:", API_BASE_URL);
        
        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ locale: "zh_HK" })
        });

        if (cancelled) return;

        console.log("Bloom taxonomy levels API response status:", resp.status, resp.statusText);

        let data;
        try {
          const text = await resp.text();
          console.log("Raw response text (first 200 chars):", text.substring(0, 200));
          data = JSON.parse(text);
        } catch (err) {
          console.error("Failed to parse JSON:", err);
          console.error("Response status:", resp.status);
          console.error("Response headers:", Object.fromEntries(resp.headers.entries()));
          data = { error: "無法解析 JSON 回應", details: err.message };
        }

        console.log("Bloom taxonomy levels API response data:", data);

        if (resp.ok) {
          if (Array.isArray(data)) {
            console.log(`Successfully loaded ${data.length} bloom taxonomy levels`);
            setBloomLevels(data);
          } else {
            console.error("Bloom taxonomy levels API returned non-array:", data);
            if (data.error) {
              console.error("LDS API error:", data.error, data.details);
            }
            setBloomLevels([]); // 確保設置為空數組
          }
        } else {
          const errorMsg = data.error || `HTTP ${resp.status}`;
          const errorDetails = data.details || "";
          console.error("Failed to load bloom taxonomy levels:", errorMsg, errorDetails);
          console.error("Full error response:", data);
          setBloomLevels([]); // 錯誤時設置為空數組
          
          // 如果是 503 或連接錯誤，可能是 LDS API 問題
          if (resp.status === 503 || resp.status === 504 || errorMsg.includes("connect") || errorMsg.includes("timeout")) {
            console.error("⚠️ LDS API 連接問題，請檢查：");
            console.error("  1. LDS_BASE 環境變數是否正確設置");
            console.error("  2. LDS_TOKEN 環境變數是否正確設置（如果需要）");
            console.error("  3. LDS API 服務器是否可訪問");
          }
        }
      } catch (err) {
        if (cancelled) return;
        console.error("Error loading bloom taxonomy levels:", err);
        console.error("Error details:", err.message, err.stack);
        setBloomLevels([]); // Set to empty array on network error
      } finally {
        if (!cancelled) {
          setIsLoadingBloomLevels(false);
        }
      }
    }

    loadBloomLevels();
    return () => { cancelled = true; };
  }, [API_BASE_URL]);

  // When selected Category changes, reset Bloom Taxonomy and Verb (if category doesn't need them)
  useEffect(() => {
    if (!selectedCategoryId) {
      return;
    }

    const selectedCategory = iloCategories.find(cat => cat.id === selectedCategoryId);
    if (selectedCategory && !selectedCategory.show_bloom_taxonomy) {
      // If category doesn't show Bloom Taxonomy, clear selection
      setSelectedBloomLevelId(null);
      setSelectedVerbId(null);
      setAvailableVerbs([]);
    }
  }, [selectedCategoryId, iloCategories]);

  // When Bloom Level is selected, load corresponding Verbs
  useEffect(() => {
    if (!selectedBloomLevelId) {
      setAvailableVerbs([]);
      setSelectedVerbId(null);
      return;
    }

    const selectedLevel = bloomLevels.find(level => level.id === selectedBloomLevelId);
    if (selectedLevel && selectedLevel.bloom_taxonomy_verbs) {
      setAvailableVerbs(selectedLevel.bloom_taxonomy_verbs);
      // Default to select first verb (if available)
      if (selectedLevel.bloom_taxonomy_verbs.length > 0) {
        setSelectedVerbId(selectedLevel.bloom_taxonomy_verbs[0].id);
      } else {
        setSelectedVerbId(null);
      }
    } else {
      setAvailableVerbs([]);
      setSelectedVerbId(null);
    }
  }, [selectedBloomLevelId, bloomLevels]);

  // -----------------------
  // First thing: use API to retrieve OPTIONS
  // You requested "do the first thing first" → I do it once on mount
  // If you don't want to call OPTIONS on every load, can change to button trigger
  // -----------------------
  useEffect(() => {
    let cancelled = false;

    async function retrieveOptions() {
      try {
        const resp = await fetch(`${API_BASE_URL}/api/chat`, {
          method: "OPTIONS",
          mode: "cors",
          credentials: "omit"
        });

        if (cancelled) return;
        // Remove auto-display of OPTIONS results to avoid disturbing users
        // addMessage("bot", buildOptionsDebugText(resp));
      } catch (err) {
        if (cancelled) return;
        console.error(err);
        // Remove auto-display of errors to avoid disturbing users
        // addMessage("bot", "OPTIONS retrieval failed: server may not support OPTIONS, blocked, or CORS settings not allowed.");
      }
    }

    retrieveOptions();
    return () => { cancelled = true; };
  }, [API_BASE_URL]);

// ... Previous code remains unchanged ...

  // 生成預期學習成果（ILO）
  async function generateILOs() {
    if (isGeneratingILOs) return;
    
    // Validate required fields
    if (!topic.trim()) {
      addMessage("bot", "請先輸入課題。");
      return;
    }
    
    if (!selectedCategoryId) {
      addMessage("bot", "請先選擇 ILO 種類（Category）。");
      return;
    }
    
    const selectedCategory = iloCategories.find(cat => cat.id === selectedCategoryId);
    if (!selectedCategory) {
      addMessage("bot", "請先選擇有效的 ILO 種類。");
      return;
    }
    
    // Check if Bloom Taxonomy is needed based on category settings
    if (selectedCategory.show_bloom_taxonomy) {
      if (selectedCategory.require_bloom_taxonomy && !selectedBloomLevelId) {
        addMessage("bot", "此種類需要選擇 Bloom Taxonomy Level。");
        return;
      }
      
      if (selectedBloomLevelId && !selectedVerbId) {
        addMessage("bot", "請先選擇動詞（Verb）。");
        return;
      }
    }

    setIsGeneratingILOs(true);

    try {
      const selectedSubject = selectedSubjectId ? subjects.find(s => s.id === selectedSubjectId) : null;
      const selectedGradeLevel = selectedGradeLevelId ? gradeLevels.find(g => g.id === selectedGradeLevelId) : null;
      const selectedCategory = iloCategories.find(cat => cat.id === selectedCategoryId);
      const selectedBloomLevel = selectedBloomLevelId ? bloomLevels.find(level => level.id === selectedBloomLevelId) : null;
      const selectedVerb = selectedVerbId ? availableVerbs.find(v => v.id === selectedVerbId) : null;

      const requestBody = {
        topic: topic.trim(),
        subject: selectedSubject ? getSubjectName(selectedSubject, "zh_HK") : "",
        grade: selectedGradeLevel ? getGradeLevelName(selectedGradeLevel, "zh_HK") : "",
        category: selectedCategory ? selectedCategory.name : "",
        bloom_level: selectedBloomLevel ? getBloomLevelName(selectedBloomLevel, "zh_HK") : "",
        action_verb: selectedVerb ? getVerbName(selectedVerb, "zh_HK") : "",
        disciplinary_practice: "General Inquiry" // Default value, can be extended later
      };

      const resp = await fetch(`${API_BASE_URL}/api/generate_ilos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
      });

      const data = await resp.json().catch((err) => {
        console.error("Failed to parse JSON response:", err);
        return { error: "無法解析伺服器回應" };
      });

      if (!resp.ok) {
        const errorMsg = data.error || data.details || `HTTP ${resp.status}`;
        console.error("ILO generation failed:", errorMsg, data);
        addMessage("bot", `生成失敗：${errorMsg}`);
        return;
      }

      // Display generated ILOs
      console.log("ILO generation response:", data, "Type:", typeof data, "IsArray:", Array.isArray(data));
      
      let ilosArray = null;
      
      if (Array.isArray(data) && data.length > 0) {
        ilosArray = data.map(ilo => {
          // Handle different data formats
          const statement = ilo.statement || ilo.text || ilo.content || "";
          return { statement };
        }).filter(ilo => ilo.statement);
      } else if (data && typeof data === "object") {
        // Try to extract array from object (support multiple key names, including case variants)
        const ilosList = data.ilos || data.ILOs || data.data || data.results || data.statements || [];
        if (Array.isArray(ilosList)) {
          ilosArray = ilosList
            .map(ilo => {
              // If ilo is a string, use directly
              if (typeof ilo === "string") {
                return { statement: ilo };
              }
              // If it's an object, extract statement
              const statement = ilo.statement || ilo.text || ilo.content || "";
              return { statement };
            })
            .filter(ilo => ilo.statement);
        }
      }
      
      if (ilosArray && ilosArray.length > 0) {
        addMessage("bot", `已生成 ${ilosArray.length} 個預期學習成果：`, ilosArray);
      } else {
        console.error("Invalid ILO response:", data);
        addMessage("bot", `生成完成，但未收到有效的學習成果。回應：${JSON.stringify(data).substring(0, 200)}`);
      }
    } catch (err) {
      console.error(err);
      addMessage("bot", "生成失敗：請稍後再試，或確認伺服器已啟動。");
    } finally {
      setIsGeneratingILOs(false);
    }
  }

  async function sendMessage(messageText = null, isSuggestedQuestion = false) {
    const text = (messageText || inputValue).trim();
    const hasFile = uploadedFile !== null;
    
    // If no text and no file, don't send
    if ((!text && !hasFile) || isTyping) return;

    // If file exists, upload and analyze first
    if (hasFile) {
      await handleFileUploadAndAnalyze(text);
      return;
    }

    // Normal chat flow
    addMessage("user", text);
    // Only clear when using inputValue (not when using suggested question)
    if (!messageText) {
      setInputValue("");
    } else {
      // If using suggested question, also clear input box
      setInputValue("");
    }
    setIsTyping(true);

    try {
      // Prepare request body, including selected subject and grade information
      const requestBody = { message: text };
      
      // Mark this as a BOT-suggested question, should be accepted
      if (isSuggestedQuestion) {
        requestBody.is_suggested_question = true;
      }
      
      if (selectedSubjectId) {
        const selectedSubject = subjects.find(s => s.id === selectedSubjectId);
        if (selectedSubject) {
          requestBody.subject = getSubjectName(selectedSubject, "zh_HK");
        }
      }
      
      if (selectedGradeLevelId) {
        const selectedGradeLevel = gradeLevels.find(g => g.id === selectedGradeLevelId);
        if (selectedGradeLevel) {
          requestBody.grade = getGradeLevelName(selectedGradeLevel, "zh_HK");
        }
      }
      
      if (topic.trim()) {
        requestBody.topic = topic.trim();
      }

      // Build conversation history (for Socratic guidance)
      // Only include recent conversations, format: {role: "user"|"assistant", content: "..."}
      const conversationHistory = messages
        .slice(-10) // Only take most recent 10 messages
        .map(m => ({
          role: m.role === "bot" ? "assistant" : m.role,
          content: m.text || ""
        }))
        .filter(m => m.content.trim().length > 0);
      
      requestBody.conversation_history = conversationHistory;

      const resp = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody)
      });

    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      // Try to extract error text from backend JSON response
      const backendText =
        extractReplyText(data) ||
        data?.error ||
        `伺服器錯誤：HTTP ${resp.status}`;
      addMessage("bot", backendText);
      return; // Don't continue
    }

    const replyText = extractReplyText(data);
    const suggestedQuestions = data?.suggested_questions || null;
    addMessage("bot", replyText || "（沒有收到回覆內容）", null, suggestedQuestions);

    // Handle actions, especially show_pattern action
    if (data?.actions && Array.isArray(data.actions)) {
      for (const action of data.actions) {
        if (action.action_type === "show_pattern" && action.payload?.patterns) {
          // Display template based on action format
          setActionTemplates({
            patterns: action.payload.patterns,
            presentation: action.ui?.presentation || "popup",
            context: action.target?.context || "ILO"
          });
          break; // Only handle first show_pattern action
        }
      }
    }
  } catch (err) {
    console.error(err);
    addMessage("bot", "連線失敗：請稍後再試，或確認伺服器已啟動。");
  } finally {
    setIsTyping(false);
    setTimeout(() => inputRef.current?.focus(), 0);
  }
}

  async function handleFileUploadAndAnalyze(userMessage = "") {
    if (!uploadedFile || isUploading || isAnalyzing) return;

    // Save file reference and filename, because cannot access after clearing file
    const fileToUpload = uploadedFile;
    const fileName = uploadedFile.name;
    
    // Immediately clear file display (no longer show file in chat box)
    setUploadedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }

    setIsUploading(true);
    setIsAnalyzing(true);

    try {
      // Display user message (if any)
      if (userMessage.trim()) {
        addMessage("user", userMessage);
      }
      addMessage("user", `📎 上傳文件：${fileName}`);
      setInputValue("");
      setIsTyping(true);

      // Create FormData to upload file (using saved file reference)
      const formData = new FormData();
      formData.append("file", fileToUpload);
      if (userMessage.trim()) {
        formData.append("message", userMessage);
      }
      if (selectedSubjectId) {
        const selectedSubject = subjects.find(s => s.id === selectedSubjectId);
        if (selectedSubject) {
          formData.append("subject", getSubjectName(selectedSubject, "zh_HK"));
        }
      }
      if (selectedGradeLevelId) {
        const selectedGradeLevel = gradeLevels.find(g => g.id === selectedGradeLevelId);
        if (selectedGradeLevel) {
          formData.append("grade", getGradeLevelName(selectedGradeLevel, "zh_HK"));
        }
      }
      if (topic.trim()) {
        formData.append("topic", topic.trim());
      }

      const resp = await fetch(`${API_BASE_URL}/api/analyze-document`, {
        method: "POST",
        body: formData
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        const errorMsg = data.error || `HTTP ${resp.status}`;
        addMessage("bot", `文件分析失敗：${errorMsg}`);
        return;
      }

      // Display analysis results
      const analysisText = data.analysis || data.message || "分析完成";
      addMessage("bot", analysisText);

      // Handle actions
      if (data?.actions && Array.isArray(data.actions)) {
        for (const action of data.actions) {
          if (action.action_type === "show_pattern" && action.payload?.patterns) {
            setActionTemplates({
              patterns: action.payload.patterns,
              presentation: action.ui?.presentation || "popup",
              context: action.target?.context || "ILO"
            });
            break;
          }
        }
      }

      // File already cleared on submit, no need to clear again here
    } catch (err) {
      console.error("File upload error:", err);
      addMessage("bot", "文件上傳失敗：請稍後再試，或確認伺服器已啟動。");
    } finally {
      setIsUploading(false);
      setIsAnalyzing(false);
      setIsTyping(false);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }

  function onInputKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <section className="chat" aria-label="Chatbot window" role="main">
      <header className="chat-header">
        <div>
          <div className="chat-title">
            <span style={{ fontWeight: 900 }}>💬</span>
            <span>LDS Chatbot</span>
          </div>
          <div className="chat-subtitle">Learning Design assistant</div>
        </div>
      </header>

      {/* TAB 導航欄 */}
      <nav className="app-nav">
        <button
          className={`nav-tab ${activeTab === "chatbot" ? "active" : ""}`}
          onClick={() => setActiveTab("chatbot")}
        >
          聊天機器人
        </button>
        <button
          className={`nav-tab ${activeTab === "generate-ilo" ? "active" : ""}`}
          onClick={() => setActiveTab("generate-ilo")}
        >
          生成ILO
        </button>
      </nav>

      {/* 聊天機器人 TAB */}
      {activeTab === "chatbot" && (
        <div className="page-content">
          {/* 課程資訊選擇器 */}
          <div className="course-info-section">
            <div className="selector-group">
              <div className="subject-selector">
                <label htmlFor="topic-input-chat" className="subject-label">
                  課題：
                </label>
                <input
                  id="topic-input-chat"
                  type="text"
                  className="topic-input"
                  placeholder="請輸入課題名稱"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                />
              </div>
            </div>

            <div className="selector-group">
              <div className="subject-selector">
                <label htmlFor="subject-select-chat" className="subject-label">
                  科目：
                </label>
                <select
                  id="subject-select-chat"
                  className="subject-select"
                  value={selectedSubjectId || ""}
                  onChange={(e) => setSelectedSubjectId(e.target.value ? parseInt(e.target.value) : null)}
                  disabled={isLoadingSubjects}
                >
                  {isLoadingSubjects ? (
                    <option value="">載入中...</option>
                  ) : subjects.length === 0 ? (
                    <option value="">無可用科目（請檢查後端連接）</option>
                  ) : (
                    <>
                      <option value="">（不指定）</option>
                      {subjects.map(subject => (
                        <option key={subject.id} value={subject.id}>
                          {getSubjectName(subject, "zh_HK")}
                        </option>
                      ))}
                    </>
                  )}
                </select>
              </div>

              <div className="subject-selector">
                <label htmlFor="grade-level-select-chat" className="subject-label">
                  年級：
                </label>
                <select
                  id="grade-level-select-chat"
                  className="subject-select"
                  value={selectedGradeLevelId || ""}
                  onChange={(e) => setSelectedGradeLevelId(e.target.value ? parseInt(e.target.value) : null)}
                  disabled={isLoadingGradeLevels}
                >
                  {isLoadingGradeLevels ? (
                    <option value="">載入中...</option>
                  ) : gradeLevels.length === 0 ? (
                    <option value="">無可用年級（請檢查後端連接）</option>
                  ) : (
                    <>
                      <option value="">（不指定）</option>
                      {gradeLevels.map(gradeLevel => (
                        <option key={gradeLevel.id} value={gradeLevel.id}>
                          {getGradeLevelName(gradeLevel, "zh_HK")}
                        </option>
                      ))}
                    </>
                  )}
                </select>
              </div>
            </div>
          </div>

          {/* 文件上傳提醒 */}
          {!uploadedFile && (
            <div className="file-upload-hint">
              <div className="file-upload-hint-icon">📄</div>
              <div className="file-upload-hint-text">
                您也可以上傳課程相關的教學文件（PDF、DOCX、TXT），我會根據文件內容提供更精準的建議。
              </div>
            </div>
          )}

          <div className="hint">{hintText}</div>

          <main className="chat-body" ref={bodyRef}>
            {messages.map(m => (
              <div key={m.id}>
                {m.text && (
                  <div className={`msg ${m.role}`}>
                    {m.text}
                  </div>
                )}
                {m.ilos && Array.isArray(m.ilos) && m.ilos.length > 0 && (
                  <div className="ilos-container">
                    {m.ilos.map((ilo, index) => (
                      <div key={index} className="ilo-item">
                        <div className="ilo-number">{index + 1}</div>
                        <div className="ilo-statement">{ilo.statement}</div>
                      </div>
                    ))}
                  </div>
                )}
                {/* 建議跟進問題 */}
                {m.role === "bot" && m.suggestedQuestions && Array.isArray(m.suggestedQuestions) && m.suggestedQuestions.length > 0 && (
                  <div className="suggested-questions-container">
                    {m.suggestedQuestions.map((question, index) => (
                      question && (
                        <button
                          key={index}
                          className="suggested-question-btn"
                          onClick={() => {
                            // Directly use question text to send, mark this as BOT-suggested question
                            sendMessage(question, true);
                          }}
                        >
                          {question}
                        </button>
                      )
                    ))}
                  </div>
                )}
              </div>
            ))}

            {isTyping && (
              <div className="typing" aria-live="polite" aria-label="Assistant is typing">
                <span className="dot"></span><span className="dot"></span><span className="dot"></span>
              </div>
            )}
          </main>

          <footer className="chat-footer">
            {/* 文件上傳區域 */}
            {uploadedFile && (
              <div className="uploaded-file-info">
                <span className="file-name">📄 {uploadedFile.name}</span>
                <button 
                  className="file-remove-btn"
                  onClick={() => setUploadedFile(null)}
                  aria-label="移除文件"
                >
                  ×
                </button>
              </div>
            )}
            <div className="input-area">
              <input
                type="file"
                ref={fileInputRef}
                className="file-input"
                accept=".pdf,.doc,.docx,.txt"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) {
                    setUploadedFile(file);
                  }
                }}
                style={{ display: "none" }}
              />
              <button
                className="file-upload-btn"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading || isAnalyzing}
                aria-label="上傳文件"
                title="上傳教學文件（PDF, DOCX, TXT）"
              >
                上傳文件
              </button>
              <textarea
                className="input"
                ref={inputRef}
                placeholder="輸入訊息…（Enter 送出 / Shift+Enter 換行）"
                rows={1}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={onInputKeyDown}
              />
              <button 
                className="send" 
                onClick={sendMessage} 
                disabled={isTyping || (!inputValue.trim() && !uploadedFile)} 
                aria-label="Send message" 
                title="Send"
              >
                ➤
              </button>
            </div>
          </footer>
        </div>
      )}

      {/* 生成ILO TAB */}
      {activeTab === "generate-ilo" && (
        <div className="page-content generate-ilo-page">
          <div className="page-header">
            <h2>構思預期學習成果 (ILO)</h2>
            <p>請填寫以下資訊以生成預期學習成果</p>
            {/* 提示用戶到聊天機器人頁面設置課題、科目、年級 */}
            {(!topic || !selectedSubjectId || !selectedGradeLevelId) && (
              <div className="course-info-reminder">
                <div className="reminder-icon">💡</div>
                <div className="reminder-content">
                  <div className="reminder-title">請先設置課程資料</div>
                  <div className="reminder-text">
                    為了生成更精準的學習目標，請先到「<strong>聊天機器人</strong>」頁面設置完整的課程資料：
                    <ul>
                      {!topic && <li>課題</li>}
                      {!selectedSubjectId && <li>科目</li>}
                      {!selectedGradeLevelId && <li>年級</li>}
                    </ul>
                    完成後再回到此頁面生成 ILO。
                  </div>
                  <button 
                    className="reminder-button"
                    onClick={() => setActiveTab("chatbot")}
                  >
                    前往「聊天機器人」頁面設置
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* ILO Category 選擇器 - 改為列表 */}
          <div className="selector-group">
            <label className="subject-label" style={{ marginBottom: "8px" }}>
              ILO 種類（Category）：
            </label>
            {isLoadingCategories ? (
              <div className="loading-text">載入中...</div>
            ) : iloCategories.length === 0 ? (
              <div className="loading-text">無可用種類（請檢查後端連接）</div>
            ) : (
              <div className="category-list">
                {iloCategories.map(category => (
                  <div key={category.id} className="category-item">
                    <label className="category-item-label">
                      <input
                        type="radio"
                        name="category"
                        value={category.id}
                        checked={selectedCategoryId === category.id}
                        onChange={(e) => setSelectedCategoryId(e.target.checked ? parseInt(e.target.value) : null)}
                        className="category-radio"
                      />
                      <div className="category-item-content">
                        <div className="category-item-name">{category.name}</div>
                        {category.description && (
                          <div className="category-item-description">{category.description}</div>
                        )}
                      </div>
                    </label>
                    <button
                      className="template-button"
                      onClick={() => {
                        setShowTemplatesForCategory(category.id);
                      }}
                      aria-label="提供模板"
                    >
                      提供模板
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Bloom Taxonomy 和 Verb 選擇器（僅在 category 需要時顯示） */}
          {selectedCategoryId && (() => {
            const selectedCategory = iloCategories.find(cat => cat.id === selectedCategoryId);
            if (selectedCategory && selectedCategory.show_bloom_taxonomy) {
              return (
                <div className="selector-group">
                  <div className="subject-selector">
                    <label htmlFor="bloom-level-select" className="subject-label">
                      Bloom Taxonomy Level：
                      {selectedCategory.require_bloom_taxonomy && <span style={{ color: "#dc2626" }}> *</span>}
                    </label>
                    <select
                      id="bloom-level-select"
                      className="subject-select"
                      value={selectedBloomLevelId || ""}
                      onChange={(e) => setSelectedBloomLevelId(e.target.value ? parseInt(e.target.value) : null)}
                      disabled={isLoadingBloomLevels}
                    >
                      {isLoadingBloomLevels ? (
                        <option value="">載入中...</option>
                      ) : bloomLevels.length === 0 ? (
                        <option value="">無可用等級</option>
                      ) : (
                        <>
                          <option value="">{selectedCategory.require_bloom_taxonomy ? "（請選擇）" : "（不指定）"}</option>
                          {bloomLevels.map(level => (
                            <option key={level.id} value={level.id}>
                              {getBloomLevelName(level, "zh_HK")}
                            </option>
                          ))}
                        </>
                      )}
                    </select>
                  </div>

                  {selectedBloomLevelId && (
                    <div className="subject-selector">
                      <label htmlFor="verb-select" className="subject-label">
                        動詞（Verb）：
                      </label>
                      <select
                        id="verb-select"
                        className="subject-select"
                        value={selectedVerbId || ""}
                        onChange={(e) => setSelectedVerbId(e.target.value ? parseInt(e.target.value) : null)}
                        disabled={availableVerbs.length === 0}
                      >
                        {availableVerbs.length === 0 ? (
                          <option value="">無可用動詞</option>
                        ) : (
                          <>
                            <option value="">（請選擇）</option>
                            {availableVerbs.map(verb => (
                              <option key={verb.id} value={verb.id}>
                                {getVerbName(verb, "zh_HK")}
                              </option>
                            ))}
                          </>
                        )}
                      </select>
                    </div>
                  )}
                </div>
              );
            }
            return null;
          })()}

          {/* 生成按鈕 */}
          <div className="selector-group">
            <div className="subject-selector">
              <button
                className="generate-ilo-button"
                onClick={generateILOs}
                disabled={isGeneratingILOs || !topic.trim() || !selectedCategoryId || 
                  (selectedCategoryId && (() => {
                    const cat = iloCategories.find(c => c.id === selectedCategoryId);
                    return cat && cat.require_bloom_taxonomy && (!selectedBloomLevelId || !selectedVerbId);
                  })())}
              >
                {isGeneratingILOs ? "生成中..." : "構思預期學習成果"}
              </button>
            </div>
          </div>

          {/* ILO 結果顯示區域 */}
          <div className="ilo-results-area">
            <main className="chat-body" ref={bodyRef}>
              {messages
                .filter(m => {
                  // Display messages containing ILOs, or error messages related to ILO generation (bot role and contains keywords like "生成", "ILO", "課題", etc.)
                  if (m.ilos && Array.isArray(m.ilos) && m.ilos.length > 0) return true;
                  if (m.role === "bot" && m.text && (
                    m.text.includes("生成") || 
                    m.text.includes("ILO") || 
                    m.text.includes("課題") || 
                    m.text.includes("種類") ||
                    m.text.includes("Bloom")
                  )) return true;
                  return false;
                })
                .map(m => (
                <div key={m.id}>
                  {m.text && (
                    <div className={`msg ${m.role}`}>
                      {m.text}
                    </div>
                  )}
                  {m.ilos && Array.isArray(m.ilos) && m.ilos.length > 0 && (
                    <div className="ilos-container">
                      {m.ilos.map((ilo, index) => (
                        <div key={index} className="ilo-item">
                          <div className="ilo-number">{index + 1}</div>
                          <div className="ilo-statement">{ilo.statement}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {messages.filter(m => m.ilos && Array.isArray(m.ilos) && m.ilos.length > 0).length === 0 && (
                <div className="empty-state">
                  <p>生成的預期學習成果將顯示在這裡</p>
                </div>
              )}
            </main>
          </div>
        </div>
      )}

      {/* 從 Action 格式顯示的模板彈出視窗 */}
      {actionTemplates && actionTemplates.presentation === "popup" && (
        <div className="template-modal-overlay" onClick={() => setActionTemplates(null)}>
          <div className="template-modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="template-modal-header">
              <h3 className="template-modal-title">{actionTemplates.context} - 模板</h3>
              <button 
                className="template-modal-close"
                onClick={() => setActionTemplates(null)}
                aria-label="關閉"
              >
                ×
              </button>
            </div>
            <div className="template-modal-body">
              {actionTemplates.patterns.length === 0 ? (
                <div className="no-templates">暫無可用模板</div>
              ) : (
                <div className="templates-list">
                  {actionTemplates.patterns.map((pattern, index) => (
                    <div key={pattern.id || index} className="template-item">
                      <div className="template-statement">
                        {pattern.statement || pattern.text || JSON.stringify(pattern)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 從按鈕點擊顯示的模板彈出視窗 */}
      {showTemplatesForCategory && (() => {
        // Debug info: check data
        console.log("顯示模板 - showTemplatesForCategory:", showTemplatesForCategory);
        console.log("顯示模板 - iloPatterns 總數:", iloPatterns.length);
        console.log("顯示模板 - 前3個 pattern 的 type.id:", iloPatterns.slice(0, 3).map(p => p?.type?.id));
        
        // Use more lenient comparison to ensure type matching
        const categoryPatterns = iloPatterns.filter(pattern => {
          if (!pattern || !pattern.type) {
            return false;
          }
          // Convert to number for comparison to ensure type consistency
          const patternTypeId = Number(pattern.type.id);
          const selectedCategoryId = Number(showTemplatesForCategory);
          return patternTypeId === selectedCategoryId;
        });
        
        console.log("顯示模板 - 匹配的模板數量:", categoryPatterns.length);
        
        // Get selected category name
        const selectedCategory = iloCategories.find(cat => cat.id === showTemplatesForCategory);
        const categoryName = selectedCategory ? selectedCategory.name : "模板";
        
        return (
          <div className="template-modal-overlay" onClick={() => setShowTemplatesForCategory(null)}>
            <div className="template-modal-content" onClick={(e) => e.stopPropagation()}>
              <div className="template-modal-header">
                <h3 className="template-modal-title">{categoryName} - 模板</h3>
                <button 
                  className="template-modal-close"
                  onClick={() => setShowTemplatesForCategory(null)}
                  aria-label="關閉"
                >
                  ×
                </button>
              </div>
              <div className="template-modal-body">
                {isLoadingPatterns ? (
                  <div className="no-templates">載入中...</div>
                ) : categoryPatterns.length === 0 ? (
                  <div className="no-templates">此種類暫無可用模板</div>
                ) : (
                  <div className="templates-list">
                    {categoryPatterns.map(pattern => (
                      <div key={pattern.id} className="template-item">
                        <div className="template-statement">
                          {getPatternStatement(pattern, "zh_HK")}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })()}
    </section>
  );
}