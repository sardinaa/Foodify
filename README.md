# 🍳 Foodify - AI-Powered Food Assistant

**Foodify** is an intelligent food companion that leverages AI to transform how you interact with recipes and meal planning. Upload food images, extract recipes from URLs, get personalized recipe recommendations, and plan your weekly meals—all powered by local LLM and Vision Language Models.

<div align="center">

![Status](https://img.shields.io/badge/Status-MVP%20Complete-success)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Node](https://img.shields.io/badge/Node-18%2B-green)
![License](https://img.shields.io/badge/License-MIT-orange)

</div>

---

## 🌟 Features

### 📸 **Image Analysis Pipeline**
Upload a photo of any dish and let AI do the magic:
- **Visual Recognition**: AI identifies the dish and analyzes ingredients
- **Recipe Generation**: Creates detailed step-by-step cooking instructions
- **Nutrition Calculation**: Provides comprehensive nutritional breakdown (calories, protein, carbs, fats, fiber)
- **Smart Matching**: Uses fuzzy matching against 2,395+ food items for accurate nutrition data

### 🔗 **URL Recipe Extraction**
Extract recipes from your favorite sources:
- **Multi-Platform Support**: YouTube, Instagram, TikTok, food blogs
- **Video Transcription**: Extracts recipes from video content using speech-to-text
- **Social Media Scraping**: Pulls recipes from Instagram posts and stories
- **Structured Parsing**: Converts unstructured content into organized recipes with ingredients and steps

### 🤖 **Intelligent Chat Agent**
Two powerful modes for personalized assistance:

**1. Fridge-to-Recipes Mode**
- Tell the AI what ingredients you have
- Get creative recipe suggestions based on available items
- Considers dietary preferences and constraints

**2. Weekly Menu Planning**
- Generate balanced meal plans for the week
- Customize based on dietary goals, cuisine preferences, and household size
- Optimized for variety and nutritional balance

### 🎯 **Recipe Recommendation System (RAG)**
Powered by ChromaDB vector database and semantic search:
- **Semantic Search**: Find similar recipes based on ingredients and cooking style
- **Context-Aware**: Understands recipe relationships and flavor profiles
- **Conversational Memory**: Maintains chat context for coherent multi-turn interactions

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (Next.js)                  │
│   React + TypeScript + Tailwind CSS + ShadcnUI      │
└────────────────────┬────────────────────────────────┘
                     │ REST API
┌────────────────────┴────────────────────────────────┐
│              Backend (FastAPI + Python)              │
│  ┌──────────────────────────────────────────────┐   │
│  │  API Routes (Image, URL, Chat, RAG)          │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │  Services (Pipelines, Agents, Scrapers)      │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │  AI Clients (Ollama LLM + VLM Integration)   │   │
│  └──────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────┐   │
│  │  Database (SQLAlchemy + SQLite)              │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │              │              │
  ┌───┴───┐    ┌─────┴─────┐  ┌────┴────┐
  │Ollama │    │ ChromaDB  │  │ SQLite  │
  │ LLM   │    │ Vectors   │  │   DB    │
  └───────┘    └───────────┘  └─────────┘
```

### Technology Stack

**Backend**
- **Framework**: FastAPI (async Python web framework)
- **Database**: SQLite with SQLAlchemy ORM
- **AI Models**: Ollama (local LLM & Vision models)
- **Vector DB**: ChromaDB for semantic search
- **Data Processing**: Pandas, RapidFuzz (fuzzy matching)
- **Web Scraping**: BeautifulSoup4, httpx, yt-dlp
- **Transcription**: Faster-Whisper for video-to-text

**Frontend**
- **Framework**: Next.js 14 (React 18+)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Custom React components
- **API Client**: Fetch API with TypeScript types

**Data & ML**
- **Nutrition Dataset**: 2,395 food items (Kaggle)
- **Embeddings**: Sentence Transformers
- **RAG Framework**: LangChain
- **Vector Store**: ChromaDB

---

## 📊 Data

### Nutrition Database
- **Source**: Kaggle Food Nutrition Dataset
- **Coverage**: 2,395 unique food items across 5 food groups
- **Metrics**: Calories, Protein, Carbs, Fat, Dietary Fiber (per 100g)
- **Location**: `data/nutrition_data.csv`
- **Quality**: Cleaned, normalized, and deduplicated

### Recipe Embeddings
- **Vector Database**: ChromaDB
- **Embedding Model**: all-MiniLM-L6-v2 (Sentence Transformers)
- **Purpose**: Semantic recipe search and recommendations

---

## 🚀 Quick Start

### Prerequisites

Before you begin, ensure you have the following installed:

| Tool | Version | Purpose |
|------|---------|---------|
| **Python** | 3.10+ | Backend runtime |
| **Node.js** | 18+ | Frontend runtime |
| **npm** | 8+ | Package manager |
| **Ollama** | Latest | Local AI models |

### 1️⃣ Install Ollama and Models

1. **Install Ollama**: Visit [ollama.ai](https://ollama.ai) and follow installation instructions for your OS

2. **Pull Required Models**:
```bash
# Language model for chat and text processing
ollama pull llama3.2

# Vision model for image analysis
ollama pull llama3.2-vision
```

3. **Verify Installation**:
```bash
ollama list
# Should show: llama3.2 and llama3.2-vision
```

### 2️⃣ Automated Setup (Recommended)

Run the setup script to automatically configure everything:

```bash
# Clone the repository
git clone https://github.com/yourusername/Foodify.git
cd Foodify

# Make setup script executable
chmod +x setup.sh

# Run automated setup
./setup.sh
```

The script will:
- ✅ Check all prerequisites
- ✅ Set up Python virtual environment
- ✅ Install backend dependencies
- ✅ Configure environment variables
- ✅ Initialize the database
- ✅ Install frontend dependencies
- ✅ Validate the installation

### 3️⃣ Manual Setup (Alternative)

#### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOL
API_HOST=0.0.0.0
API_PORT=8000
DATABASE_URL=sqlite:///./foodify.db
NUTRITION_DATA_PATH=../data/nutrition_data.csv
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
VLM_PROVIDER=ollama
VLM_BASE_URL=http://localhost:11434
VLM_MODEL=llama3.2-vision
EOL

# Initialize database (optional - auto-created on first run)
python -c "from app.db.models import Base; from app.db.session import engine; Base.metadata.create_all(bind=engine)"
```

#### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env.local file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local
```

### 4️⃣ Running the Application

You can run both services using the start script or manually:

#### Option A: Using Start Script (Recommended)

```bash
# From project root
./start.sh
```

This will start both backend and frontend in the background.

#### Option B: Manual Start

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate  # On Windows: venv\Scripts\activate
python -m app.main
# OR
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### 5️⃣ Access the Application

Once both services are running:

- **Frontend App**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

---

## 📖 How to Use

### 📸 Image Analysis

1. **Navigate to the Image Analysis tab** in the web interface
2. **Upload a food image** - drag & drop or click to select
3. **Add optional context** - provide a dish name or description for better results
4. **Analyze** - Click the analyze button and wait for AI processing
5. **View Results**:
   - Dish name and description
   - Complete ingredient list with quantities
   - Step-by-step cooking instructions
   - Nutritional breakdown (calories, protein, carbs, fats, fiber)
   - Per-serving and total nutrition values

**Example Use Cases:**
- Identify unknown dishes from restaurant photos
- Extract recipes from cookbook images
- Get nutrition info for homemade meals
- Analyze ingredient composition

### 🔗 URL Recipe Extraction

1. **Navigate to the URL Analysis tab**
2. **Paste a recipe URL** from supported platforms:
   - YouTube recipe videos
   - Instagram recipe posts
   - TikTok cooking videos
   - Food blogs and recipe websites
3. **Extract** - Click to process the URL
4. **Review Results**:
   - Automatically parsed ingredients
   - Organized cooking steps
   - Estimated prep/cook time
   - Nutritional analysis

**Supported Sources:**
- YouTube (video transcription)
- Instagram (post scraping)
- TikTok (video content)
- Recipe websites (structured data extraction)

### 💬 Chat & Planning

#### Mode 1: Fridge-to-Recipes
1. **Select "What's in your fridge?"** mode
2. **List your ingredients** - e.g., "I have chicken, tomatoes, pasta, and basil"
3. **Set preferences** (optional) - dietary restrictions, cuisine type, cooking time
4. **Get recommendations** - AI suggests recipes you can make
5. **View detailed recipes** - Click on suggestions to see full recipe and nutrition

#### Mode 2: Weekly Menu Planning
1. **Select "Weekly Menu Planning"** mode
2. **Provide constraints**:
   - Number of people
   - Dietary preferences (vegetarian, keto, etc.)
   - Cuisine preferences
   - Budget considerations
3. **Generate plan** - Get a complete weekly meal plan
4. **Review meals** - Browse breakfast, lunch, dinner for each day
5. **Adjust as needed** - Ask for alternatives or modifications

**Chat Features:**
- **Context awareness** - Remembers previous conversation
- **Follow-up questions** - Refine recommendations iteratively
- **Recipe details** - Expand any suggested recipe for full details
- **Shopping lists** - Generate ingredient lists for planned meals

---

## 🔌 API Reference

### Core Endpoints

#### `POST /api/image/analyze`
Analyze a food image and extract recipe with nutrition.

**Request:**
```json
{
  "image": "base64_encoded_image_data",
  "title": "Optional dish name"
}
```

**Response:**
```json
{
  "recipe_name": "Spaghetti Carbonara",
  "ingredients": [...],
  "instructions": [...],
  "nutrition": {
    "per_serving": {...},
    "total": {...}
  }
}
```

#### `POST /api/url/analyze`
Extract recipe from a URL (video, social media, blog).

**Request:**
```json
{
  "url": "https://youtube.com/watch?v=...",
  "platform": "youtube"
}
```

**Response:**
```json
{
  "recipe_name": "...",
  "ingredients": [...],
  "instructions": [...],
  "nutrition": {...}
}
```

#### `POST /api/chat`
Interact with the chat agent for recipe suggestions or meal planning.

**Request:**
```json
{
  "message": "I have chicken and rice",
  "mode": "fridge_to_recipes",
  "conversation_id": "optional_session_id"
}
```

**Response:**
```json
{
  "response": "AI generated response",
  "recipes": [...],
  "conversation_id": "session_id"
}
```

#### `GET /api/rag/search`
Search for similar recipes using semantic search.

**Query Parameters:**
- `query`: Search query (ingredients, dish name, etc.)
- `limit`: Number of results (default: 5)

**Response:**
```json
{
  "results": [
    {
      "recipe_name": "...",
      "similarity_score": 0.85,
      "ingredients": [...],
      "instructions": [...]
    }
  ]
}
```

### Additional Endpoints

- `GET /api/recipes` - List all saved recipes
- `GET /api/recipes/{id}` - Get specific recipe
- `DELETE /api/recipes/{id}` - Delete a recipe
- `GET /api/chat/history` - Get chat conversation history
- `DELETE /api/chat/clear` - Clear chat history

**Interactive API Documentation**: Visit http://localhost:8000/docs for full API playground

---

## 📁 Project Structure

```
Foodify/
├── backend/                      # Python FastAPI Backend
│   ├── app/
│   │   ├── main.py              # Application entry point
│   │   ├── api/                 # API route handlers
│   │   │   ├── routes_image.py  # Image analysis endpoints
│   │   │   ├── routes_url.py    # URL extraction endpoints
│   │   │   ├── routes_chat.py   # Chat agent endpoints
│   │   │   └── routes_rag.py    # RAG search endpoints
│   │   ├── services/            # Business logic
│   │   │   ├── image_pipeline.py          # Image-to-recipe pipeline
│   │   │   ├── url_pipeline.py            # URL extraction pipeline
│   │   │   ├── chat_agent.py              # Chat & planning agent
│   │   │   ├── recipe_rag.py              # RAG system
│   │   │   ├── recipe_vectorstore.py      # Vector DB management
│   │   │   ├── social_media_scraper.py    # Social media extraction
│   │   │   ├── video_transcript.py        # Video transcription
│   │   │   └── conversation_memory.py     # Chat context management
│   │   ├── core/                # Core configurations
│   │   │   ├── config.py        # App settings
│   │   │   ├── llm_client.py    # LLM integration
│   │   │   └── vlm_client.py    # Vision model integration
│   │   ├── db/                  # Database layer
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   ├── schema.py        # Pydantic schemas
│   │   │   ├── session.py       # DB session management
│   │   │   ├── crud_recipes.py  # Recipe CRUD operations
│   │   │   ├── crud_chat.py     # Chat history operations
│   │   │   └── crud_menus.py    # Menu planning operations
│   │   ├── utils/               # Utilities
│   │   │   ├── nutrition_lookup.py   # Fuzzy nutrition matching
│   │   │   ├── recipe_parser.py      # Recipe text parsing
│   │   │   ├── text_cleaning.py      # Text preprocessing
│   │   │   ├── unit_conversion.py    # Unit conversions
│   │   │   └── prompt_loader.py      # Prompt management
│   │   └── prompts/             # AI prompts
│   │       ├── llm_prompts.json
│   │       ├── vlm_prompts.json
│   │       └── rag_prompts.json
│   ├── tests/                   # Unit tests
│   ├── requirements.txt         # Python dependencies
│   └── foodify.db              # SQLite database
│
├── frontend/                    # Next.js Frontend
│   ├── app/                     # Next.js 14 App Router
│   │   ├── page.tsx            # Home page
│   │   ├── layout.tsx          # Root layout
│   │   ├── chat/               # Chat interface
│   │   ├── recipes/            # Recipe browsing
│   │   └── globals.css         # Global styles
│   ├── components/              # React components
│   │   ├── ImageAnalysis.tsx   # Image upload & analysis
│   │   ├── UrlAnalysis.tsx     # URL extraction interface
│   │   ├── ChatPlanning.tsx    # Chat interface
│   │   ├── RecipeCard.tsx      # Recipe display card
│   │   ├── RecipeDetailModal.tsx
│   │   ├── RecipeDisplay.tsx
│   │   ├── FilterPanel.tsx
│   │   └── TabNavigation.tsx
│   ├── lib/                     # Frontend utilities
│   │   ├── apiClient.ts        # API communication
│   │   └── utils.ts            # Helper functions
│   ├── public/                  # Static assets
│   ├── package.json            # Node dependencies
│   └── tsconfig.json           # TypeScript config
│
├── data/                        # Data files
│   ├── nutrition_data.csv      # Nutrition database
│   └── nutrition_eda.ipynb     # Data exploration notebook
│
├── chroma_db/                   # ChromaDB vector store
├── setup.sh                     # Automated setup script
├── start.sh                     # Application start script
└── README.md                    # This file
```

---

## ⚙️ Configuration

### Backend Environment Variables (`.env`)

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=sqlite:///./foodify.db

# Data Sources
NUTRITION_DATA_PATH=../data/nutrition_data.csv

# LLM Configuration
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048

# Vision Language Model
VLM_PROVIDER=ollama
VLM_BASE_URL=http://localhost:11434
VLM_MODEL=llama3.2-vision
VLM_TEMPERATURE=0.5

# Vector Store (RAG)
CHROMA_PERSIST_DIRECTORY=./chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Optional: External APIs
# YOUTUBE_API_KEY=your_key_here  # For enhanced video extraction
```

### Frontend Environment Variables (`.env.local`)

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Optional: Analytics
# NEXT_PUBLIC_GA_ID=your_google_analytics_id
```

### Customization Options

#### Switch AI Models

To use different Ollama models, update `.env`:
```env
# For faster inference (smaller model)
LLM_MODEL=llama3.2:1b
VLM_MODEL=llava

# For better quality (larger model)
LLM_MODEL=llama3.2:70b
VLM_MODEL=llama3.2-vision:90b
```

#### Configure RAG System

Adjust vector store settings in `backend/app/services/recipe_vectorstore.py`:
```python
# Change embedding model
EMBEDDING_MODEL = "all-mpnet-base-v2"  # Better quality

# Adjust search parameters
TOP_K = 10  # Return more results
SIMILARITY_THRESHOLD = 0.7  # Stricter matching
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run specific test file
pytest tests/test_nutrition.py

# Run with coverage
pytest --cov=app tests/
```

### Frontend Tests

```bash
cd frontend

# Run tests (if configured)
npm test

# Type checking
npm run type-check

# Linting
npm run lint
```

---

## 🚧 Limitations & Future Enhancements

### Current Limitations

- **Nutrition Accuracy**: Values are estimates based on fuzzy matching; not medical-grade
- **AI Dependency**: Quality depends on Ollama model performance
- **Local Processing**: Requires local compute resources for AI models
- **Simple Unit Conversion**: Basic metric/imperial conversions only
- **No User Authentication**: Single-user MVP design
- **Limited Recipe Database**: Initial RAG system needs more recipe data

### Planned Enhancements

- [ ] User authentication and multi-user support
- [ ] Recipe favorites and collections
- [ ] Shopping list generation with grocery store integration
- [ ] Meal prep scheduling and reminders
- [ ] Dietary goal tracking (calories, macros)
- [ ] Recipe rating and reviews
- [ ] Social sharing features
- [ ] Mobile app (React Native)
- [ ] Advanced nutrition analysis (vitamins, minerals)
- [ ] Ingredient substitution suggestions
- [ ] Cost estimation and budget tracking
- [ ] Integration with smart kitchen appliances

---

## 🤝 Contributing

Contributions are welcome! This is an educational project showcasing full-stack AI integration.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style and conventions
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

**Disclaimer**: This is an educational project for demonstration purposes. Nutritional information is approximate and should not replace professional dietary advice.

---

## 👨‍💻 Author

Built as a technical showcase demonstrating:
- Full-stack development (Python + TypeScript)
- AI/ML integration (LLMs, Vision Models, RAG)
- Modern web architecture (FastAPI + Next.js)
- Data engineering (ETL, vector databases)
- API design and documentation

---

## 🙏 Acknowledgments

- **Ollama** - For local AI model infrastructure
- **Kaggle** - Food nutrition dataset
- **FastAPI** - Modern Python web framework
- **Next.js** - React framework
- **ChromaDB** - Vector database for RAG
- **LangChain** - RAG framework
- **Hugging Face** - Embedding models

---

<div align="center">

**⭐ Star this repo if you find it helpful!**

Made with ❤️ and 🤖

</div>
