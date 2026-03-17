# 🤖 AI Chatbot Setup Guide

## Issues Fixed

Your chatbot had **3 critical issues**:

### 1. **DOM Timing Bug** ❌ → ✅
- **Problem**: Chat form handler was initialized before DOM elements existed
- **Fix**: Moved initialization into `DOMContentLoaded` event handler
- **Impact**: Chat form now properly attaches to HTML elements

### 2. **Chat History Broken** ❌ → ✅
- **Problem**: Only saved user messages, not bot responses → context lost between messages
- **Old**:
  ```javascript
  chatHistory.push(msg);  // Only user message added
  ```
- **New**:
  ```javascript
  chatHistory.push(msg);      // Add user message
  chatHistory.push(data.reply); // Add bot response
  ```
- **Impact**: AI now maintains proper conversation context

### 3. **Missing Dependency** ❌ → ✅
- **Problem**: `requests` library wasn't in requirements.txt but was imported
- **Fix**: Added `requests==2.31.*` to requirements.txt
- **Impact**: OpenRouter API calls will now work

### 4. **Hardcoded API Key** ⚠️ → ✅
- **Problem**: API key was hardcoded in config.py (security risk)
- **Fix**: Removed fallback key, now only reads from environment variable
- **Impact**: Must set `OPENROUTER_API_KEY` env var to enable chatbot

---

## ✅ Installation & Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Get OpenRouter API Key
1. Go to https://openrouter.ai/
2. Sign up for a free account
3. Generate an API key
4. Copy your key

### Step 3: Set Environment Variable

**Windows (PowerShell):**
```powershell
$env:OPENROUTER_API_KEY = "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"
python app.py
```

**Windows (CMD):**
```cmd
set OPENROUTER_API_KEY=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
python app.py
```

**Linux/Mac:**
```bash
export OPENROUTER_API_KEY="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"
python app.py
```

**Windows (Persistent - Set in System Environment Variables):**
1. `Win + X` → "System"
2. "Advanced system settings"
3. "Environment Variables"
4. New User Variable:
   - Name: `OPENROUTER_API_KEY`
   - Value: `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`
5. Restart terminal/IDE

### Step 4: Test the Chatbot
1. Start the server: `python app.py`
2. Open http://localhost:5000 in browser
3. Log in with your account
4. Look for the **💬 AI Chatbox** in bottom-right corner
5. Type a message like: "What should I feed my dog?"

---

## 🔍 How It Works

### User Message Flow
```
User types "How often should I feed my dog?"
                    ↓
        JavaScript validates message
                    ↓
  POST /api/chat with {message, history}
                    ↓
Backend calls openrouter_chat() function
                    ↓
Sends request to: https://openrouter.ai/api/v1/chat/completions
Model: openchat/openchat-3.5-0106 (fast, free tier)
                    ↓
OpenRouter API returns AI response
                    ↓
Response sent back to frontend as JSON
                    ↓
JavaScript displays response in chatbox
Message added to chatHistory for context
```

### Error Handling
If the chatbot shows an error:
- **"[Error: ...]"** → Check your OpenRouter API key
- **"[Network error: ...]"** → Check internet connection
- **"[OpenRouter API error: ...]"** → API call failed (check logs)

---

## 📝 Verification Checklist

After setup, verify:

- [ ] `OPENROUTER_API_KEY` environment variable is set
- [ ] `requests` library is installed (`pip list | grep requests`)
- [ ] Flask server starts without errors: `python app.py`
- [ ] Chatbox widget appears in bottom-right of dashboard
- [ ] No console errors in browser (F12 → Console tab)
- [ ] Send a test message and receive a response

---

## 🐛 Troubleshooting

### Issue: "OpenRouter API key not set" message
**Solution**: 
- Verify environment variable is set: `echo $OPENROUTER_API_KEY` (Linux/Mac) or `echo %OPENROUTER_API_KEY%` (Windows)
- Restart the Flask server after setting env var
- Check you didn't paste extra spaces or quotes

### Issue: Chatbox doesn't appear
**Solution**:
- Check browser console for JavaScript errors (F12)
- Verify you're logged in (should see pet dashboard)
- Clear browser cache (Ctrl+Shift+Del)

### Issue: Message sends but no response comes back
**Solution**:
- Check Flask server logs for error messages
- Verify `requests` is installed: `python -c "import requests; print('OK')"`
- Check OpenRouter API key is valid at https://openrouter.ai/

### Issue: Response is slow
**Solution**:
- This is normal (API calls take 1-5 seconds)
- Button shows "Send" while processing
- First message may be slower

---

## 🔧 Advanced: Changing the AI Model

To use a different OpenRouter model, edit `ai_engine.py`:

```python
def openrouter_chat(message, history=None, model="openchat/openchat-3.5-0106"):
    # Change this model name to use a different AI
    # Available models: https://openrouter.ai/docs/models
```

**Popular options:**
- `openchat/openchat-3.5-0106` (default - fast FREE tier)
- `meta-llama/llama-2-70b-chat` (more powerful)
- `gpt-3.5-turbo` (requires credits)
- `gpt-4` (expensive)

---

## 📊 API Usage

**Free Tier (OpenRouter):**
- First month: $5 free credit
- Per 1M tokens: ~$0.50-2 depending on model
- Typical chat: ~50-500 tokens per exchange

**Cost Example:**
- 100 messages × 200 tokens avg = 20,000 tokens ≈ $0.01-0.02 (free tier)

---

## ✨ What Your Chatbot Can Do

Try these prompts:
- "What are signs my dog might be sick?"
- "How much should a 20kg dog eat per day?"
- "What's the best feeding schedule for cats?"
- "My pet has diarrhea, what should I do?"
- "When should I call a vet?"

---

## 📞 Support

If problems persist:
1. Check the CODEBASE_ANALYSIS.md for architecture details
2. Review Flask server error logs
3. Check OpenRouter API status: https://status.openrouter.ai/
4. Verify your API key at: https://openrouter.ai/account

