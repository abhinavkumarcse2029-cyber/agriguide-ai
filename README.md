# 🌾 AgriGuide AI

> **IBM watsonx.ai powered Agriculture Assistant for Smart Farming Decisions**

AgriGuide AI is an intelligent agricultural decision support assistant that helps farmers with crop selection, fertilizer scheduling, pest management, disease identification, weather-based advisory, and sustainable farming practices — all through a beautiful AI chat interface powered by **IBM watsonx.ai Granite models**.

---

## 🚀 Live Demo

Deploy on GitHub + Vercel in under 5 minutes (see deployment section below).

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Chat Interface** | ChatGPT-style multilingual chat powered by IBM Granite |
| 🌱 **Crop Recommendation** | Season & soil-based AI crop suggestions |
| 💧 **Fertilizer Guide** | NPK schedules, organic alternatives, deficiency diagnosis |
| 🐛 **Pest Management** | IPM strategies, identification, and safe pesticides |
| 🛡️ **Disease Identification** | Symptom-based disease diagnosis and treatment |
| ☁️ **Weather Advisory** | Climate-smart farming decisions and seasonal alerts |
| ♻️ **Sustainable Farming** | Organic practices, vermicompost, zero-budget natural farming |
| 📊 **Farm Dashboard** | Charts, calendar, and farm analytics |
| 🌍 **9 Languages** | Hindi, Tamil, Telugu, Kannada, Marathi, Bengali, Gujarati, Punjabi, English |
| 🌙 **Dark Mode** | Beautiful dark/light theme toggle |
| 📱 **Mobile Responsive** | Works perfectly on phones, tablets, and desktops |

---

## 🛠️ Tech Stack

- **Backend**: Python Flask 3.0
- **AI/LLM**: IBM watsonx.ai — Granite 3.3 8B Instruct
- **Frontend**: Bootstrap 5, Chart.js, Bootstrap Icons
- **Fonts**: Google Fonts (Inter)
- **Deployment**: Vercel (serverless), Heroku, or Railway

---

## 📁 Project Structure

```
agriguide-ai/
├── app.py                  # Flask backend + watsonx.ai integration
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore
├── vercel.json             # Vercel deployment config
├── Procfile                # Heroku/Railway config
├── runtime.txt             # Python version
├── README.md
├── templates/
│   ├── base.html           # Base template (navbar + footer)
│   ├── index.html          # Landing page
│   ├── chat.html           # AI Chat interface
│   ├── dashboard.html      # Farm analytics dashboard
│   ├── crop.html           # Crop recommendation
│   ├── fertilizer.html     # Fertilizer guide
│   ├── pest.html           # Pest management
│   ├── disease.html        # Disease identification
│   ├── weather.html        # Weather advisory
│   ├── sustainable.html    # Sustainable farming
│   ├── about.html          # About page
│   ├── contact.html        # Contact page
│   ├── 404.html            # Not found page
│   └── 500.html            # Server error page
└── static/
    ├── css/
    │   └── style.css       # Main stylesheet (dark mode + animations)
    └── js/
        └── main.js         # Chat engine + charts + dark mode
```

---

## ⚡ Quick Start (Local Development)

### 1. Prerequisites
- Python 3.10+
- IBM Cloud account with watsonx.ai access
- watsonx.ai Project ID

