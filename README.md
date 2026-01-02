# 💕 Couple Chat AI

A private, secure two-person chat platform with AI-powered features, encrypted messaging, and romantic UI design.

## ✨ Features

### Core Messaging
- **Private Two-Person Rooms**: Maximum 2 users per room with secret codes
- **Encrypted Messages**: AES-256-GCM encryption for all media files
- **Message Types**: Text, images, and voice messages
- **View Once Images**: Self-destructing images that disappear after viewing
- **Message Reactions**: ❤️ 😂 😢 😮 😠

### AI Features
- **Smart AI Bot**: Mention `@bot` to chat with AI assistant
- **Automatic Persona Switching**: AI adapts tone based on context (NO regex - embedding-based)
  - **Care Mode**: Supportive and empathetic responses
  - **Intimate Mode**: Romantic and affectionate (requires consent)
- **Consent-Aware NSFW**: Both partners must explicitly consent
- **Tap to Remember**: Save important messages to vector memory
- **RAG-Powered Context**: AI remembers your conversations using ChromaDB

### Security
- **Room Secrets**: Password-protected rooms
- **Device Binding**: Optional device verification
- **File Validation**: Size limits and type restrictions
- **Content Safety**: Built-in content moderation

---

## 🏗️ Architecture

```
couple-chat-ai/
├── backend/                 # FastAPI Python backend
│   ├── main.py             # Application entry point
│   ├── config.py           # Settings management
│   ├── core/               # Core modules
│   │   ├── encryption.py   # AES-256-GCM encryption
│   │   ├── security.py     # File validation, room security
│   │   └── supabase_client.py
│   ├── models/             # Pydantic v2 models
│   │   ├── user.py
│   │   ├── room.py
│   │   └── message.py
│   ├── services/           # Business logic
│   │   ├── room_service.py
│   │   ├── message_service.py
│   │   ├── memory_service.py
│   │   └── bot_service.py
│   ├── ai/                 # AI modules
│   │   ├── embeddings.py   # BGE-small embeddings
│   │   ├── rag_index.py    # LlamaIndex + ChromaDB
│   │   ├── orchestrator.py # LangGraph state machine
│   │   └── personas/       # AI personas
│   │       ├── base.py
│   │       ├── care.py
│   │       └── intimate.py
│   ├── routes/             # API endpoints
│   │   ├── rooms.py
│   │   ├── chat.py
│   │   ├── bot.py
│   │   └── memory.py
│   └── ws/                 # WebSocket handling
│       └── connection_manager.py
│
├── frontend/               # Next.js 14 frontend
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   ├── room/[id]/page.tsx
│   │   └── components/
│   │       ├── ChatBubble.tsx
│   │       ├── MessageInput.tsx
│   │       ├── ReactionBar.tsx
│   │       └── RememberButton.tsx
│   ├── package.json
│   └── tailwind.config.js
│
└── supabase_schema.sql     # Database schema
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Supabase Account** (free tier works)
- **Groq API Key** (free tier available at https://console.groq.com/)

### 1. Clone & Setup

```bash
git clone <your-repo>
cd couple-chat-ai
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate
# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Supabase (get from supabase.com dashboard)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Encryption (generate with: python -c "import secrets; print(secrets.token_hex(32))")
ENCRYPTION_KEY=your-64-char-hex-key

# Groq API Configuration
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.1-8b-instant

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_data
```

### 3. Supabase Database Setup

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Create a new project
3. Go to **SQL Editor**
4. Copy contents of `supabase_schema.sql` and run it
5. Go to **Storage** and create a bucket named `media` (public)

### 4. Get Groq API Key

1. Go to [Groq Console](https://console.groq.com/)
2. Sign up for a free account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key and add it to your `.env` file

### 5. Start Backend

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## 🎮 Demo Mode

A demo room is pre-configured for testing:

- **Room ID**: `1`
- **Room Secret**: `12589`

1. Open `http://localhost:3000`
2. Click **"Enter Demo Room"** button
3. Or enter Room ID: `1` and Secret: `12589` manually

---

## 🔧 API Endpoints

