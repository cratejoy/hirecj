"""
Podcast ingestion module for Knowledge CLI
Handles RSS feeds, audio download, transcription, and upload
"""
import os
import sys
import json
import hashlib
import shutil
import asyncio
import aiohttp
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse

import feedparser
import requests
import yt_dlp
from openai import OpenAI
from pydub import AudioSegment
from dotenv import load_dotenv

from .utils import print_success, print_error, print_info, print_warning, ProgressBar, parse_api_error
from .audio_utils import chunk_audio, get_audio_duration, validate_audio_file
from .config import Config

# Load environment variables
load_dotenv()


class PodcastIngester:
    """Handles podcast ingestion from RSS feeds"""
    
    def __init__(self, namespace: str, api_base: str):
        self.namespace = namespace
        self.api_base = api_base
        self.config = Config()
        
        # Set up OpenAI client
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        self.openai = OpenAI(api_key=api_key)
        
        # Set up state directories
        self.state_dir = Path.home() / '.knowledge' / 'podcast_state'
        self.processed_dir = self.state_dir / 'processed'
        self.failed_dir = self.state_dir / 'failed'
        self.downloads_dir = self.state_dir / 'downloads'
        
        # Create directories
        for dir_path in [self.processed_dir, self.failed_dir, self.downloads_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    async def ingest_rss_feed(self, rss_url: str, limit: Optional[int] = None,
                            skip_existing: bool = True, keep_audio: bool = False) -> Dict[str, int]:
        """
        Ingest podcasts from an RSS feed
        
        Args:
            rss_url: URL of the RSS feed
            limit: Maximum number of episodes to process
            skip_existing: Skip already processed episodes
            keep_audio: Keep audio files after processing
            
        Returns:
            Dictionary with processing statistics
        """
        print_info(f"📡 Parsing RSS feed: {rss_url}")
        
        # Parse RSS feed
        feed = feedparser.parse(rss_url)
        
        if feed.bozo:
            print_error(f"Failed to parse RSS feed: {feed.bozo_exception}")
            return {"total": 0, "processed": 0, "skipped": 0, "failed": 0}
        
        if not feed.entries:
            print_error("No entries found in RSS feed")
            return {"total": 0, "processed": 0, "skipped": 0, "failed": 0}
        
        feed_title = feed.feed.get('title', 'Unknown Feed')
        print_success(f"✅ Found feed: {feed_title}")
        print_info(f"📊 Total episodes: {len(feed.entries)}")
        
        # Extract audio episodes
        audio_episodes = self._extract_audio_episodes(feed.entries, limit)
        
        if not audio_episodes:
            print_error("No audio episodes found in feed")
            return {"total": 0, "processed": 0, "skipped": 0, "failed": 0}
        
        print_success(f"✅ Found {len(audio_episodes)} audio episode(s)")
        if limit:
            print_info(f"📌 Limited to {limit} episode(s) as requested")
        
        # Process episodes
        stats = {
            "total": len(audio_episodes),
            "processed": 0,
            "skipped": 0,
            "failed": 0
        }
        
        for i, episode in enumerate(audio_episodes, 1):
            print(f"\n{'='*60}")
            print_info(f"Episode {i}/{len(audio_episodes)}: {episode['title'][:50]}...")
            
            try:
                episode_id = self._get_episode_id(episode['url'])
                
                # Check if already processed
                if skip_existing and self._is_episode_processed(episode_id):
                    print_warning("⏭️  Skipping - already processed")
                    stats["skipped"] += 1
                    continue
                
                # Process episode
                success = await self._process_episode(
                    episode,
                    episode_id,
                    feed_title,
                    rss_url,
                    keep_audio
                )
                
                if success:
                    stats["processed"] += 1
                else:
                    stats["failed"] += 1
                    
            except Exception as e:
                print_error(f"Failed to process episode: {str(e)}")
                stats["failed"] += 1
                continue
        
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
        """Extract episodes with audio files from RSS entries"""
        audio_episodes = []
        
        for entry in entries:
            audio_url = None
            
            # Check enclosures first (most common for podcasts)
            if hasattr(entry, 'enclosures'):
                for enc in entry.enclosures:
                    mime_type = enc.get('type', '')
                    if mime_type.startswith('audio/'):
                        audio_url = enc.get('href', enc.get('url'))
                        break
            
            # Also check links
            if not audio_url and hasattr(entry, 'links'):
                for link in entry.links:
                    if link.get('type', '').startswith('audio/'):
                        audio_url = link.get('href')
                        break
            
            if audio_url:
                # Extract episode info
                episode = {
                    'url': audio_url,
                    'title': entry.get('title', 'Unknown Episode'),
                    'published': entry.get('published', 'Unknown'),
                    'description': entry.get('description', '')[:500],
                    'duration': entry.get('itunes_duration', 'Unknown')
                }
                
                audio_episodes.append(episode)
                
                # Check limit
                if limit and len(audio_episodes) >= limit:
                    break
        
        return audio_episodes
    
    def _get_episode_id(self, url: str) -> str:
        """Generate unique ID for episode based on URL"""
        return hashlib.sha256(url.encode()).hexdigest()[:16]
    
    def _is_episode_processed(self, episode_id: str) -> bool:
        """Check if episode has already been processed"""
        processed_file = self.processed_dir / f"{episode_id}.json"
        return processed_file.exists()
    
    async def _process_episode(self, episode: Dict, episode_id: str,
                             feed_title: str, feed_url: str,
                             keep_audio: bool = False) -> bool:
        """Process a single podcast episode"""
        try:
            # Create episode directory
            episode_dir = self.downloads_dir / episode_id
            episode_dir.mkdir(exist_ok=True)
            
            # Download audio
            print_info("💾 Downloading audio...")
            audio_path = await self._download_audio(
                episode['url'],
                episode_dir / 'audio.mp3'
            )
            
            if not audio_path:
                return False
            
            # Validate audio
            if not validate_audio_file(audio_path):
                print_error("Downloaded file is not a valid audio file")
                return False
            
            # Get duration
            duration_seconds, duration_str = get_audio_duration(audio_path)
            print_info(f"Duration: {duration_str}")
            
            # Transcribe
            print_info("🎙️  Transcribing audio...")
            transcript = await self._transcribe_audio(audio_path, episode_id)
            
            if not transcript:
                return False
            
            print_success(f"✅ Transcription complete: {len(transcript):,} characters")
            
            # Prepare content
            content = self._prepare_content(
                episode,
                transcript,
                feed_title,
                feed_url,
                duration_str
            )
            
            # Upload to Knowledge service
            print_info("📤 Uploading to Knowledge service...")
            document_id = await self._upload_to_knowledge(content, episode_id, episode)
            
            if document_id:
                # Mark as processed
                self._mark_processed(
                    episode_id,
                    episode,
                    document_id,
                    len(transcript)
                )
                print_success(f"✅ Uploaded to namespace '{self.namespace}'")
                print_info(f"Document ID: {document_id}")
                
                # Clean up audio if requested
                if not keep_audio:
                    shutil.rmtree(episode_dir)
                    print_info("🧹 Cleaned up audio files")
                
                return True
            else:
                return False
                
        except Exception as e:
            print_error(f"Error processing episode: {str(e)}")
            # Mark as failed
            self._mark_failed(episode_id, episode, str(e))
            return False
    
    async def _download_audio(self, url: str, output_path: Path) -> Optional[Path]:
        """Download audio file with progress tracking"""
        try:
            # Check if already downloaded
            if output_path.exists():
                print_info("Using existing download")
                return output_path
            
            # Download with progress
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            size_mb = downloaded / 1024 / 1024
                            total_mb = total_size / 1024 / 1024
                            print(f"\r  Progress: {size_mb:.1f} MB / {total_mb:.1f} MB ({percent:.1f}%)", 
                                  end='', flush=True)
            
            print()  # New line after progress
            file_size_mb = output_path.stat().st_size / 1024 / 1024
            print_success(f"✅ Download complete! File size: {file_size_mb:.1f} MB")
            
            return output_path
            
        except requests.exceptions.RequestException as e:
            print_error(f"Download failed: {str(e)}")
            return None
        except Exception as e:
            print_error(f"Unexpected error during download: {str(e)}")
            return None
    
    async def _transcribe_audio(self, audio_path: Path, episode_id: str) -> Optional[str]:
        """Transcribe audio using OpenAI Whisper API"""
        try:
            # Check for existing transcript
            transcript_path = self.downloads_dir / episode_id / 'transcript.txt'
            if transcript_path.exists():
                print_info("Using existing transcript")
                return transcript_path.read_text(encoding='utf-8')
            
            # Create chunks directory
            chunks_dir = self.downloads_dir / episode_id / 'chunks'
            chunks_dir.mkdir(exist_ok=True)
            
            # Chunk audio if needed
            chunks = chunk_audio(audio_path, chunks_dir)
            
            # Transcribe chunks
            transcripts = []
            for i, chunk_path in enumerate(chunks, 1):
                print(f"  Transcribing chunk {i}/{len(chunks)}...", end='', flush=True)
                
                try:
                    with open(chunk_path, 'rb') as audio_file:
                        response = self.openai.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text"
                        )
                    
                    transcripts.append(response)
                    print(" ✓")
                    
                except Exception as e:
                    print(f" ✗ Error: {str(e)}")
                    raise
            
            # Combine transcripts
            full_transcript = '\n'.join(transcripts)
            
            # Save transcript
            transcript_path.write_text(full_transcript, encoding='utf-8')
            
            # Clean up chunks
            shutil.rmtree(chunks_dir)
            
            return full_transcript
            
        except Exception as e:
            print_error(f"Transcription failed: {str(e)}")
            return None
    
    def _prepare_content(self, episode: Dict, transcript: str,
                        feed_title: str, feed_url: str,
                        duration: str) -> str:
        """Prepare content with metadata for upload"""
        return f"""Podcast Episode Transcript

Title: {episode['title']}
Podcast: {feed_title}
Published: {episode['published']}
Duration: {duration}
Source: {feed_url}
Audio URL: {episode['url']}

Description:
{episode.get('description', 'No description available')}

Transcript:
{transcript}
"""
    
    async def _upload_to_knowledge(self, content: str, episode_id: str,
                                 episode: Dict) -> Optional[str]:
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
                        return result.get('document_id')
                    else:
                        error_text = await resp.text()
                        error_msg = parse_api_error(error_text)
                        print_error(f"Upload failed: {error_msg}")
                        return None
                        
        except Exception as e:
            print_error(f"Upload error: {str(e)}")
            return None
    
    def _mark_processed(self, episode_id: str, episode: Dict,
                       document_id: str, transcript_length: int):
        """Mark episode as successfully processed"""
        processed_file = self.processed_dir / f"{episode_id}.json"
        processed_data = {
            "episode_id": episode_id,
            "title": episode['title'],
            "url": episode['url'],
            "processed_at": datetime.now().isoformat(),
            "namespace": self.namespace,
            "document_id": document_id,
            "transcript_length": transcript_length
        }
        
        with open(processed_file, 'w') as f:
            json.dump(processed_data, f, indent=2)
    
    def _mark_failed(self, episode_id: str, episode: Dict, error: str):
        """Mark episode as failed"""
        failed_file = self.failed_dir / f"{episode_id}.json"
        failed_data = {
            "episode_id": episode_id,
            "title": episode['title'],
            "url": episode['url'],
            "failed_at": datetime.now().isoformat(),
            "error": error
        }
        
        with open(failed_file, 'w') as f:
            json.dump(failed_data, f, indent=2)
    
    async def process_youtube_video(self, youtube_url: str, keep_audio: bool = False) -> bool:
        """
        Process a YouTube video (bonus feature)
        
        Args:
            youtube_url: URL of the YouTube video
            keep_audio: Keep audio file after processing
            
        Returns:
            True if successful, False otherwise
        """
        print_info(f"🎥 Processing YouTube video: {youtube_url}")
        
        try:
            # Generate video ID
            video_id = hashlib.sha256(youtube_url.encode()).hexdigest()[:16]
            
            # Check if already processed
            if self._is_episode_processed(f"yt_{video_id}"):
                print_warning("Video already processed")
                return True
            
            # Create directory
            video_dir = self.downloads_dir / f"yt_{video_id}"
            video_dir.mkdir(exist_ok=True)
            
            # Download audio
            print_info("💾 Downloading audio from YouTube...")
            audio_path, metadata = await self._download_youtube_audio(youtube_url, video_dir)
            
            if not audio_path:
                return False
            
            # Get duration
            duration_seconds, duration_str = get_audio_duration(audio_path)
            print_info(f"Duration: {duration_str}")
            
            # Transcribe
            print_info("🎙️  Transcribing audio...")
            transcript = await self._transcribe_audio(audio_path, f"yt_{video_id}")
            
            if not transcript:
                return False
            
            print_success(f"✅ Transcription complete: {len(transcript):,} characters")
            
            # Prepare content
            content = f"""YouTube Video Transcript

Title: {metadata.get('title', 'Unknown')}
Channel: {metadata.get('channel', 'Unknown')}
URL: {youtube_url}
Duration: {duration_str}
Upload Date: {metadata.get('upload_date', 'Unknown')}

Description:
{metadata.get('description', 'No description')[:500]}

Transcript:
{transcript}
"""
            
            # Upload to Knowledge service
            print_info("📤 Uploading to Knowledge service...")
            
            # Create fake episode dict for upload
            episode = {
                'title': metadata.get('title', 'Unknown'),
                'url': youtube_url,
                'published': metadata.get('upload_date', 'Unknown')
            }
            
            document_id = await self._upload_to_knowledge(
                content,
                f"yt_{video_id}",
                episode
            )
            
            if document_id:
                # Mark as processed
                self._mark_processed(
                    f"yt_{video_id}",
                    episode,
                    document_id,
                    len(transcript)
                )
                print_success(f"✅ Uploaded to namespace '{self.namespace}'")
                print_info(f"Document ID: {document_id}")
                
                # Clean up if requested
                if not keep_audio:
                    shutil.rmtree(video_dir)
                    print_info("🧹 Cleaned up audio files")
                
                return True
            else:
                return False
                
        except Exception as e:
            print_error(f"Failed to process YouTube video: {str(e)}")
            return False
    
    async def _download_youtube_audio(self, url: str, output_dir: Path) -> Tuple[Optional[Path], Dict]:
        """Download audio from YouTube video"""
        try:
            # Set up yt-dlp options
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(output_dir / 'audio.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
            }
            
            # Extract info and download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Get metadata
                metadata = {
                    'title': info.get('title', 'Unknown'),
                    'channel': info.get('uploader', 'Unknown'),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'description': info.get('description', '')
                }
                
                # Find the audio file
                audio_files = list(output_dir.glob('audio.mp3'))
                if audio_files:
                    audio_path = audio_files[0]
                else:
                    # Look for any mp3 file
                    audio_files = list(output_dir.glob('*.mp3'))
                    if audio_files:
                        audio_path = audio_files[0]
                    else:
                        print_error("No audio file found after download")
                        return None, {}
                
                file_size_mb = audio_path.stat().st_size / 1024 / 1024
                print_success(f"✅ Download complete! File size: {file_size_mb:.1f} MB")
                
                return audio_path, metadata
                
        except Exception as e:
            print_error(f"YouTube download failed: {str(e)}")
            return None, {}