# Agentic RAG Demo – Quick Start

## 1 · Prerequisites
- Python ≥ 3.10
- Git

## 2 · Clone & Install
```bash
git clone https://github.com/your-org/agentic-rag-demo.git
cd agentic-rag-demo

# Create & activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\activate

# Install all required packages
pip install -r requirements.txt
```

## 3 · Environment Variables
Create a `.env` file in the repo root:

```env
# .env – example / fake values
OPENAI_API_KEY=sk-your-fake-key
AZURE_SEARCH_ENDPOINT=https://fake-search-endpoint.search.windows.net
AZURE_SEARCH_KEY=00000000000000000000000000000000
AZURE_SEARCH_INDEX=my-index
```

## 4 · Run
CLI:
```bash
python app.py              # or whatever entry point you use
```

Streamlit UI:
```bash
streamlit run ui/app.py    # adjust path if needed
```

## 5 · Troubleshooting
If imports fail, ensure the virtual environment is active (`which python` should point to `.venv`).  
Re-run `pip install -r requirements.txt` after any changes to `requirements.txt`.
