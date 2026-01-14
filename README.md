## Prerequisites

Before you begin, you'll need:

1. **Python 3.10+** installed
2. **Google Chrome** browser (for Web Speech API)
3. **Google Cloud Account** with billing enabled

---

## Setup Guide

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/role-play-demo.git
cd role-play-demo
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Set Up Google Cloud

#### 4.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click the project dropdown → **New Project**
3. Name it (e.g., `role-play-demo`) → **Create**
4. Select your new project

#### 4.2 Enable Required APIs

Go to **APIs & Services → Library** and enable these APIs:

| API | Search Term |
|-----|-------------|
| Cloud Speech-to-Text API | `speech to text` |
| Cloud Text-to-Speech API | `text to speech` |
| Generative Language API (Gemini) | `generative language` |

For each: Click on it → Click **Enable**

#### 4.3 Create Service Account

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → Service Account**
3. Name: `role-play-service`
4. Click **Create and Continue**
5. Role: Select **Project → Editor**
6. Click **Done**

#### 4.4 Download Service Account Key

1. Click on your new service account
2. Go to **Keys** tab
3. Click **Add Key → Create new key**
4. Select **JSON** → **Create**
5. Save the downloaded file as `credentials.json` in your project folder

#### 4.5 Get Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click **Create API Key**
3. Select your project
4. Copy the API key

#### 4.6 Enable Billing

1. In Cloud Console, go to **Billing**
2. Link a billing account (new accounts get $300 free credits)

### Step 5: Configure Environment Variables

Create a `.env` file in your project root:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Path to your service account JSON file
GOOGLE_APPLICATION_CREDENTIALS=/full/path/to/your/credentials.json

# Your Gemini API key from AI Studio
GOOGLE_API_KEY=AIzaSy...your-key-here

# Your Google Cloud project ID
GOOGLE_CLOUD_PROJECT=your-project-id
```

### Step 6: Run the Application

```bash
source venv/bin/activate  # If not already activated
uvicorn app.main:app --reload
```

### Step 7: Open in Browser

1. Open **Google Chrome** (required for speech recognition)
2. Go to `http://localhost:8000`
3. Click **Start Conversation**
4. **Allow microphone access** when prompted
5. Start practicing your sales pitch!

---

## Usage

### Starting a Conversation

1. Click **Start Conversation**
2. Allow microphone access
3. Speak naturally - your words appear as you talk
4. The AI buyer will respond with voice

### Text Input (Alternative)

If voice isn't working, you can type messages in the text box at the bottom.

### Ending & Getting Feedback

1. Click **Stop** when you're done
2. Wait for the coaching assessment to generate
3. Review your score and feedback

---

## Coaching Assessment

When you stop the conversation, you'll receive:

- **Overall Score** (1-10)
- **Summary** of how the conversation went
- **Strongest Points** - What you did well
- **Areas for Improvement** - Where to focus
- **Key Opportunities Missed** - Pain points you didn't uncover
- **One Key Tip** - Most important takeaway

---

## Project Structure

```
role-play-demo/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI server & WebSocket handler
│   ├── config.py            # Environment configuration
│   ├── characters.py        # AI buyer persona definition
│   ├── conversation.py      # Conversation state management
│   └── services/
│       ├── __init__.py
│       ├── gemini.py        # Google Gemini integration
│       ├── speech_to_text.py # Google Cloud STT
│       └── text_to_speech.py # Google Cloud TTS
├── static/
│   ├── css/
│   │   └── style.css        # UI styling
│   └── js/
│       └── app.js           # Frontend logic
├── templates/
│   └── index.html           # Main page
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── .gitignore
└── README.md
```

---

## Customizing the Buyer Persona

Edit `app/characters.py` to modify the buyer's:

- **Background** - Company info, role
- **Priorities** - What they care about
- **Pain Points** - Hidden problems to uncover
- **Behavior** - How they respond to questions

---

## Troubleshooting

### "Speech recognition not supported"
- Use **Google Chrome** - other browsers may not support Web Speech API

### Microphone not working
- Check Chrome's address bar for microphone icon
- Click it and ensure the site has permission
- Try refreshing the page

### No audio playback
- Check your system volume
- Click anywhere on the page (browser autoplay policy)
- Check Chrome DevTools console for errors

### "API key not valid" errors
- Verify your `.env` file has correct values
- Make sure APIs are enabled in Google Cloud Console
- Check that billing is enabled

### Assessment not appearing
- Make sure you had at least 2-3 exchanges before stopping
- Check the browser console for errors

---

## API Costs

This app uses Google Cloud APIs which have costs:

| Service | Free Tier | After Free Tier |
|---------|-----------|-----------------|
| Speech-to-Text | 60 min/month | $0.006/15 sec |
| Text-to-Speech | 1M chars/month | $4/1M chars |
| Gemini API | Generous free tier | Pay per token |

New Google Cloud accounts get **$300 free credits** for 90 days.

---

## Tech Stack

- **Backend**: Python, FastAPI, WebSockets
- **Frontend**: HTML, CSS, JavaScript
- **Speech Recognition**: Chrome Web Speech API
- **AI Model**: Google Gemini
- **Text-to-Speech**: Google Cloud TTS

---

## License

MIT License - feel free to use and modify for your own training purposes.

---

## Contributing

Contributions welcome! Feel free to:
- Add new buyer personas
- Improve the assessment criteria
- Enhance the UI
- Fix bugs

---

## Support

If you encounter issues, please open a GitHub issue with:
- Your OS and Python version
- Browser and version
- Error messages from console/terminal
- Steps to reproduce
