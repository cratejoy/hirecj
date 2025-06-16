#!/usr/bin/env python3
"""
Universal ingestion script for Knowledge API
Supports files, directories, URLs, and JSON data
"""
import argparse
import asyncio
import aiohttp
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

API_BASE = "http://localhost:8004"

class UniversalIngester:
    """Handles various ingestion types for the Knowledge API"""
    
    def __init__(self, namespace: str, dry_run: bool = False):
        self.namespace = namespace
        self.dry_run = dry_run
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
        self.failed_items = []
    
    async def ingest_file(self, session: aiohttp.ClientSession, file_path: Path) -> bool:
        """Ingest a single file"""
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            self.failed_items.append(str(file_path))
            return False
        
        if self.dry_run:
            print(f"[DRY RUN] Would upload: {file_path}")
            return True
        
        try:
            with open(file_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=file_path.name)
                
                async with session.post(
                    f"{API_BASE}/api/{self.namespace}/documents/upload",
                    data=data
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"✅ Uploaded: {file_path.name} ({result['content_length']} chars)")
                        return True
                    else:
                        error = await resp.text()
                        print(f"❌ Failed to upload {file_path.name}: {error}")
                        self.failed_items.append(str(file_path))
                        return False
        except Exception as e:
            print(f"❌ Error uploading {file_path}: {e}")
            self.failed_items.append(str(file_path))
            return False
    
    async def ingest_directory(self, session: aiohttp.ClientSession, dir_path: Path, 
                             recursive: bool = False, pattern: str = "*") -> int:
        """Ingest all files in a directory"""
        count = 0
        
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        # Filter to supported extensions
        supported_extensions = {'.txt', '.md', '.json'}
        files = [f for f in files if f.is_file() and f.suffix.lower() in supported_extensions]
        
        print(f"Found {len(files)} files to ingest")
        
        for file_path in files:
            self.stats['total'] += 1
            if await self.ingest_file(session, file_path):
                self.stats['successful'] += 1
                count += 1
            else:
                self.stats['failed'] += 1
        
        return count
    
    async def ingest_url(self, session: aiohttp.ClientSession, url: str, 
                        metadata: Dict[str, str] = None) -> bool:
        """Ingest content from a URL"""
        if self.dry_run:
            print(f"[DRY RUN] Would fetch and ingest: {url}")
            return True
        
        try:
            async with session.post(
                f"{API_BASE}/api/{self.namespace}/documents/url",
                json={"url": url, "metadata": metadata or {}}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Ingested URL: {url} ({result['content_length']} chars)")
                    return True
                else:
                    error = await resp.text()
                    print(f"❌ Failed to ingest URL {url}: {error}")
                    self.failed_items.append(url)
                    return False
        except Exception as e:
            print(f"❌ Error ingesting URL {url}: {e}")
            self.failed_items.append(url)
            return False
    
    async def ingest_urls_from_file(self, session: aiohttp.ClientSession, 
                                   urls_file: Path) -> int:
        """Ingest URLs from a file (one URL per line)"""
        count = 0
        
        try:
            with open(urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip() 
                       and not line.strip().startswith('#')]
            
            print(f"Found {len(urls)} URLs to ingest")
            
            for url in urls:
                self.stats['total'] += 1
                if await self.ingest_url(session, url):
                    self.stats['successful'] += 1
                    count += 1
                else:
                    self.stats['failed'] += 1
                await asyncio.sleep(0.5)  # Rate limiting
            
            return count
            
        except Exception as e:
            print(f"❌ Error reading URLs file: {e}")
            return 0
    
    async def ingest_json_data(self, session: aiohttp.ClientSession, 
                              json_file: Path) -> bool:
        """Ingest data from a JSON file"""
        # For now, treat JSON files as regular files
        # In the future, this could handle batch JSON data differently
        return await self.ingest_file(session, json_file)
    
    def print_summary(self):
        """Print ingestion summary"""
        print("\n" + "="*50)
        print("Ingestion Summary")
        print("="*50)
        print(f"Total items:      {self.stats['total']}")
        print(f"Successful:       {self.stats['successful']}")
        print(f"Failed:           {self.stats['failed']}")
        print(f"Skipped:          {self.stats['skipped']}")
        
        if self.failed_items:
            print(f"\nFailed items ({len(self.failed_items)}):")
            for item in self.failed_items[:10]:
                print(f"  - {item}")
            if len(self.failed_items) > 10:
                print(f"  ... and {len(self.failed_items) - 10} more")

async def main():
    global API_BASE
    
    parser = argparse.ArgumentParser(
        description="Universal ingestion script for Knowledge API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest a single file
  %(prog)s --namespace products --type file /path/to/document.txt
  
  # Ingest all files in a directory
  %(prog)s --namespace docs --type directory /path/to/docs/
  
  # Ingest files recursively with pattern
  %(prog)s --namespace docs --type directory --recursive /path/to/docs/ "*.md"
  
  # Ingest URLs from a file
  %(prog)s --namespace web --type urls /path/to/urls.txt
  
  # Ingest a single URL
  %(prog)s --namespace web --type url https://example.com/article
  
  # Dry run to see what would be ingested
  %(prog)s --namespace test --type directory --dry-run /path/to/docs/
"""
    )
    
    parser.add_argument('--namespace', required=True, help='Target namespace')
    parser.add_argument('--type', required=True, 
                       choices=['file', 'directory', 'url', 'urls', 'json'],
                       help='Type of content to ingest')
    parser.add_argument('path_or_url', help='Path to file/directory or URL')
    parser.add_argument('pattern', nargs='?', default='*',
                       help='File pattern for directory ingestion (default: *)')
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='Recursively process directories')
    parser.add_argument('--metadata', '-m', type=json.loads,
                       help='Additional metadata as JSON string')
    parser.add_argument('--dry-run', '-n', action='store_true',
                       help='Show what would be ingested without actually doing it')
    parser.add_argument('--api-base', default=API_BASE,
                       help=f'API base URL (default: {API_BASE})')
    
    args = parser.parse_args()
    
    # Override global API base if specified
    if args.api_base != API_BASE:
        API_BASE = args.api_base
    
    # Create ingester
    ingester = UniversalIngester(args.namespace, args.dry_run)
    
    # Check namespace exists
    async with aiohttp.ClientSession() as session:
        if not args.dry_run:
            try:
                async with session.get(f"{API_BASE}/api/namespaces/{args.namespace}") as resp:
                    if resp.status == 404:
                        print(f"❌ Namespace '{args.namespace}' not found")
                        print("Available namespaces:")
                        async with session.get(f"{API_BASE}/api/namespaces") as ns_resp:
                            if ns_resp.status == 200:
                                data = await ns_resp.json()
                                for ns in data['namespaces']:
                                    print(f"  - {ns['id']}: {ns['name']}")
                        return 1
            except aiohttp.ClientError as e:
                print(f"❌ Cannot connect to API at {API_BASE}: {e}")
                return 1
        
        # Process based on type
        try:
            if args.type == 'file':
                file_path = Path(args.path_or_url)
                ingester.stats['total'] = 1
                if await ingester.ingest_file(session, file_path):
                    ingester.stats['successful'] = 1
                else:
                    ingester.stats['failed'] = 1
            
            elif args.type == 'directory':
                dir_path = Path(args.path_or_url)
                if not dir_path.is_dir():
                    print(f"❌ Not a directory: {dir_path}")
                    return 1
                await ingester.ingest_directory(session, dir_path, 
                                              args.recursive, args.pattern)
            
            elif args.type == 'url':
                ingester.stats['total'] = 1
                if await ingester.ingest_url(session, args.path_or_url, args.metadata):
                    ingester.stats['successful'] = 1
                else:
                    ingester.stats['failed'] = 1
            
            elif args.type == 'urls':
                urls_file = Path(args.path_or_url)
                if not urls_file.exists():
                    print(f"❌ URLs file not found: {urls_file}")
                    return 1
                await ingester.ingest_urls_from_file(session, urls_file)
            
            elif args.type == 'json':
                json_file = Path(args.path_or_url)
                ingester.stats['total'] = 1
                if await ingester.ingest_json_data(session, json_file):
                    ingester.stats['successful'] = 1
                else:
                    ingester.stats['failed'] = 1
            
            # Print summary
            ingester.print_summary()
            
            return 0 if ingester.stats['failed'] == 0 else 1
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))