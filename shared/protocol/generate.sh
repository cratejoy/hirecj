#!/bin/bash
# Generate TypeScript types from Pydantic models using pydantic-to-typescript

set -e

# Change to the repository root
cd "$(dirname "$0")/../.."

echo "Generating TypeScript types from Pydantic models..."

# Check if pydantic2ts is available
if ! command -v pydantic2ts &> /dev/null; then
    echo "Error: pydantic2ts not found. Please install it with: pip install pydantic-to-typescript"
    exit 1
fi

# Check if json2ts is available
if ! command -v json2ts &> /dev/null; then
    echo "Error: json2ts not found. Please install it with: npm install -g json-schema-to-typescript"
    exit 1
fi

# Add current directory to PYTHONPATH so shared module can be imported
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Generate TypeScript from Pydantic models
echo "Running pydantic2ts..."

# Generate for homepage
pydantic2ts --module shared.protocol.models --output homepage/src/protocol/generated.ts
echo "✅ TypeScript types generated for homepage at homepage/src/protocol/generated.ts"

# Generate for editor
pydantic2ts --module shared.protocol.models --output editor/src/protocol/generated.ts
echo "✅ TypeScript types generated for editor at editor/src/protocol/generated.ts"

echo "✅ All TypeScript types generated successfully!"