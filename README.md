# LDS Chatbot

Learning Design Studio Chatbot - 一個用於學習設計和課程規劃的聊天機器人。

## 環境要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

## 本地部署步驟

### 1. 克隆或下載項目

```bash
cd LDS-Chatbot
```

### 2. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

**注意：** 如果遇到 `PyPDF2` 或 `python-docx` 安裝問題，可以跳過（這些是可選的，用於文件解析）。

### 3. 安裝前端依賴

```bash
npm install
```

### 4. 設置環境變數

**必須設置的環境變數：**

- `AZURE_OPENAI_API_KEY` - Azure OpenAI API Key（必需）

**可選的環境變數：**

- `ENDPOINT_URL` - Azure OpenAI Endpoint URL（默認：`https://cite-icdevai04-openai-andy-usnc.openai.azure.com/`）
- `AZURE_OPENAI_DEPLOYMENT` - 部署名稱（默認：`gpt-4.1`）
- `AZURE_OPENAI_API_VERSION` - API 版本（默認：`2025-01-01-preview`）
- `LDS_TOKEN` - LDS API Token（用於獲取科目、年級等選項）
- `LDS_BASE` - LDS API 基礎 URL（默認：`https://lds.cite.hku.hk/api`）
- `PORT` - Flask 後端端口（默認：`5000`）

**Windows (PowerShell):**
```powershell
$env:AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
$env:LDS_TOKEN="your-lds-token"  # 可選
$env:ENDPOINT_URL="https://cite-icdevai04-openai-andy-usnc.openai.azure.com/"  # 可選
$env:AZURE_OPENAI_DEPLOYMENT="gpt-4.1"  # 可選
```

**Windows (CMD):**
```cmd
set AZURE_OPENAI_API_KEY=your-azure-openai-api-key
set LDS_TOKEN=your-lds-token
set ENDPOINT_URL=https://cite-icdevai04-openai-andy-usnc.openai.azure.com/
set AZURE_OPENAI_DEPLOYMENT=gpt-4.1
```

**Linux/Mac:**
```bash
export AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
export LDS_TOKEN="your-lds-token"
export ENDPOINT_URL="https://cite-icdevai04-openai-andy-usnc.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="gpt-4.1"
```

**或者創建 `.env` 文件（如果使用 python-dotenv）：**
```env
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
LDS_TOKEN=your-lds-token
ENDPOINT_URL=https://cite-icdevai04-openai-andy-usnc.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2025-01-01-preview
LDS_BASE=https://lds.cite.hku.hk/api
PORT=5000
```

## 運行應用

### 方法 1: 分別啟動（推薦用於開發）

**步驟 1 - 啟動 Flask 後端:**

打開第一個終端窗口，設置環境變數並啟動後端：

**Windows (PowerShell):**
```powershell
$env:AZURE_OPENAI_API_KEY="your-api-key"
python app.py
```

**Windows (CMD):**
```cmd
set AZURE_OPENAI_API_KEY=your-api-key
python app.py
```

**Linux/Mac:**
```bash
export AZURE_OPENAI_API_KEY="your-api-key"
python app.py
```

後端將運行在 `http://localhost:5000`

**步驟 2 - 啟動 Vite 前端:**

打開第二個終端窗口：
```bash
npm run dev
```

前端將運行在 `http://localhost:5173`

### 方法 2: 使用啟動腳本（Windows）

創建 `start.ps1` 文件：
```powershell
# 設置環境變數
$env:AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
$env:LDS_TOKEN="your-lds-token"  # 可選

# 啟動後端（在新窗口）
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:AZURE_OPENAI_API_KEY='your-azure-openai-api-key'; python app.py"

# 等待後端啟動
Start-Sleep -Seconds 3

# 啟動前端
npm run dev
```

然後運行：
```powershell
.\start.ps1
```

### 方法 3: 使用啟動腳本（Linux/Mac）

