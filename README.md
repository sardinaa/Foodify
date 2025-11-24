# 🍳 Foodify - AI-Powered Food Assistant

**Foodify** is an intelligent food companion that leverages AI to transform how you interact with recipes and meal planning. Upload food images, extract recipes from URLs, get personalized recipe recommendations, and plan your weekly meals—all powered by local LLM and Vision Language Models.

<div align="center">

![Status](https://img.shields.io/badge/Status-Production%20Ready-success)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Node](https://img.shields.io/badge/Node-18%2B-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-MIT-orange)

</div>

---

## �🌟 Features

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

### 🎯 **Recipe Recommendation System (Full RAG)**
Powered by ChromaDB vector database and semantic search with complete recipe context:
- **Full RAG Implementation**: Semantic search (ChromaDB) + complete recipe retrieval (PostgreSQL/SQLite) + LLM-generated recommendations
- **Complete Context**: Returns full recipes with ingredients, steps, and nutrition—not just metadata
- **Context-Aware**: Understands recipe relationships and flavor profiles
- **Conversational Memory**: Maintains chat context for coherent multi-turn interactions
- **Unified Search**: Single search method handles ingredients, categories, and cooking styles

### 🐳 **Docker Deployment**
Production-ready containerization:
- **Docker Compose**: One-command deployment for both frontend and backend
- **Persistent Storage**: Database and vector store mounted as volumes
- **Health Checks**: Automatic service health monitoring
- **Easy Scaling**: Configure resource limits and replicas
- **Ollama Integration**: Seamless connection to host-based Ollama models

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                 Frontend (Next.js 14)                     │
│  React 18 + TypeScript + Tailwind CSS + ShadcnUI        │
│  Standalone Build (Docker-ready)                         │
└────────────────────┬─────────────────────────────────────┘
                     │ REST API
┌────────────────────┴─────────────────────────────────────┐
│              Backend (FastAPI + Python 3.11)              │
│  ┌───────────────────────────────────────────────────┐   │
│  │  API Routes Layer                                  │   │
│  │  - Image Analysis   - URL Extraction              │   │
│  │  - Chat Agent       - RAG Search                  │   │
│  └───────────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Service Layer (Refactored & Modular)             │   │
│  │  - Pipelines: image_pipeline, url_pipeline        │   │
│  │  - Chat: intent, router, helpers (new modules)    │   │
│  │  - RAG: Full context retrieval + generation       │   │
│  │  - Scrapers: Social media, video transcription    │   │
│  │  - Memory: Conversation context management        │   │
│  └───────────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Core & Utils (Enhanced)                          │   │
│  │  - LLM/VLM Clients  - Constants (NEW)             │   │
│  │  - Config (relative paths) - Serializers (NEW)    │   │
│  │  - JSON Parser (NEW) - Prompt Loader              │   │
│  └───────────────────────────────────────────────────┘   │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Database Layer (SQLAlchemy + SQLite)             │   │
│  │  - Models  - CRUD  - Serializers (unified)        │   │
│  └───────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────┘
                       │
      ┌────────────────┼────────────────┐
      │                │                │
  ┌───┴────┐    ┌──────┴──────┐   ┌────┴────┐
  │Ollama  │    │  ChromaDB   │   │ SQLite  │
  │LLM/VLM │    │(Embeddings) │   │   DB    │
  │(Host)  │    │  + Full RAG │   │         │
  └────────┘    └─────────────┘   └─────────┘

Docker Deployment (Optional):
┌─────────────────────────────────────────┐
│       Docker Compose Orchestration       │
│  ┌─────────────┐    ┌─────────────┐    │
│  │  Frontend   │    │   Backend   │    │
│  │  Container  │◄───┤  Container  │    │
│  └─────────────┘    └─────────────┘    │
│         ▲                  ▲            │
│         │                  │            │
│    Volume Mounts     Host Network       │
│    (database, etc)   (Ollama access)    │
└─────────────────────────────────────────┘
```

### Technology Stack

**Backend** (Production-Ready)
- **Framework**: FastAPI (async Python 3.11+)
- **Database**: SQLite with SQLAlchemy ORM + unified serializers
- **AI Models**: Ollama (local LLM & Vision models)
- **Vector DB**: ChromaDB for semantic search + cached instance
- **RAG System**: Full RAG implementation (retrieval + augmentation + generation)
- **Data Processing**: Pandas, RapidFuzz (fuzzy matching)
- **Web Scraping**: BeautifulSoup4, httpx, yt-dlp
- **Transcription**: Faster-Whisper for video-to-text
- **Configuration**: Centralized constants, relative paths
- **Code Quality**: Modular architecture, DRY principles

**Frontend** (Docker-Ready)
- **Framework**: Next.js 14 (React 18+) with standalone output
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Custom React components
- **API Client**: Fetch API with TypeScript types
- **Build**: Optimized for containerization

**Data & ML**
- **Nutrition Dataset**: 2,395 food items (Kaggle)
- **Embeddings**: Sentence Transformers (all-MiniLM-L6-v2)
- **RAG Framework**: Custom implementation with full context
- **Vector Store**: ChromaDB with metadata + full recipe storage

**DevOps & Deployment**
- **Containerization**: Docker + Docker Compose
- **Configuration**: Environment-based, portable
- **Persistence**: Volume mounts for data and databases
- **Health Checks**: Service monitoring and auto-restart

---

## 📊 Data

### Nutrition Database
- **Source**: Kaggle Food Nutrition Dataset
- **Coverage**: 2,395 unique food items across 5 food groups
- **Metrics**: Calories, Protein, Carbs, Fat, Dietary Fiber (per 100g)
- **Location**: `data/nutrition_data.csv`
- **Quality**: Cleaned, normalized, and deduplicated

### Recipe Dataset
- **Source**: HuggingFace [`datahiveai/recipes-with-nutrition`](https://huggingface.co/datasets/datahiveai/recipes-with-nutrition)
- **Access**: Pulled on-demand during ingestion (`backend/scripts/ingest_data.py`)
- **Storage**: Persisted in SQLite (`backend/foodify.db`) and indexed in ChromaDB (`backend/chroma_db/`)
- **Status**: Legacy CSV dumps (`AkashPS11/recipes_data_food.com`) have been removed in favor of the richer HuggingFace dataset

### Recipe Embeddings
- **Vector Database**: ChromaDB
- **Embedding Model**: all-MiniLM-L6-v2 (Sentence Transformers)
- **Purpose**: Semantic recipe search and recommendations

---

## 🚀 Quick Start with Docker

### Prerequisites

Before you begin, ensure you have the following installed:

| Tool | Version | Purpose |
|------|---------|---------|
| **Docker** | 20.10+ | Container runtime |
| **Docker Compose** | 2.0+ | Multi-container orchestration |
| **Ollama** | Latest | Local AI models (LLM/VLM) |

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

### 2️⃣ Deploy with Docker Compose

```bash
# Clone the repository
git clone https://github.com/yourusername/Foodify.git
cd Foodify

# Build and start all services
docker-compose up --build

# Or run in detached mode (recommended)
docker-compose up -d --build
```

That's it! Docker will:
- ✅ Build backend and frontend containers
- ✅ Set up the database and vector store
- ✅ Configure networking between services
- ✅ Start health monitoring
- ✅ Mount data volumes for persistence

### 3️⃣ Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 4️⃣ Manage Docker Services

```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop services
docker-compose down

# Stop and remove volumes (⚠️ deletes database)
docker-compose down -v

# Rebuild after code changes
docker-compose up --build
```

---

## ⚙️ Configuration

### Environment Variables (Optional)

Docker Compose includes sensible defaults. To customize, create a `.env` file:

```bash
cp .env.example .env
```

Edit `.env` to override defaults:
```env
# Backend Configuration
API_PORT=8000
DATABASE_URL=sqlite:///app/foodify.db

# LLM/VLM Configuration
LLM_BASE_URL=http://host.docker.internal:11434
LLM_MODEL=llama3:latest
VLM_MODEL=qwen3-vl:latest

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Customizing AI Models

To use different Ollama models, edit your `.env` file:

```env
# For faster inference (smaller models)
LLM_MODEL=llama3.2:1b
VLM_MODEL=llava

# For better quality (larger models)
LLM_MODEL=llama3.2:70b
VLM_MODEL=llama3.2-vision:90b

# Default (recommended balance)
LLM_MODEL=llama3.2
VLM_MODEL=llama3.2-vision
```

Then restart Docker Compose:
```bash
docker-compose down
docker-compose up -d
```

### Persistent Data

Docker volumes automatically persist:
- **Database**: `./backend/foodify.db` - all recipes and chat history
- **Vector Store**: `./backend/chroma_db` - recipe embeddings
- **Nutrition Data**: `./data` - nutrition database

Your data is safe even if you restart or rebuild containers!

### Connecting to Ollama on Host

The Docker setup uses `host.docker.internal` to connect to Ollama running on your host machine:

**Linux Users**: You may need to add `--add-host=host.docker.internal:host-gateway` to docker run, or update `docker-compose.yml`:

```yaml
backend:
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

**Verify Ollama is accessible from Docker**:
```bash
curl http://localhost:11434/api/tags
```

### Advanced Docker Usage

<details>
<summary><b>Build Individual Services</b></summary>

#### Backend Only
```bash
cd backend
docker build -t foodify-backend .
docker run -p 8000:8000 \
  -v $(pwd)/foodify.db:/app/foodify.db \
  -v $(pwd)/chroma_db:/app/chroma_db \
  -e LLM_BASE_URL=http://host.docker.internal:11434 \
  foodify-backend
```

#### Frontend Only
```bash
cd frontend
docker build -t foodify-frontend .
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://localhost:8000 \
  foodify-frontend
```

</details>

### Production Deployment

For production deployments:

1. **Use external databases** instead of SQLite
2. **Set up proper secrets management** for API keys
3. **Configure reverse proxy** (nginx/Caddy) for SSL/TLS
4. **Use orchestration** (Kubernetes, Docker Swarm) for scaling
5. **Set resource limits** in docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 4G
   ```

---

## �📖 How to Use

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

## �📁 Project Structure

```
Foodify/
├── backend/                      # Python FastAPI Backend
│   ├── app/
│   │   ├── main.py              # Application entry point
│   │   ├── api/                 # API route handlers
│   │   │   ├── routes_image.py  # Image analysis endpoints
│   │   │   ├── routes_url.py    # URL extraction endpoints
│   │   │   ├── routes_chat.py   # Chat agent endpoints
│   │   │   └── routes_rag.py    # Full RAG endpoints (UPDATED)
│   │   ├── services/            # Business logic
│   │   │   ├── image_pipeline.py          # Image-to-recipe pipeline
│   │   │   ├── url_pipeline.py            # URL extraction pipeline
│   │   │   ├── chat_agent.py              # Chat agent (REFACTORED)
│   │   │   ├── chat/                      # Chat modules (NEW)
│   │   │   │   ├── intent.py              # Intent detection
│   │   │   │   ├── router.py              # Handler routing
│   │   │   │   └── helpers.py             # Common chat helpers
│   │   │   ├── ingestion/                 # Ingestion modules (NEW)
│   │   │   │   └── base.py                # Shared recipe persistence
│   │   │   ├── recipe_rag.py              # Full RAG system (ENHANCED)
│   │   │   ├── recipe_vectorstore.py      # Vector DB (cached)
│   │   │   ├── social_media_scraper.py    # Social media extraction
│   │   │   ├── video_transcript.py        # Video transcription
│   │   │   └── conversation_memory.py     # Chat context management
│   │   ├── core/                # Core configurations
│   │   │   ├── config.py        # App settings (relative paths)
│   │   │   ├── constants.py     # Application constants (NEW)
│   │   │   ├── llm_client.py    # LLM integration
│   │   │   └── vlm_client.py    # Vision model integration
│   │   ├── db/                  # Database layer
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   ├── schema.py        # Pydantic schemas
│   │   │   ├── serializers.py   # Unified serializers (NEW)
│   │   │   ├── session.py       # DB session management
│   │   │   ├── crud_recipes.py  # Recipe CRUD operations
│   │   │   ├── crud_chat.py     # Chat history operations
│   │   │   └── crud_menus.py    # Menu planning operations
│   │   ├── utils/               # Utilities
│   │   │   ├── json_parser.py        # Robust JSON extraction (NEW)
│   │   │   ├── nutrition_lookup.py   # Fuzzy nutrition matching
│   │   │   ├── recipe_parser.py      # Recipe text parsing
│   │   │   ├── text_cleaning.py      # Text preprocessing (enhanced)
│   │   │   ├── unit_conversion.py    # Unit conversions
│   │   │   └── prompt_loader.py      # Prompt management
│   │   └── prompts/             # AI prompts
│   │       ├── llm_prompts.json
│   │       ├── vlm_prompts.json
│   │       └── rag_prompts.json
│   ├── tests/                   # Unit tests
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile              # Backend Docker image (NEW)
│   ├── .dockerignore           # Docker ignore patterns (NEW)
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
│   ├── next.config.ts          # Next.js config (standalone)
│   ├── Dockerfile              # Frontend Docker image (NEW)
│   ├── .dockerignore           # Docker ignore patterns (NEW)
│   └── tsconfig.json           # TypeScript config
│
├── data/                        # Data files
│   ├── nutrition_data.csv      # Nutrition database
│   └── nutrition_eda.ipynb     # Data exploration notebook
│
├── chroma_db/                   # ChromaDB vector store
├── docker-compose.yml           # Docker orchestration (NEW)
├── .dockerignore               # Root Docker ignore (NEW)
├── start.sh                     # Application start script
└── README.md                    # This file (UPDATED)
```


Change embedding model in `backend/app/core/config.py`:
```python
embedding_model: str = "all-mpnet-base-v2"  # Better quality
# or "all-MiniLM-L6-v2" for faster inference
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
- **Local Processing**: Requires local compute resources for AI models (Docker deployment simplifies this)
- **Simple Unit Conversion**: Basic metric/imperial conversions only
- **No User Authentication**: Single-user design (production-ready architecture for future multi-user)
- **SQLite Database**: Suitable for demo/MVP; PostgreSQL recommended for production scale

### Planned Enhancements

**Infrastructure & Scaling**
- [ ] PostgreSQL migration for production scale
- [ ] Redis caching for improved performance
- [ ] Kubernetes deployment configurations
- [ ] CI/CD pipeline (GitHub Actions)

**Features**
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
- AI/ML integration (LLMs, Vision Models, Full RAG)
- Modern web architecture (FastAPI + Next.js)
- Data engineering (ETL, vector databases)
- API design and documentation
- DevOps & Containerization (Docker, Docker Compose)
- Code quality & maintainability (DRY, modular architecture)
- Production-ready deployment strategies

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
