# HireCJ Knowledge Service - LightRAG Knowledge Graph

A comprehensive knowledge management system using LightRAG to ingest, process, and query content from multiple sources including RSS feeds, podcasts, YouTube videos, and text transcripts.

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

3. Install LightRAG from the local directory:
```bash
pip install -e ./LightRAG
```

4. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Usage

### Content Ingestion

The system supports ingesting content from multiple sources:

#### Add RSS Feed/Podcast:
```bash
python -m src ingest add https://example.com/podcast.rss
# Or limit episodes:
python -m src ingest add https://example.com/podcast.rss --limit 5
```

#### Add YouTube Video:
```bash
python -m src ingest add https://youtube.com/watch?v=VIDEO_ID
```

#### Process Pipeline:
```bash
python -m src ingest process
```

#### Check Status:
```bash
python -m src ingest status
```

### Interactive Demo

Run the interactive query interface:
```bash
python -m src demo
# Or just:
python -m src
```

### Web UI Server

Start the LightRAG web interface:
```bash
./run_lightrag_server.sh
# Access at http://localhost:9621
```

### Makefile Commands

```bash
make demo            # Run interactive demo
make ingest-status   # Check pipeline status
make ingest-process  # Process pending items
make ingest-add URL=https://example.com/feed.rss LIMIT=5
make server         # Start web UI server
```

## Query Modes

- **naive**: Direct text search without knowledge graph
- **local**: Search using local entity relationships
- **global**: Search using global knowledge patterns
- **hybrid**: Combines local and global search for best results

## Features

- **Multi-Source Ingestion**: RSS feeds, podcasts, YouTube videos, text files
- **Audio Transcription**: Automatic transcription using OpenAI Whisper
- **Knowledge Graph**: LightRAG-powered graph database for intelligent querying
- **Pipeline Management**: Track content through download, transcription, and loading stages
- **Web UI**: Interactive interface for exploring the knowledge graph
- **Persistent Storage**: Database persists between runs

## Project Structure

```
hirecj-knowledge/
├── src/
│   ├── ingest.py                    # Content ingestion pipeline
│   ├── load_transcript.py           # Direct transcript loader
│   └── scripts/
│       └── lightrag_transcripts_demo.py  # Interactive demo
├── content/                         # Pipeline directories
│   ├── inbox/                       # New URLs to process
│   ├── downloading/                 # Currently downloading
│   ├── downloaded/                  # Downloaded content
│   ├── audio/                       # Extracted audio files
│   ├── chunks/                      # Audio chunks for transcription
│   ├── transcribing/                # Currently transcribing
│   ├── transcripts/                 # Completed transcripts
│   ├── loaded/                      # Loaded into LightRAG
│   └── failed/                      # Failed items
├── transcripts/                     # Legacy transcript files
├── lightrag_transcripts_db/         # LightRAG database
├── requirements.txt
├── run_lightrag_server.sh           # Web UI launcher
└── README.md
```