創建 `start.sh` 文件：
```bash
#!/bin/bash

# 設置環境變數
export AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
export LDS_TOKEN="your-lds-token"  # 可選

# 啟動後端（在背景）
python app.py &
BACKEND_PID=$!

# 等待後端啟動
sleep 3

# 啟動前端
npm run dev

# 當前端停止時，也停止後端
trap "kill $BACKEND_PID" EXIT
```

然後運行：
```bash
chmod +x start.sh
./start.sh
```

## 訪問應用

### 本地訪問
打開瀏覽器訪問：`http://localhost:5173`

### 通過 IP 地址訪問（分享給同網絡用戶）

1. **獲取你的 IP 地址：**
   
   **Windows:**
   ```powershell
   ipconfig
   ```
   查找 "IPv4 Address"，例如：`10.64.141.53`
   
   **Linux/Mac:**
   ```bash
   ifconfig
   # 或
   ip addr show
   ```

2. **啟動應用後，其他人可以通過以下地址訪問：**
   ```
   http://<你的IP地址>:5173
   ```
   例如：`http://10.64.141.53:5173`

3. **注意事項：**
   - 確保你的防火牆允許端口 5173 和 5000 的連接
   - 確保所有設備都在同一網絡中
   - 後端和前端都需要在啟動時顯示網絡訪問地址

## 故障排除

### 後端無法啟動

1. **檢查 Python 版本：**
   ```bash
   python --version  # 應該是 3.8 或更高
   ```

2. **檢查依賴是否安裝：**
   ```bash
   pip list
   ```
   確保以下包已安裝：
   - Flask
   - flask-cors
   - requests
   - openai

3. **檢查環境變數是否設置：**
   ```bash
   python -c "import os; print('AZURE_OPENAI_API_KEY:', bool(os.getenv('AZURE_OPENAI_API_KEY')))"
   ```

4. **檢查端口是否被佔用：**
   ```bash
   # Windows
   netstat -ano | findstr :5000
   
   # Linux/Mac
   lsof -i :5000
   ```

### 前端無法連接後端

1. **確認後端正在運行：**
   - 檢查終端是否有 `Running on http://0.0.0.0:5000` 訊息
   - 訪問 `http://localhost:5000/api/health` 確認後端響應

2. **檢查 Vite 代理配置：**
   - 確認 `vite.config.js` 中的 proxy 設置為 `http://localhost:5000`

3. **檢查瀏覽器控制台：**
   - 打開瀏覽器開發者工具（F12）
   - 查看 Console 和 Network 標籤的錯誤訊息

### Azure OpenAI 認證失敗

1. **檢查 API Key：**
   ```bash
   python -c "import os; print('API Key set:', bool(os.getenv('AZURE_OPENAI_API_KEY')))"
   ```

2. **檢查 Endpoint URL：**
   - 確認 `ENDPOINT_URL` 環境變數設置正確
   - 確認 endpoint URL 以 `/` 結尾

3. **查看後端日誌：**
   - 檢查終端中的錯誤訊息
   - 確認 Azure OpenAI client 是否成功初始化

### LDS API 認證失敗 (401)

1. **檢查 LDS_TOKEN：**
   - 確認 `LDS_TOKEN` 是否正確設置
   - 確認 token 是否有效且未過期

2. **查看後端日誌：**
   - 檢查終端中的錯誤訊息
   - 確認 LDS API 請求是否成功

### 文件上傳功能無法使用

1. **檢查文件解析庫：**
   ```bash
   pip install PyPDF2 python-docx
   ```
   這些庫是可選的，如果未安裝，PDF/DOCX 解析功能將不可用

2. **檢查文件大小：**
   - 確認上傳的文件不超過服務器限制
   - 檢查後端日誌中的錯誤訊息

## 項目結構

```
LDS-Chatbot/
├── app.py              # Flask 後端主文件
├── requirements.txt    # Python 依賴
├── package.json       # Node.js 依賴
├── vite.config.js     # Vite 配置
├── src/
│   ├── App.jsx        # React 主組件
│   ├── main.jsx       # React 入口
│   └── styles.css     # 樣式文件
└── index.html         # HTML 模板
```

