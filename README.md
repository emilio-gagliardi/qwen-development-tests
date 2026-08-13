# LiteLLM + Haystack RAG Pipeline

A minimal RAG pipeline demonstrating:
- LiteLLM as a unified LLM gateway
- Haystack for RAG orchestration
- Intent classification before model routing
- Model router based on request complexity/nuance
- Pydantic for all data contracts
- FastAPI for the RAG endpoint

## Architecture

```
User Request → FastAPI Endpoint → Intent Classifier → Model Router → LLM (via LiteLLM) → Response
                                      ↓
                              Document Store (for RAG)
```

## Setup

### Prerequisites
- Python 3.9+
- LiteLLM proxy server running
- API keys for your LLM providers

### Installation

```bash
pip install -r requirements.txt
```

### Running LiteLLM Proxy

Create a `litellm_config.yaml` file and run:

```bash
litellm --config litellm_config.yaml
```

### Running the RAG Service

```bash
uvicorn app.main:app --reload
```

## API Endpoints

- `POST /rag/query` - Submit a query to the RAG pipeline
- `GET /health` - Health check endpoint

## Data Contracts

All request/response objects use Pydantic models defined in `app/schemas.py`.

## Components

1. **Intent Classifier**: Classifies user requests by complexity and intent
2. **Model Router**: Routes requests to appropriate models based on classification
3. **RAG Pipeline**: Haystack-based retrieval augmented generation
4. **LiteLLM Gateway**: Unified interface to multiple LLM providers
