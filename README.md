# LDS Chatbot

Learning Design Studio Chatbot - An AI-powered chatbot for learning design and curriculum planning.

## Requirements

- Python 3.8+
- Node.js 16+
- npm or yarn

## Local Deployment Steps

### 1. Clone or Download the Project

```bash
cd LDS-Chatbot
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If you encounter installation issues with `PyPDF2` or `python-docx`, you can skip them (these are optional, used for file parsing).

### 3. Install Frontend Dependencies

```bash
npm install
```

### 4. Set Environment Variables

**Required Environment Variables:**

- `AZURE_OPENAI_API_KEY` - Azure OpenAI API Key (required)

**Optional Environment Variables:**

- `ENDPOINT_URL` - Azure OpenAI Endpoint URL (default: `https://cite-icdevai04-openai-andy-usnc.openai.azure.com/`)
- `AZURE_OPENAI_DEPLOYMENT` - Deployment name (default: `gpt-4.1`)
- `AZURE_OPENAI_API_VERSION` - API version (default: `2025-01-01-preview`)
- `LDS_TOKEN` - LDS API Token (for fetching subjects, grade levels, etc.)
- `LDS_BASE` - LDS API Base URL (default: `https://lds.cite.hku.hk/api`)
- `PORT` - Flask backend port (default: `5000`)

**Windows (PowerShell):**
```powershell
$env:AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
$env:LDS_TOKEN="your-lds-token"  # Optional
$env:ENDPOINT_URL="https://cite-icdevai04-openai-andy-usnc.openai.azure.com/"  # Optional
$env:AZURE_OPENAI_DEPLOYMENT="gpt-4.1"  # Optional
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

**Or create a `.env` file (if using python-dotenv):**
```env
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
LDS_TOKEN=your-lds-token
ENDPOINT_URL=https://cite-icdevai04-openai-andy-usnc.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2025-01-01-preview
LDS_BASE=https://lds.cite.hku.hk/api
PORT=5000
```

## Running the Application

### Method 1: Start Separately (Recommended for Development)

**Step 1 - Start Flask Backend:**

Open the first terminal window, set environment variables and start the backend:

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

The backend will run on `http://localhost:5000`

**Step 2 - Start Vite Frontend:**

Open a second terminal window:
```bash
npm run dev
```

The frontend will run on `http://localhost:5173`

### Method 2: Using Startup Script (Windows)

Create a `start.ps1` file:
```powershell
# Set environment variables
$env:AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
$env:LDS_TOKEN="your-lds-token"  # Optional

# Start backend (in new window)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; `$env:AZURE_OPENAI_API_KEY='your-azure-openai-api-key'; python app.py"

# Wait for backend to start
Start-Sleep -Seconds 3

# Start frontend
npm run dev
```

Then run:
```powershell
.\start.ps1
```

### Method 3: Using Startup Script (Linux/Mac)

Create a `start.sh` file:
```bash
#!/bin/bash

# Set environment variables
export AZURE_OPENAI_API_KEY="your-azure-openai-api-key"
export LDS_TOKEN="your-lds-token"  # Optional

# Start backend (in background)
python app.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
npm run dev

# Stop backend when frontend stops
trap "kill $BACKEND_PID" EXIT
```

Then run:
```bash
chmod +x start.sh
./start.sh
```

## Accessing the Application

### Local Access
Open your browser and visit: `http://localhost:5173`

### Access via IP Address (Share with Users on Same Network)

1. **Get your IP address:**
   
   **Windows:**
   ```powershell
   ipconfig
   ```
   Look for "IPv4 Address", e.g., `10.64.141.53`
   
   **Linux/Mac:**
   ```bash
   ifconfig
   # or
   ip addr show
   ```

2. **After starting the application, others can access it via:**
   ```
   http://<your-ip-address>:5173
   ```
   Example: `http://10.64.141.53:5173`

3. **Notes:**
   - Ensure your firewall allows connections on ports 5173 and 5000
   - Ensure all devices are on the same network
   - Both backend and frontend need to display network access addresses when starting

## Troubleshooting

### Backend Cannot Start

1. **Check Python version:**
   ```bash
   python --version  # Should be 3.8 or higher
   ```

2. **Check if dependencies are installed:**
   ```bash
   pip list
   ```
   Ensure the following packages are installed:
   - Flask
   - flask-cors
   - requests
   - openai

3. **Check if environment variables are set:**
   ```bash
   python -c "import os; print('AZURE_OPENAI_API_KEY:', bool(os.getenv('AZURE_OPENAI_API_KEY')))"
   ```

4. **Check if port is in use:**
   ```bash
   # Windows
   netstat -ano | findstr :5000
   
   # Linux/Mac
   lsof -i :5000
   ```

### Frontend Cannot Connect to Backend

1. **Confirm backend is running:**
   - Check terminal for `Running on http://0.0.0.0:5000` message
   - Visit `http://localhost:5000/api/health` to confirm backend response

2. **Check Vite proxy configuration:**
   - Confirm proxy in `vite.config.js` is set to `http://localhost:5000`

3. **Check browser console:**
   - Open browser developer tools (F12)
   - Check Console and Network tabs for error messages

### Azure OpenAI Authentication Failed

1. **Check API Key:**
   ```bash
   python -c "import os; print('API Key set:', bool(os.getenv('AZURE_OPENAI_API_KEY')))"
   ```

2. **Check Endpoint URL:**
   - Confirm `ENDPOINT_URL` environment variable is set correctly
   - Confirm endpoint URL ends with `/`

3. **Check backend logs:**
   - Check error messages in terminal
   - Confirm Azure OpenAI client initialized successfully

### LDS API Authentication Failed (401)

1. **Check LDS_TOKEN:**
   - Confirm `LDS_TOKEN` is set correctly
   - Confirm token is valid and not expired

2. **Check backend logs:**
   - Check error messages in terminal
   - Confirm LDS API requests are successful

### File Upload Feature Not Working

1. **Check file parsing libraries:**
   ```bash
   pip install PyPDF2 python-docx
   ```
   These libraries are optional; if not installed, PDF/DOCX parsing features will be unavailable

2. **Check file size:**
   - Confirm uploaded files don't exceed server limits
   - Check error messages in backend logs

## Project Structure

```
LDS-Chatbot/
├── app.py              # Flask backend main file
├── requirements.txt    # Python dependencies
├── package.json       # Node.js dependencies
├── vite.config.js     # Vite configuration
├── src/
│   ├── App.jsx        # React main component
│   ├── main.jsx       # React entry point
│   └── styles.css     # Stylesheet
└── index.html         # HTML template
```

## Features

- **Intelligent Chatbot Interface**: Socratic guidance methodology that asks questions to guide users through learning design
- **ILO Generation Tool**: Structured workflow for creating Intended Learning Outcomes with category selection, Bloom's Taxonomy levels, and verb selection
- **Document Analysis**: Upload teaching documents (PDF, DOCX, TXT) for AI-powered analysis and improvement suggestions
- **Smart Suggestions**: AI-generated follow-up questions to help users continue conversations naturally
- **Multi-language Support**: Traditional Chinese, English, and Simplified Chinese
- **Context-aware Assistance**: Uses course information (topic, subject, grade level) for personalized guidance

## Technology Stack

- **Frontend**: React + Vite
- **Backend**: Flask (Python)
- **AI**: Azure OpenAI (GPT-4)
- **Integration**: LDS API for educational data