### Rooms

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rooms/create` | Create new room |
| POST | `/api/rooms/join` | Join existing room |
| GET | `/api/rooms/{room_id}` | Get room details |
| POST | `/api/rooms/{room_id}/leave` | Leave room |

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/api/chat/ws/{room_id}/{user_id}` | WebSocket connection |
| GET | `/api/chat/history/{room_id}` | Get message history |
| POST | `/api/chat/upload` | Upload media file |
| POST | `/api/chat/view-once/{message_id}` | Mark view-once as viewed |

### Bot

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/bot/chat` | Send message to bot |
| GET | `/api/bot/personas` | List available personas |
| POST | `/api/bot/consent` | Update NSFW consent |

### Memory

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/memory/remember` | Save message to memory |
| GET | `/api/memory/search` | Search memories |
| GET | `/api/memory/categories` | List memory categories |

---

## 🔌 WebSocket Events

### Client → Server

```json
// Send message
{ "event": "message", "data": { "content": "Hello!", "type": "text", "mention_bot": false } }

// Typing indicator
{ "event": "typing", "data": { "is_typing": true } }

// Add reaction
{ "event": "reaction", "data": { "message_id": "uuid", "reaction_type": "heart", "action": "add" } }
```

### Server → Client

```json
// New message
{ "event": "new_message", "data": { "id": "uuid", "content": "...", ... } }

// Typing status
{ "event": "typing_status", "data": { "typing_users": ["user-id"] } }

// Reaction update
{ "event": "reaction_added", "data": { "message_id": "uuid", "reactions": {...} } }
```

---

## 🎨 UI Theme

The frontend uses a **romantic dark-red theme**:

| Color | Hex | Usage |
|-------|-----|-------|
| Background | `#0d0208` | Main background |
| Card | `#1a0a10` | Cards, modals |
| Romantic | `#8B0A1A` | Primary accent |
| Gold | `#D4A574` | Secondary accent |
| Text | `#F5E6D3` | Primary text |

---

## 🛡️ Security Features

### Encryption
- **AES-256-GCM** for all media files
- Unique nonce per file
- Server-side encryption/decryption

### Room Security
- Secret codes for room access
- Maximum 2 users per room
- Device binding (optional)

### Content Safety
- File type validation
- Size limits (10MB default)
- Optional content moderation

---

## 🧠 AI System

### Embedding-Based Intent Classification

The system uses **BGE-small-en-v1.5** embeddings to classify user intent:

```python
# Reference embeddings for each persona
INTENT_REFERENCES = {
    "care": [
        "I'm feeling sad",
        "I need support",
        "comfort me"
    ],
    "intimate": [
        "I love you",
        "kiss me",
        "I want to be close"
    ]
}
```

### LangGraph Orchestrator

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Classify  │────▶│ Check NSFW   │────▶│   Route     │
│   Intent    │     │  Consent     │     │  Persona    │
└─────────────┘     └──────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    ▼                          ▼                          ▼
              ┌──────────┐              ┌──────────┐              ┌──────────┐
              │   Base   │              │   Care   │              │ Intimate │
              │ Persona  │              │ Persona  │              │ Persona  │
              └──────────┘              └──────────┘              └──────────┘
```

### Memory System

- **ChromaDB** for vector storage
- **LlamaIndex** for RAG pipeline
- Categories: general, date, milestone, intimate, inside_joke

---

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Supabase project URL | Yes |
| `SUPABASE_KEY` | Supabase anon key | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key | Yes |
| `ENCRYPTION_KEY` | 64-char hex key | Yes |
| `LLM_PROVIDER` | AI provider (groq/openrouter) | Yes |
| `GROQ_API_KEY` | Groq API key | Yes |
| `GROQ_MODEL` | Model name | Yes |
| `EMBEDDING_MODEL` | HuggingFace model | No |
| `CHROMA_PERSIST_DIR` | ChromaDB storage | No |
| `MAX_FILE_SIZE_MB` | Upload limit | No |

---

## 🚧 Production Deployment

### Backend (Docker)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend (Vercel)

```bash
cd frontend
vercel deploy
```

### Environment Setup
1. Set all environment variables in your deployment platform
2. Use a managed Supabase instance
3. Configure Groq API key for fast LLM inference
4. Ensure ChromaDB persistence is properly configured

---

## 📄 License

MIT License - See LICENSE file for details.

---

## 💖 Made with Love

This project is designed for couples who want a private, secure, and AI-enhanced chat experience.

**Demo Credentials:**
- Room ID: `1`
- Secret: `12589`
