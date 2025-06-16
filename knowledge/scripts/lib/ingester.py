"""
Enhanced document ingestion for Knowledge CLI
"""
import aiohttp
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import mimetypes
from .utils import print_success, print_error, print_info, print_warning, ProgressBar, format_size, format_duration


class KnowledgeIngester:
    """Enhanced ingester with progress tracking and better error handling"""
    
    def __init__(self, namespace: str, api_base: str, parallel: int = 1):
        self.namespace = namespace
        self.api_base = api_base
        self.parallel = parallel
        self.stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "bytes_processed": 0,
            "start_time": datetime.now()
        }
        self.failed_items = []
        self.semaphore = asyncio.Semaphore(parallel)
    
    async def ingest_file(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ingest a single file with progress tracking"""
        async with self.semaphore:
            self.stats["total"] += 1
            
            if not file_path.exists():
                print_error(f"File not found: {file_path}")
                self.stats["failed"] += 1
                self.failed_items.append(str(file_path))
                return {"success": False, "error": "File not found"}
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size == 0:
                print_warning(f"Skipping empty file: {file_path}")
                self.stats["skipped"] += 1
                return {"success": False, "error": "Empty file"}
            
            # Check if file type is supported
            mime_type, _ = mimetypes.guess_type(str(file_path))
            supported_types = {
                'text/plain', 'text/markdown', 'text/x-markdown',
                'application/json', 'text/csv', 'text/html',
                'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
            
            if mime_type and mime_type not in supported_types:
                print_warning(f"Unsupported file type {mime_type}: {file_path}")
                self.stats["skipped"] += 1
                return {"success": False, "error": f"Unsupported file type: {mime_type}"}
            
            try:
                async with aiohttp.ClientSession() as session:
                    with open(file_path, 'rb') as f:
                        data = aiohttp.FormData()
                        data.add_field('file', f, filename=file_path.name)
                        if metadata:
                            data.add_field('metadata', json.dumps(metadata))
                        
                        async with session.post(
                            f"{self.api_base}/api/{self.namespace}/documents/upload",
                            data=data
                        ) as resp:
                            if resp.status == 200:
                                result = await resp.json()
                                self.stats["successful"] += 1
                                self.stats["bytes_processed"] += file_size
                                print_success(f"Uploaded: {file_path.name} ({format_size(file_size)})")
                                return {"success": True, **result}
                            else:
                                error = await resp.text()
                                print_error(f"Failed to upload {file_path.name}: {error}")
                                self.stats["failed"] += 1
                                self.failed_items.append(str(file_path))
                                return {"success": False, "error": error}
            except Exception as e:
                print_error(f"Error uploading {file_path}: {e}")
                self.stats["failed"] += 1
                self.failed_items.append(str(file_path))
                return {"success": False, "error": str(e)}
    
    async def ingest_url(self, url: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ingest content from a URL"""
        async with self.semaphore:
            self.stats["total"] += 1
            
            try:
                async with aiohttp.ClientSession() as session:
                    payload = {"url": url}
                    if metadata:
                        payload["metadata"] = metadata
                    
                    async with session.post(
                        f"{self.api_base}/api/{self.namespace}/documents/url",
                        json=payload
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            self.stats["successful"] += 1
                            content_length = result.get('content_length', 0)
                            self.stats["bytes_processed"] += content_length
                            print_success(f"Ingested URL: {url} ({format_size(content_length)})")
                            return {"success": True, **result}
                        else:
                            error = await resp.text()
                            print_error(f"Failed to ingest URL {url}: {error}")
                            self.stats["failed"] += 1
                            self.failed_items.append(url)
                            return {"success": False, "error": error}
            except Exception as e:
                print_error(f"Error ingesting URL {url}: {e}")
                self.stats["failed"] += 1
                self.failed_items.append(url)
                return {"success": False, "error": str(e)}
    
    async def ingest_directory(self, dir_path: Path, recursive: bool = False, 
                             pattern: str = "*") -> List[Dict[str, Any]]:
        """Ingest all files in a directory"""
        results = []
        
        # Get all files matching pattern
        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        
        # Filter to only files
        files = [f for f in files if f.is_file()]
        
        if not files:
            print_warning(f"No files found matching pattern: {pattern}")
            return results
        
        print_info(f"Found {len(files)} files to ingest")
        progress = ProgressBar(len(files), "Ingesting files")
        
        # Process files in batches
        tasks = []
        for file_path in files:
            task = self.ingest_file(file_path)
            tasks.append(task)
        
        # Process with progress updates
        for task in asyncio.as_completed(tasks):
            result = await task
            results.append(result)
            progress.update()
        
        return results
    
    async def ingest_urls_from_file(self, urls_file: Path) -> List[Dict[str, Any]]:
        """Ingest URLs from a file (one URL per line)"""
        results = []
        
        try:
            with open(urls_file, 'r') as f:
                urls = [line.strip() for line in f if line.strip() 
                       and not line.strip().startswith('#')]
            
            if not urls:
                print_warning("No URLs found in file")
                return results
            
            print_info(f"Found {len(urls)} URLs to ingest")
            progress = ProgressBar(len(urls), "Ingesting URLs")
            
            # Process URLs with rate limiting
            for url in urls:
                result = await self.ingest_url(url)
                results.append(result)
                progress.update()
                
                # Small delay between URLs to avoid rate limiting
                await asyncio.sleep(0.5)
            
            return results
            
        except Exception as e:
            print_error(f"Error reading URLs file: {e}")
            return results
    
    async def print_summary(self):
        """Print ingestion summary"""
        duration = (datetime.now() - self.stats["start_time"]).total_seconds()
        
        print("\n" + "="*60)
        print("Ingestion Summary")
        print("="*60)
        print(f"Total items:      {self.stats['total']}")
        print(f"Successful:       {self.stats['successful']}")
        print(f"Failed:           {self.stats['failed']}")
        print(f"Skipped:          {self.stats['skipped']}")
        print(f"Data processed:   {format_size(self.stats['bytes_processed'])}")
        print(f"Time taken:       {format_duration(duration)}")
        
        if duration > 0:
            rate = self.stats['bytes_processed'] / duration
            print(f"Processing rate:  {format_size(int(rate))}/s")
        
        if self.failed_items:
            print(f"\nFailed items ({len(self.failed_items)}):")
            for item in self.failed_items[:10]:
                print(f"  - {item}")
            if len(self.failed_items) > 10:
                print(f"  ... and {len(self.failed_items) - 10} more")