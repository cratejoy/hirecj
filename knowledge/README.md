# LightRAG Video Transcripts Demo

A lightweight demonstration of using LightRAG to analyze and query video transcripts using a knowledge graph approach.

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install LightRAG from the third-party directory:
```bash
pip install -e ../third-party/LightRAG
```

4. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Usage

Run the demo script:
```bash
python src/scripts/lightrag_transcripts_demo.py
```

The demo provides:
- Automatic loading of all transcripts from the `transcripts/` directory
- Sample queries to demonstrate different search modes
- Interactive query mode for custom questions
- Database persistence for faster subsequent runs

## Query Modes

- **naive**: Direct text search without knowledge graph
- **local**: Search using local entity relationships
- **global**: Search using global knowledge patterns
- **hybrid**: Combines local and global search for best results

## Project Structure

```
hirecj-knowledge/
├── src/
│   └── scripts/
│       └── lightrag_transcripts_demo.py
├── transcripts/         # Video transcript files
├── lightrag_transcripts_db/  # LightRAG database (auto-created)
├── requirements.txt
└── README.md
```