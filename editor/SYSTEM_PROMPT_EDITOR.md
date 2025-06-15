# System Prompt Editor

A simple interface to edit CJ system prompts directly from the browser.

## Features

- Load all available prompt versions from disk
- Edit prompts in a large text area
- Save prompts back to their YAML files
- Automatic backup creation before overwriting
- Integrated with HireCJ agents service

## Setup

1. Start the agents service (includes prompt API):
```bash
cd agents
python -m app
```

2. Install editor dependencies and start:
```bash
cd editor
npm install
npm run dev
```

The editor will be available at http://localhost:5173

## Usage

1. Navigate to the "System Prompts" tab
2. Select a version from the dropdown (e.g., v6.0.1)
3. Edit the prompt content in the text area
4. Click "Save" to write changes to disk

## Architecture

- **API**: `/agents/app/api/routes/prompts.py` - FastAPI endpoints
- **UI**: `/editor/src/views/SystemPromptsView.tsx` - React component
- **Prompts**: `/agents/prompts/cj/versions/*.yaml` - Prompt files

## API Endpoints

- `GET /api/v1/prompts` - List all prompt versions
- `GET /api/v1/prompts/{version}` - Get specific prompt content
- `PUT /api/v1/prompts/{version}` - Save prompt content

## Notes

- The API automatically creates timestamped backups before overwriting files
- YAML files are preserved in their original format
- No authentication required (internal tool)
- Integrated into main agents service on port 8000