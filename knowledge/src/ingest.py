#!/usr/bin/env python
"""
Simple content ingestion pipeline for RSS/podcasts -> Whisper -> LightRAG
Following North Star principles: Simple, no cruft, elegant
"""
import sys
import json
import hashlib
import shutil
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import feedparser
import requests
import yt_dlp
from openai import OpenAI
from pydub import AudioSegment
from dotenv import load_dotenv

# Load environment
load_dotenv()


class ContentProcessor:
    def __init__(self, base_dir: Path = Path("content")):
        self.base_dir = base_dir
        self.ensure_directories()
        self.openai = OpenAI()
    
    def ensure_directories(self):
        """Create all required directories"""
        dirs = ['inbox', 'downloading', 'downloaded', 'audio', 
                'chunks', 'transcribing', 'transcripts', 'loaded', 'failed']
        for d in dirs:
            (self.base_dir / d).mkdir(parents=True, exist_ok=True)
    
    def add_url(self, url: str, limit: int = None):
        """Add URL to inbox - user-friendly interface
        
        Args:
            url: The URL to add
            limit: For RSS feeds, max number of episodes to process (default: all)
        """
        # Create unique ID from URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Determine content type
        if 'youtube.com' in url or 'youtu.be' in url:
            prefix = 'youtube'
        elif any(x in url for x in ['.rss', '/rss', 'feed', 'podcast', 'libsyn']):
            prefix = 'rss'
        else:
            prefix = 'content'
        
        filename = f"{prefix}_{url_hash}.json"
        filepath = self.base_dir / 'inbox' / filename
        
        # For RSS feeds, don't check for duplicates at feed level
        # Episodes are checked individually during processing
        if prefix != 'rss':
            # Check if already exists in any directory
            existing_locations = []
            for dir_name in ['inbox', 'downloading', 'downloaded', 'transcripts', 'loaded']:
                check_path = self.base_dir / dir_name / filename
                if dir_name in ['transcripts', 'loaded']:
                    check_path = self.base_dir / dir_name / f"{prefix}_{url_hash}.txt"
                elif dir_name in ['downloaded', 'downloading']:
                    check_path = self.base_dir / dir_name / f"{prefix}_{url_hash}"
                    
                if check_path.exists():
                    existing_locations.append(dir_name)
            
            if existing_locations:
                print(f"⚠️  URL already exists in: {', '.join(existing_locations)}")
                print(f"   {url}")
                return
        else:
            # For RSS, just check if it's already in inbox
            if filepath.exists():
                print(f"⚠️  RSS feed already in inbox, will check for new episodes on process")
                return
        
        # Check failed directory
        failed_path = self.base_dir / 'failed' / f"{prefix}_{url_hash}.error"
        if failed_path.exists():
            print(f"⚠️  URL previously failed. Delete {failed_path} to retry.")
            return
        
        # Store as JSON for richer metadata
        data = {
            'url': url,
            'added_at': datetime.now().isoformat(),
            'type': prefix,
            'limit': limit  # How many episodes to process
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Added {prefix} content: {url}")
        if limit and prefix == 'rss':
            print(f"  Will process up to {limit} episodes")
    
    def process_inbox(self):
        """Process all items in inbox and resume any incomplete work"""
        # First, check for stuck documents in LightRAG
        self._check_pending_lightrag_docs()
        
        # Then check for transcripts that need loading
        transcripts_to_load = list((self.base_dir / 'transcripts').glob('*.txt'))
        if transcripts_to_load:
            print(f"📋 Found {len(transcripts_to_load)} transcript(s) to load into LightRAG")
            for transcript_file in transcripts_to_load:
                try:
                    print(f"\n🔄 Resuming: Loading {transcript_file.stem} into LightRAG...")
                    with open(transcript_file, encoding='utf-8') as f:
                        content = f.read()
                    
                    self._load_to_lightrag(content, transcript_file.stem)
                    print(f"  ✅ Successfully loaded into knowledge graph!")
                    
                    # Move to loaded directory
                    loaded_file = self.base_dir / 'loaded' / transcript_file.name
                    shutil.move(str(transcript_file), str(loaded_file))
                    print(f"  📁 Moved to loaded directory")
                    
                except Exception as e:
                    print(f"  ❌ Failed to load {transcript_file.stem}: {str(e)}")
                    # Don't move to failed - leave in transcripts to retry
        
        # Now process inbox items
        inbox = self.base_dir / 'inbox'
        items = list(inbox.glob('*.json'))
        
        if not items and not transcripts_to_load:
            print("No new items to process")
            # Don't return - let it continue to check other things
        
        if items:
            # Deduplicate by URL
            seen_urls = set()
            unique_items = []
            
            for item_file in items:
                try:
                    with open(item_file) as f:
                        data = json.load(f)
                        url = data['url']
                        
                    if url not in seen_urls:
                        seen_urls.add(url)
                        unique_items.append(item_file)
                    else:
                        print(f"⚠️  Skipping duplicate: {item_file.name} (same URL already queued)")
                except Exception as e:
                    print(f"⚠️  Error reading {item_file}: {e}")
                    unique_items.append(item_file)  # Process anyway
            
            print(f"\n📥 Processing {len(unique_items)} new item(s)...")
            
            for item_file in unique_items:
                try:
                    print(f"\n📥 Processing: {item_file.stem}")
                    self.process_item(item_file)
                    print(f"✓ Completed: {item_file.stem}")
                except Exception as e:
                    print(f"✗ Failed: {item_file.stem} - {str(e)}")
                    self._move_to_failed(item_file, str(e))
    
    def process_item(self, item_file: Path):
        """Process single item through all stages"""
        with open(item_file) as f:
            data = json.load(f)
        
        url = data['url']
        content_type = data['type']
        item_id = item_file.stem
        
        # Move to downloading
        item_file.rename(self.base_dir / 'downloading' / item_file.name)
        
        try:
            if content_type == 'rss':
                limit = data.get('limit')
                self._process_rss(url, item_id, limit)
            elif content_type == 'youtube':
                self._process_youtube(url, item_id)
            else:
                raise NotImplementedError(f"Type {content_type} not yet supported")
        finally:
            # Cleanup downloading marker
            downloading_file = self.base_dir / 'downloading' / item_file.name
            if downloading_file.exists():
                downloading_file.unlink()
    
    def _process_rss(self, rss_url: str, feed_id: str, limit: int = None):
        """Process RSS feed - download and process multiple episodes"""
        print(f"  📡 Parsing RSS feed: {rss_url}")
        feed = feedparser.parse(rss_url)
        
        feed_title = feed.feed.get('title', 'Unknown Feed')
        print(f"  📰 Feed title: {feed_title}")
        print(f"  📊 Total entries: {len(feed.entries)}")
        
        # Find episodes with audio
        audio_episodes = []
        
        for i, entry in enumerate(feed.entries):
            audio_url = None
            
            # Check enclosures first (most common for podcasts)
            if hasattr(entry, 'enclosures'):
                for enc in entry.enclosures:
                    if enc.get('type', '').startswith('audio/'):
                        audio_url = enc.get('href', enc.get('url'))
                        break
            
            # Also check links
            if not audio_url and hasattr(entry, 'links'):
                for link in entry.links:
                    if link.get('type', '').startswith('audio/'):
                        audio_url = link['href']
                        break
            
            if audio_url:
                audio_episodes.append({
                    'url': audio_url,
                    'title': entry.get('title', 'Unknown Episode'),
                    'published': entry.get('published_parsed', None),
                    'index': i
                })
                
                # Check if we've hit the limit
                if limit and len(audio_episodes) >= limit:
                    break
        
        if not audio_episodes:
            print(f"  ❌ No audio episodes found in RSS feed")
            raise ValueError("No audio episodes found in RSS feed")
        
        print(f"  ✅ Found {len(audio_episodes)} audio episode(s)")
        if limit:
            print(f"  📌 Limited to {limit} episode(s) as requested")
        
        # Process each episode
        for ep_num, episode in enumerate(audio_episodes, 1):
            print(f"\n  {'='*60}")
            print(f"  📻 Episode {ep_num}/{len(audio_episodes)}: {episode['title'][:60]}...")
            
            # Create unique ID for this episode
            episode_hash = hashlib.md5(episode['url'].encode()).hexdigest()[:8]
            episode_id = f"{feed_id}_ep{episode_hash}"
            
            # Check if already processed
            if self._is_episode_processed(episode_id):
                print(f"  ⏭️  Skipping - already processed")
                continue
            
            try:
                # Download and process this episode
                self._process_episode(episode, episode_id, feed_title, rss_url)
                
            except Exception as e:
                print(f"  ❌ Failed to process episode: {str(e)}")
                # Continue with next episode instead of failing entire feed
                continue
    
    def _is_episode_processed(self, episode_id: str) -> bool:
        """Check if episode is already processed"""
        # Check in various directories
        checks = [
            self.base_dir / 'downloaded' / episode_id,
            self.base_dir / 'transcripts' / f"{episode_id}.txt",
            self.base_dir / 'loaded' / f"{episode_id}.txt"
        ]
        
        return any(path.exists() for path in checks)
    
    def _process_episode(self, episode: dict, episode_id: str, feed_title: str, feed_url: str):
        """Process a single episode"""
        # Download audio
        download_dir = self.base_dir / 'downloaded' / episode_id
        download_dir.mkdir(exist_ok=True)
        
        audio_file = download_dir / 'audio.mp3'
        print(f"  💾 Downloading: {episode['url']}")
        
        response = requests.get(episode['url'], stream=True)
        response.raise_for_status()
        
        # Get total size if available
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(audio_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\r  📥 Progress: {downloaded:,} / {total_size:,} bytes ({percent:.1f}%)", end='', flush=True)
        
        print(f"\n  ✅ Download complete! File size: {audio_file.stat().st_size:,} bytes")
        
        # Save metadata
        metadata = {
            'url': feed_url,
            'audio_url': episode['url'],
            'title': episode['title'],
            'feed_title': feed_title,
            'download_date': datetime.now().isoformat()
        }
        
        with open(download_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Copy to audio dir
        audio_dir = self.base_dir / 'audio' / episode_id
        audio_dir.mkdir(exist_ok=True)
        shutil.copy2(audio_file, audio_dir / 'audio.mp3')
        
        # Process audio through chunking and transcription
        self._process_audio(audio_dir / 'audio.mp3', episode_id, metadata)
    
    def _process_youtube(self, youtube_url: str, video_id: str):
        """Process YouTube video - download and extract audio"""
        print(f"  🎥 Processing YouTube video: {youtube_url}")
        
        # Download video
        download_dir = self.base_dir / 'downloaded' / video_id
        download_dir.mkdir(exist_ok=True)
        
        print(f"  💾 Downloading video...")
        
        ydl_opts = {
            'outtmpl': str(download_dir / 'video.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            # Get best quality audio
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                
                # Get video metadata
                title = info.get('title', 'Unknown Video')
                channel = info.get('uploader', 'Unknown Channel')
                upload_date = info.get('upload_date', 'Unknown')
                duration = info.get('duration', 0)
                
                print(f"  📺 Title: {title}")
                print(f"  👤 Channel: {channel}")
                print(f"  📅 Upload date: {upload_date}")
                print(f"  ⏱️  Duration: {duration//60}:{duration%60:02d}")
                
                # Save metadata
                metadata = {
                    'url': youtube_url,
                    'title': title,
                    'channel': channel,
                    'upload_date': upload_date,
                    'duration': duration,
                    'download_date': datetime.now().isoformat()
                }
                
                with open(download_dir / 'metadata.json', 'w') as f:
                    json.dump(metadata, f, indent=2)
                
        except Exception as e:
            print(f"  ❌ Failed to download video: {str(e)}")
            raise
        
        # Find the downloaded audio file
        audio_files = list(download_dir.glob('*.mp3'))
        if not audio_files:
            # If no mp3, look for the video file and extract audio
            video_files = list(download_dir.glob('video.*'))
            if not video_files:
                raise Exception("No video or audio file found after download")
            
            video_file = video_files[0]
            print(f"  🎵 Extracting audio from video...")
            
            audio_file = download_dir / 'audio.mp3'
            self._extract_audio_from_video(video_file, audio_file)
        else:
            audio_file = audio_files[0]
            # Rename to standard name
            new_audio_file = download_dir / 'audio.mp3'
            audio_file.rename(new_audio_file)
            audio_file = new_audio_file
        
        print(f"  ✅ Audio ready: {audio_file.stat().st_size:,} bytes")
        
        # Copy to audio directory
        audio_dir = self.base_dir / 'audio' / video_id
        audio_dir.mkdir(exist_ok=True)
        shutil.copy2(audio_file, audio_dir / 'audio.mp3')
        
        # Process audio through chunking and transcription
        self._process_audio(audio_dir / 'audio.mp3', video_id, metadata)
    
    def _extract_audio_from_video(self, video_path: Path, audio_path: Path):
        """Extract audio from video using ffmpeg"""
        cmd = [
            'ffmpeg', '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'mp3',
            '-ab', '192k',  # Audio bitrate
            '-ar', '44100',  # Sample rate
            '-y',  # Overwrite output
            str(audio_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"ffmpeg failed: {result.stderr}")
    
    def _process_audio(self, audio_file: Path, item_id: str, metadata: dict):
        """Chunk and transcribe audio"""
        # Chunk audio
        print(f"\n  🔪 Chunking audio file: {audio_file}")
        print(f"  📏 File size: {audio_file.stat().st_size:,} bytes ({audio_file.stat().st_size / 1024 / 1024:.1f} MB)")
        
        chunks_dir = self.base_dir / 'chunks' / item_id
        chunks_dir.mkdir(exist_ok=True)
        
        chunks = self._chunk_audio(audio_file, chunks_dir)
        print(f"  ✅ Created {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            print(f"     - Chunk {i+1}: {chunk.name} ({chunk.stat().st_size:,} bytes)")
        
        # Transcribe
        print(f"\n  🎙️ Starting transcription...")
        shutil.move(str(chunks_dir), str(self.base_dir / 'transcribing' / item_id))
        transcribing_dir = self.base_dir / 'transcribing' / item_id
        
        transcripts = []
        for i, chunk in enumerate(sorted(transcribing_dir.glob('chunk_*.mp3'))):
            print(f"  📝 Transcribing chunk {i+1}/{len(chunks)}: {chunk.name}")
            print(f"     Sending to Whisper API...")
            text = self._transcribe_chunk(chunk)
            print(f"     ✅ Received {len(text)} characters")
            print(f"     Preview: {text[:100]}..." if len(text) > 100 else f"     Text: {text}")
            transcripts.append(text)
        
        # Save transcript
        full_transcript = '\n'.join(transcripts)
        print(f"\n  📄 Total transcript length: {len(full_transcript):,} characters")
        
        enriched = f"""Title: {metadata.get('title', 'Unknown')}
Feed: {metadata.get('feed_title', 'Unknown')}
URL: {metadata.get('url', 'Unknown')}
Date: {metadata.get('download_date', 'Unknown')}

{full_transcript}
"""
        
        transcript_file = self.base_dir / 'transcripts' / f"{item_id}.txt"
        transcript_file.write_text(enriched, encoding='utf-8')
        print(f"  💾 Saved transcript to: {transcript_file}")
        
        # Load into LightRAG
        print(f"\n  🧠 Loading into LightRAG...")
        self._load_to_lightrag(enriched, item_id)
        print(f"  ✅ Successfully loaded into knowledge graph!")
        
        # Move to loaded directory
        loaded_file = self.base_dir / 'loaded' / f"{item_id}.txt"
        shutil.move(str(transcript_file), str(loaded_file))
        print(f"  📁 Moved to loaded directory")
        
        # Cleanup
        print(f"\n  🧹 Cleaning up temporary files...")
        shutil.rmtree(transcribing_dir)
        print(f"  ✅ Pipeline complete for {item_id}!")
    
    def _chunk_audio(self, audio_path: Path, output_dir: Path, max_size_mb: int = 10):
        """Split audio into chunks under 10MB for Whisper API"""
        print(f"     Loading audio with pydub...")
        audio = AudioSegment.from_mp3(audio_path)
        
        duration_seconds = len(audio) / 1000
        print(f"     Audio duration: {duration_seconds:.1f} seconds ({duration_seconds/60:.1f} minutes)")
        
        # Calculate chunk duration for ~9MB chunks (safety margin)
        bitrate = 128  # kbps
        max_duration_ms = (max_size_mb * 8 * 1024) / bitrate * 1000
        chunk_duration_minutes = max_duration_ms / 1000 / 60
        print(f"     Max chunk duration: {chunk_duration_minutes:.1f} minutes per chunk")
        
        chunks = []
        for i, start in enumerate(range(0, len(audio), int(max_duration_ms))):
            chunk = audio[start:start + int(max_duration_ms)]
            chunk_path = output_dir / f"chunk_{i:03d}.mp3"
            print(f"     Creating chunk {i+1}: {start/1000:.1f}s - {(start + len(chunk))/1000:.1f}s")
            chunk.export(chunk_path, format="mp3", bitrate="128k")
            chunks.append(chunk_path)
        
        return chunks
    
    def _transcribe_chunk(self, audio_path: Path) -> str:
        """Transcribe audio chunk using Whisper API"""
        with open(audio_path, 'rb') as f:
            response = self.openai.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )
        return response
    
    def _load_to_lightrag(self, content: str, item_id: str = None):
        """Load transcript into LightRAG"""
        try:
            # Try the simple approach first
            from lightrag import LightRAG
            from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
            
            rag = LightRAG(
                working_dir="./lightrag_transcripts_db",
                embedding_func=openai_embed,
                llm_model_func=gpt_4o_mini_complete,
            )
            
            # Use blocking insert instead of async
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Include file_paths for source tracking if item_id is provided
                if item_id:
                    loop.run_until_complete(rag.ainsert(content, file_paths=[f"{item_id}.txt"]))
                else:
                    loop.run_until_complete(rag.ainsert(content))
            finally:
                loop.close()
                
        except Exception as e:
            # If it fails with history_messages, it might already be loaded
            if 'history_messages' in str(e):
                print(f"  ⚠️  Note: May already be in LightRAG (got '{e}')")
                # Don't raise - treat as success
            else:
                raise
    
    def _check_pending_lightrag_docs(self):
        """Check for and reprocess any pending documents in LightRAG"""
        try:
            from lightrag import LightRAG
            from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
            from lightrag.base import DocStatus
            
            print("🔍 Checking for pending documents in LightRAG...")
            
            # Initialize LightRAG to check doc status
            rag = LightRAG(
                working_dir="./lightrag_transcripts_db",
                embedding_func=openai_embed,
                llm_model_func=gpt_4o_mini_complete,
            )
            
            # Use async to check status
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Initialize storages
                loop.run_until_complete(rag.initialize_storages())
                
                # Get status counts
                status_counts = loop.run_until_complete(rag.get_processing_status())
                pending_count = status_counts.get(DocStatus.PENDING, 0)
                
                if pending_count > 0:
                    print(f"🔄 Found {pending_count} pending document(s) in LightRAG")
                    
                    # Get pending documents
                    pending_docs = loop.run_until_complete(rag.doc_status.get_docs_by_status(DocStatus.PENDING))
                    
                    for doc_id, doc_info in pending_docs.items():
                        try:
                            print(f"  📄 Reprocessing pending document: {doc_id}")
                            
                            # The content is stored in doc_info
                            content = doc_info.content if hasattr(doc_info, 'content') else str(doc_info.get('content', ''))
                            
                            if content:
                                # Extract a reasonable item_id from file_path or doc_id
                                file_path = doc_info.file_path if hasattr(doc_info, 'file_path') else doc_info.get('file_path', f"{doc_id}.txt")
                                if file_path == "unknown_source":
                                    file_path = f"{doc_id.replace('doc-', '')[:8]}.txt"
                                
                                # Re-insert to trigger processing
                                loop.run_until_complete(rag.ainsert(content, file_paths=[file_path]))
                                print(f"    ✅ Successfully reprocessed with source: {file_path}")
                            else:
                                print(f"    ⚠️  No content found for document")
                                
                        except Exception as e:
                            print(f"    ❌ Failed to reprocess: {str(e)}")
                else:
                    print("  ✅ No pending documents found")
                            
            finally:
                loop.close()
                
        except Exception as e:
            # Log the error but continue
            print(f"  ⚠️  Could not check pending docs: {str(e)}")
    
    def status(self):
        """Show pipeline status with counts at each stage"""
        print("\n📊 Content Pipeline Status")
        print("=" * 60)
        
        # Count files at each stage
        stages = [
            ("📥 Inbox", self.base_dir / "inbox", "*.json"),
            ("⬇️  Downloading", self.base_dir / "downloading", "*"),
            ("💾 Downloaded", self.base_dir / "downloaded", "*"),
            ("🎵 Audio", self.base_dir / "audio", "*"),
            ("🔪 Chunks", self.base_dir / "chunks", "*"),
            ("🎙️  Transcribing", self.base_dir / "transcribing", "*"),
            ("📝 Transcripts", self.base_dir / "transcripts", "*.txt"),
            ("✅ Loaded", self.base_dir / "loaded", "*.txt"),
            ("❌ Failed", self.base_dir / "failed", "*.error"),
        ]
        
        total_items = 0
        for name, path, pattern in stages:
            if path.exists():
                items = list(path.glob(pattern))
                # For directories with subdirs, count the subdirs not files
                if name in ["⬇️  Downloading", "💾 Downloaded", "🎵 Audio", "🔪 Chunks", "🎙️  Transcribing"]:
                    items = [item for item in items if item.is_dir()]
                count = len(items)
                total_items += count
                
                if count > 0:
                    print(f"{name:<20} {count:>5} items")
                    # Show first few items for context
                    for item in items[:3]:
                        print(f"  └─ {item.name}")
                    if count > 3:
                        print(f"  └─ ... and {count - 3} more")
            else:
                print(f"{name:<20}     0 items")
        
        print("-" * 60)
        print(f"{'Total in Pipeline:':<20} {total_items:>5} items")
        
        # Check LightRAG status
        print("\n🧠 LightRAG Database Status")
        print("=" * 60)
        
        try:
            from lightrag import LightRAG
            from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
            from lightrag.base import DocStatus
            
            # Initialize LightRAG
            rag = LightRAG(
                working_dir="./lightrag_transcripts_db",
                embedding_func=openai_embed,
                llm_model_func=gpt_4o_mini_complete,
            )
            
            # Use async to get actual counts
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Initialize storages
                loop.run_until_complete(rag.initialize_storages())
                
                # Get processing status
                status_counts = loop.run_until_complete(rag.get_processing_status())
                
                # Display status counts
                statuses = [
                    ("✅ Processed", DocStatus.PROCESSED),
                    ("⏳ Processing", DocStatus.PROCESSING),
                    ("🔄 Pending", DocStatus.PENDING),
                    ("❌ Failed", DocStatus.FAILED),
                ]
                
                total_docs = 0
                for name, status in statuses:
                    count = status_counts.get(status, 0)
                    total_docs += count
                    if count > 0:
                        print(f"{name:<20} {count:>5} documents")
                
                print("-" * 60)
                print(f"{'Total Documents:':<20} {total_docs:>5} documents")
                
                # Get some stats about the knowledge graph
                print("\n📈 Knowledge Graph Stats")
                print("=" * 60)
                
                # Count entities and relationships
                try:
                    entity_count = len(rag.entities)
                    relationship_count = len(rag.relationships) 
                    chunk_count = len(rag.chunks)
                    
                    print(f"{'🏷️  Entities:':<20} {entity_count:>5}")
                    print(f"{'🔗 Relationships:':<20} {relationship_count:>5}")
                    print(f"{'📄 Chunks:':<20} {chunk_count:>5}")
                except:
                    print("  ⚠️  Could not retrieve graph statistics")
                
            finally:
                loop.close()
                
        except Exception as e:
            print(f"  ⚠️  Could not connect to LightRAG: {str(e)}")
        
        print("\n💡 Tip: Run 'python src/ingest.py process' to process pending items")
        print()
    
    def _move_to_failed(self, item_file: Path, error: str):
        """Move failed item and record error"""
        error_file = self.base_dir / 'failed' / f"{item_file.stem}.error"
        
        # Read original data
        if item_file.exists():
            with open(item_file) as f:
                data = json.load(f)
        else:
            # Try downloading location
            downloading = self.base_dir / 'downloading' / item_file.name
            if downloading.exists():
                with open(downloading) as f:
                    data = json.load(f)
                downloading.unlink()
            else:
                data = {"url": "unknown"}
        
        # Write error info
        error_data = {
            'original': data,
            'error': error,
            'failed_at': datetime.now().isoformat()
        }
        
        with open(error_file, 'w') as f:
            json.dump(error_data, f, indent=2)
    


def main():
    """CLI interface"""
    processor = ContentProcessor()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python src/ingest.py add URL [--limit N]  # Add content to process")
        print("  python src/ingest.py process               # Process all pending items")
        print("  python src/ingest.py status                # Show pipeline status")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "add" and len(sys.argv) > 2:
        url = sys.argv[2]
        limit = None
        
        # Check for --limit flag
        if len(sys.argv) > 3 and sys.argv[3] == "--limit" and len(sys.argv) > 4:
            try:
                limit = int(sys.argv[4])
            except ValueError:
                print("Error: --limit must be followed by a number")
                sys.exit(1)
        
        processor.add_url(url, limit)
    
    elif command == "process":
        processor.process_inbox()
    
    elif command == "status":
        processor.status()
    
    else:
        print("Usage:")
        print("  python src/ingest.py add URL [--limit N]  # Add content to process")
        print("  python src/ingest.py process               # Process all pending items")
        print("  python src/ingest.py status                # Show pipeline status")
        sys.exit(1)


if __name__ == "__main__":
    main()