### 2. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/agriguide-ai.git
cd agriguide-ai

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your IBM credentials
```

Open `.env` and fill in your credentials:

```env
IBM_API_KEY=your_ibm_cloud_api_key_here
IBM_PROJECT_ID=your_watsonx_project_id_here
IBM_URL=https://us-south.ml.cloud.ibm.com
MODEL_NAME=ibm/granite-3-3-8b-instruct
FLASK_SECRET_KEY=your-random-secret-key-here
```

### 4. Get IBM watsonx.ai Credentials

1. Go to [IBM Cloud](https://cloud.ibm.com) → Sign up / Log in
2. Create a **watsonx.ai** service instance
3. Create a new **Project** in watsonx.ai
4. Copy your **Project ID** from project settings
5. Go to **Manage → Access (IAM)** → **API Keys** → Create an API key
6. Copy the API key to your `.env` file

### 5. Run the Application

```bash
python app.py
```

Open your browser at: **http://localhost:5000**

---

## 🔧 Customising the AI Agent

Open [`app.py`](app.py) and modify the `AGENT_INSTRUCTIONS` dictionary at the top of the file:

```python
AGENT_INSTRUCTIONS = {
    # Change the AI personality
    "personality": "friendly, knowledgeable agricultural expert",

    # Change the response tone
    "tone": "professional yet approachable",

    # Add/remove safety rules
    "safety_rules": [
        "Never recommend unsafe pesticide combinations",
        ...
    ],

    # Add specializations
    "specializations": [
        "Smallholder farming",
        "Drip irrigation",
        ...
    ],

    # Change recommendation style
    "recommendation_style": "Bullet points with cost estimates and timelines",
}
```

---

## 🚀 Deployment

### Deploy to Vercel (Recommended)

1. Push your code to GitHub (without `.env`!)
2. Go to [vercel.com](https://vercel.com) → New Project → Import from GitHub
3. Add environment variables in Vercel dashboard:
   - `IBM_API_KEY`
   - `IBM_PROJECT_ID`
   - `IBM_URL`
   - `MODEL_NAME`
   - `FLASK_SECRET_KEY`
4. Click **Deploy**

### Deploy to Heroku

```bash
heroku create agriguide-ai
heroku config:set IBM_API_KEY=your_key
heroku config:set IBM_PROJECT_ID=your_project_id
heroku config:set IBM_URL=https://us-south.ml.cloud.ibm.com
heroku config:set MODEL_NAME=ibm/granite-3-3-8b-instruct
heroku config:set FLASK_SECRET_KEY=your_secret_key
git push heroku main
```

### Deploy to Railway

1. Connect GitHub repo to [Railway](https://railway.app)
2. Add environment variables in Railway dashboard
3. Railway auto-detects Python and deploys

### Deploy with Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
```

```bash
docker build -t agriguide-ai .
docker run -p 5000:5000 --env-file .env agriguide-ai
```

---

## 🌐 Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `IBM_API_KEY` | ✅ | IBM Cloud API Key |
| `IBM_PROJECT_ID` | ✅ | watsonx.ai Project ID |
| `IBM_URL` | ✅ | watsonx.ai endpoint URL |
| `MODEL_NAME` | ✅ | Granite model ID |
| `FLASK_SECRET_KEY` | ✅ | Flask session secret |
| `FLASK_DEBUG` | ❌ | Set `False` in production |
| `PORT` | ❌ | Port (default: 5000) |

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/chat` | POST | Send chat message, get AI response |
| `/api/quick-ask` | POST | One-shot farming question |
| `/api/clear-chat` | POST | Clear session chat history |
| `/api/health` | GET | Health check + config status |
| `/api/crop-data` | GET | Crop season data for dashboard |

### Chat API Example

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What crop should I grow on sandy soil in Rajasthan during Kharif?"}'
```

---

## 🔒 Security Notes

- **Never commit `.env`** — it's in `.gitignore`
- Use **environment variables** for all secrets
- The AI follows strict **safety rules** — no unsafe pesticide advice
- Chat history is **session-based** — not stored permanently
- Set `FLASK_DEBUG=False` in production

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

MIT License — free for personal and commercial use.

---

## 🙏 Acknowledgements

- **IBM watsonx.ai** — Foundation model platform
- **IBM Granite** — Open-source LLM family
- **ICAR** — Indian Council of Agricultural Research knowledge base
- **Bootstrap** — UI framework
- **Chart.js** — Data visualisation

---

**Made with ❤️ for India's 140 million farmers** 🌾
