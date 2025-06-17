#!/usr/bin/env python3
"""
RSS Podcast Ingester for Knowledge Service
Fetches podcasts from RSS feeds, transcribes them, and loads into knowledge namespaces
"""
import sys
import json
import hashlib
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import argparse

import feedparser
import requests
from openai import OpenAI
from pydub import AudioSegment
import yt_dlp

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.lib.utils import print_success, print_error, print_info, print_warning, ProgressBar
from scripts.lib.config import Config


class PodcastIngester:
    """Ingests podcasts from RSS feeds into Knowledge namespaces"""
    
    def __init__(self, namespace: str, api_base: str = None):
        self.namespace = namespace
        self.config = Config()
        self.api_base = api_base or self.config.get('api_base', 'http://localhost:8004')
        self.openai = OpenAI()
        self.work_dir = Path("podcast_workspace")
        self.ensure_directories()
        
    def ensure_directories(self):
        """Create working directories"""
        dirs = ['downloads', 'audio', 'chunks', 'transcripts', 'completed']
        for d in dirs:
            (self.work_dir / d).mkdir(parents=True, exist_ok=True)
    
    async def ingest_rss_feed(self, rss_url: str, limit: Optional[int] = None, 
                            skip_existing: bool = True) -> Dict[str, int]:
        """Ingest podcasts from an RSS feed"""
        print_info(f"Parsing RSS feed: {rss_url}")
        
        # Parse RSS feed
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            print_error("No entries found in RSS feed")
            return {"total": 0, "processed": 0, "skipped": 0, "failed": 0}
        
        feed_title = feed.feed.get('title', 'Unknown Feed')
        print_success(f"Found feed: {feed_title}")
        print_info(f"Total episodes: {len(feed.entries)}")
        
        # Find episodes with audio
        audio_episodes = self._extract_audio_episodes(feed.entries, limit)
        if not audio_episodes:
            print_error("No audio episodes found in feed")
            return {"total": 0, "processed": 0, "skipped": 0, "failed": 0}
        
        print_success(f"Found {len(audio_episodes)} audio episodes")
        if limit:
            print_info(f"Processing first {limit} episodes")
        
        # Process episodes
        stats = {"total": len(audio_episodes), "processed": 0, "skipped": 0, "failed": 0}
        
        for i, episode in enumerate(audio_episodes):
            print(f"\n{'='*60}")
            print_info(f"Episode {i+1}/{len(audio_episodes)}: {episode['title'][:50]}...")
            
            try:
                # Check if already processed
                episode_id = self._get_episode_id(episode['url'])
                if skip_existing and self._is_episode_processed(episode_id):
                    print_warning("Already processed - skipping")
                    stats["skipped"] += 1
                    continue
                
                # Process episode
                success = await self._process_episode(
                    episode, 
                    episode_id, 
                    feed_title, 
                    rss_url
                )
                
                if success:
                    stats["processed"] += 1
                else:
                    stats["failed"] += 1
                    
            except Exception as e:
                print_error(f"Failed to process episode: {str(e)}")
                stats["failed"] += 1
        
        # Summary
        print(f"\n{'='*60}")
        print_success("RSS Feed Processing Complete")
        print_info(f"Total episodes: {stats['total']}")
        print_info(f"Processed: {stats['processed']}")
        print_info(f"Skipped: {stats['skipped']}")
        if stats['failed'] > 0:
            print_warning(f"Failed: {stats['failed']}")
        
        return stats
    
    def _extract_audio_episodes(self, entries: List, limit: Optional[int]) -> List[Dict]:
        """Extract episodes with audio files"""
        audio_episodes = []
        
        for entry in entries:
            audio_url = None
            
            # Check enclosures (most common for podcasts)
            if hasattr(entry, 'enclosures'):
                for enc in entry.enclosures:
                    if enc.get('type', '').startswith('audio/'):
                        audio_url = enc.get('href', enc.get('url'))
                        break
            
            # Check links
            if not audio_url and hasattr(entry, 'links'):
                for link in entry.links:
                    if link.get('type', '').startswith('audio/'):
                        audio_url = link.get('href')
                        break
            
            if audio_url:
                audio_episodes.append({
                    'url': audio_url,
                    'title': entry.get('title', 'Unknown Episode'),
                    'published': entry.get('published', 'Unknown'),
                    'description': entry.get('description', '')[:500]
                })
                
                if limit and len(audio_episodes) >= limit:
                    break
        
        return audio_episodes
    
    def _get_episode_id(self, url: str) -> str:
        """Generate unique ID for episode"""
        return hashlib.md5(url.encode()).hexdigest()[:12]
    
    def _is_episode_processed(self, episode_id: str) -> bool:
        """Check if episode already processed"""
        return (self.work_dir / 'completed' / f"{episode_id}.json").exists()
    
    async def _process_episode(self, episode: Dict, episode_id: str, 
                             feed_title: str, feed_url: str) -> bool:
        """Process a single podcast episode"""
        try:
            # Download audio
            print_info("Downloading audio...")
            audio_path = await self._download_audio(episode['url'], episode_id)
            if not audio_path:
                return False
            
            # Transcribe
            print_info("Transcribing audio...")
            transcript = await self._transcribe_audio(audio_path, episode_id)
            if not transcript:
                return False
            
            # Prepare content with metadata
            content = self._prepare_content(episode, transcript, feed_title, feed_url)
            
            # Upload to Knowledge service
            print_info("Uploading to Knowledge service...")
            success = await self._upload_to_knowledge(content, episode_id, episode)
            
            if success:
                # Mark as completed
                self._mark_completed(episode_id, episode, transcript)
                print_success("Episode processed successfully!")
            
            return success
            
        except Exception as e:
            print_error(f"Error processing episode: {str(e)}")
            return False
    
    async def _download_audio(self, url: str, episode_id: str) -> Optional[Path]:
        """Download audio file"""
        try:
            audio_dir = self.work_dir / 'downloads' / episode_id
            audio_dir.mkdir(exist_ok=True)
            audio_path = audio_dir / 'audio.mp3'
            
            # Skip if already downloaded
            if audio_path.exists():
                print_info("Using existing download")
                return audio_path
            
            # Download with progress
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(audio_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r  Progress: {percent:.1f}%", end='', flush=True)
            
            print()  # New line after progress
            file_size = audio_path.stat().st_size
            print_success(f"Downloaded: {file_size / 1024 / 1024:.1f} MB")
            
            return audio_path
            
        except Exception as e:
            print_error(f"Download failed: {str(e)}")
            return None
    
    async def _transcribe_audio(self, audio_path: Path, episode_id: str) -> Optional[str]:
        """Transcribe audio using Whisper API"""
        try:
            # Check for existing transcript
            transcript_path = self.work_dir / 'transcripts' / f"{episode_id}.txt"
            if transcript_path.exists():
                print_info("Using existing transcript")
                return transcript_path.read_text(encoding='utf-8')
            
            # Load audio
            print_info("Loading audio file...")
            audio = AudioSegment.from_mp3(audio_path)
            duration_seconds = len(audio) / 1000
            print_info(f"Duration: {duration_seconds/60:.1f} minutes")
            
            # Chunk if needed (Whisper has 25MB limit)
            chunks_dir = self.work_dir / 'chunks' / episode_id
            chunks_dir.mkdir(parents=True, exist_ok=True)
            
            chunks = self._chunk_audio(audio, chunks_dir)
            print_info(f"Created {len(chunks)} chunks")
            
            # Transcribe chunks
            transcripts = []
            for i, chunk_path in enumerate(chunks):
                print(f"  Transcribing chunk {i+1}/{len(chunks)}...", end='', flush=True)
                
                with open(chunk_path, 'rb') as f:
                    response = self.openai.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        response_format="text"
                    )
                
                transcripts.append(response)
                print(" ✓")
            
            # Combine transcripts
            full_transcript = '\n'.join(transcripts)
            
            # Save transcript
            transcript_path.parent.mkdir(exist_ok=True)
            transcript_path.write_text(full_transcript, encoding='utf-8')
            
            print_success(f"Transcription complete: {len(full_transcript)} characters")
            return full_transcript
            
        except Exception as e:
            print_error(f"Transcription failed: {str(e)}")
            return None
    
    def _chunk_audio(self, audio: AudioSegment, output_dir: Path, 
                    max_size_mb: int = 24) -> List[Path]:
        """Split audio into chunks under 24MB"""
        # Calculate chunk duration for target size
        bitrate = 128  # kbps
        max_duration_ms = (max_size_mb * 8 * 1024) / bitrate * 1000
        
        chunks = []
        for i, start in enumerate(range(0, len(audio), int(max_duration_ms))):
            chunk = audio[start:start + int(max_duration_ms)]
            chunk_path = output_dir / f"chunk_{i:03d}.mp3"
            chunk.export(chunk_path, format="mp3", bitrate="128k")
            chunks.append(chunk_path)
        
        return chunks
    
    def _prepare_content(self, episode: Dict, transcript: str, 
                        feed_title: str, feed_url: str) -> str:
        """Prepare content with metadata for upload"""
        return f"""Podcast Episode Transcript

Title: {episode['title']}
Podcast: {feed_title}
Published: {episode['published']}
Source: {feed_url}
Audio URL: {episode['url']}

Description:
{episode.get('description', 'No description available')}

Transcript:
{transcript}
"""
    
    async def _upload_to_knowledge(self, content: str, episode_id: str, 
                                 episode: Dict) -> bool:
        """Upload transcript to Knowledge service"""
        try:
            async with aiohttp.ClientSession() as session:
                # Prepare metadata
                metadata = {
                    "type": "podcast_transcript",
                    "episode_title": episode['title'],
                    "episode_id": episode_id,
                    "published": episode['published'],
                    "source_url": episode['url']
                }
                
                # Create document
                payload = {
                    "content": content,
                    "metadata": metadata
                }
                
                async with session.post(
                    f"{self.api_base}/api/{self.namespace}/documents",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print_success(f"Uploaded to namespace '{self.namespace}'")
                        print_info(f"Document ID: {result.get('document_id', 'unknown')}")
                        return True
                    else:
                        error = await resp.text()
                        print_error(f"Upload failed: {error}")
                        return False
                        
        except Exception as e:
            print_error(f"Upload error: {str(e)}")
            return False
    
    def _mark_completed(self, episode_id: str, episode: Dict, transcript: str):
        """Mark episode as completed"""
        completed_file = self.work_dir / 'completed' / f"{episode_id}.json"
        completed_data = {
            "episode_id": episode_id,
            "title": episode['title'],
            "url": episode['url'],
            "processed_at": datetime.now().isoformat(),
            "transcript_length": len(transcript)
        }
        
        completed_file.parent.mkdir(exist_ok=True)
        with open(completed_file, 'w') as f:
            json.dump(completed_data, f, indent=2)
    
    async def process_youtube_video(self, youtube_url: str) -> bool:
        """Process a YouTube video (bonus feature)"""
        print_info(f"Processing YouTube video: {youtube_url}")
        
        try:
            video_id = hashlib.md5(youtube_url.encode()).hexdigest()[:12]
            
            # Download audio from YouTube
            audio_path = await self._download_youtube_audio(youtube_url, video_id)
            if not audio_path:
                return False
            
            # Transcribe
            transcript = await self._transcribe_audio(audio_path, video_id)
            if not transcript:
                return False
            
            # Get video metadata
            metadata = self._get_youtube_metadata(youtube_url)
            
            # Prepare content
            content = f"""YouTube Video Transcript

Title: {metadata.get('title', 'Unknown')}
Channel: {metadata.get('channel', 'Unknown')}
URL: {youtube_url}
Duration: {metadata.get('duration', 'Unknown')}

Description:
{metadata.get('description', 'No description')[:500]}

Transcript:
{transcript}
"""
            
            # Upload to Knowledge service
            await self._upload_to_knowledge(content, video_id, {
                'title': metadata.get('title', 'Unknown'),
                'url': youtube_url,
                'published': metadata.get('upload_date', 'Unknown')
            })
            
            return True
            
        except Exception as e:
            print_error(f"Failed to process YouTube video: {str(e)}")
            return False
    
    async def _download_youtube_audio(self, url: str, video_id: str) -> Optional[Path]:
        """Download audio from YouTube video"""
        try:
            audio_dir = self.work_dir / 'downloads' / f"yt_{video_id}"
            audio_dir.mkdir(exist_ok=True)
            
            ydl_opts = {
                'outtmpl': str(audio_dir / 'audio.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Find the audio file
            audio_files = list(audio_dir.glob('audio.mp3'))
            if audio_files:
                return audio_files[0]
            
            # Look for any mp3 file
            audio_files = list(audio_dir.glob('*.mp3'))
            if audio_files:
                return audio_files[0]
                
            return None
            
        except Exception as e:
            print_error(f"YouTube download failed: {str(e)}")
            return None
    
    def _get_youtube_metadata(self, url: str) -> Dict:
        """Get YouTube video metadata"""
        try:
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'channel': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'duration': f"{info.get('duration', 0)//60}:{info.get('duration', 0)%60:02d}",
                    'description': info.get('description', '')
                }
        except:
            return {}


async def main():
    """CLI for RSS podcast ingestion"""
    parser = argparse.ArgumentParser(
        description="Ingest podcasts from RSS feeds into Knowledge namespaces"
    )
    
    parser.add_argument(
        'action',
        choices=['rss', 'youtube'],
        help='Type of content to ingest'
    )
    
    parser.add_argument(
        'url',
        help='RSS feed URL or YouTube video URL'
    )
    
    parser.add_argument(
        '-n', '--namespace',
        required=True,
        help='Target namespace for ingestion'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of episodes to process (RSS only)'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='Skip episodes that have already been processed'
    )
    
    parser.add_argument(
        '--api-base',
        help='Knowledge service API base URL (default: from config or http://localhost:8004)'
    )
    
    args = parser.parse_args()
    
    # Create ingester
    ingester = PodcastIngester(args.namespace, args.api_base)
    
    # Process based on action
    if args.action == 'rss':
        stats = await ingester.ingest_rss_feed(
            args.url, 
            limit=args.limit,
            skip_existing=args.skip_existing
        )
        return 0 if stats['failed'] == 0 else 1
    
    elif args.action == 'youtube':
        success = await ingester.process_youtube_video(args.url)
        return 0 if success else 1


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))