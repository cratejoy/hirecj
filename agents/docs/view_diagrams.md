# How to View Mermaid Diagrams

## Option 1: Mermaid Live Editor (Easiest - No Install)

1. Go to: https://mermaid.live/
2. Copy the mermaid code block from `workflow_diagram_daily_briefing.md` (everything between ` ```mermaid` and ` ``` `)
3. Paste it into the editor
4. The diagram renders instantly on the right
5. You can export as PNG, SVG, or PDF

## Option 2: VS Code Preview

1. Install the "Markdown Preview Mermaid Support" extension
2. Open `workflow_diagram_daily_briefing.md` in VS Code
3. Press `Cmd+Shift+V` (Mac) or `Ctrl+Shift+V` (Windows/Linux)
4. The diagram renders in the preview pane

## Option 3: GitHub

1. Push the files to GitHub
2. GitHub automatically renders Mermaid diagrams in markdown files
3. Just view the .md file on GitHub

## Option 4: Command Line (Using Mermaid CLI)

```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Extract and render the diagram
cd /Users/aelaguiz/workspace/hirecj-data/docs

# Create a temporary file with just the mermaid content
cat workflow_diagram_daily_briefing.md | sed -n '/```mermaid/,/```/p' | sed '1d;$d' > temp_diagram.mmd

# Render to PNG
mmdc -i temp_diagram.mmd -o daily_briefing_workflow.png

# Render to SVG (better quality)
mmdc -i temp_diagram.mmd -o daily_briefing_workflow.svg

# Clean up
rm temp_diagram.mmd

# Open the image
open daily_briefing_workflow.png
```

## Option 5: Using Python (with a simple script)

```python
# Save this as render_mermaid.py
import re
import webbrowser
import urllib.parse

def render_mermaid_online(md_file):
    with open(md_file, 'r') as f:
        content = f.read()

    # Extract mermaid code
    pattern = r'```mermaid\n(.*?)\n```'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        mermaid_code = match.group(1)
        # Create Mermaid Live URL
        base_url = "https://mermaid.live/edit#pako:"
        encoded = urllib.parse.quote(mermaid_code)
        url = f"{base_url}{encoded}"
        webbrowser.open(url)
    else:
        print("No mermaid diagram found")

# Use it
render_mermaid_online('docs/workflow_diagram_daily_briefing.md')
```

## Quick Copy-Paste Method

If you just want to see the diagram quickly, here's a direct link you can create:

1. Copy the mermaid code from the file
2. Go to https://mermaid.live/
3. Paste and view instantly

The diagram shows the complete daily briefing workflow with all the components, data flow, and tool usage!
