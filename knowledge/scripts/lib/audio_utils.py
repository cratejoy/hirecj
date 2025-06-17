"""
Audio processing utilities for Knowledge CLI
"""
from pathlib import Path
from typing import List, Tuple
from pydub import AudioSegment
from .utils import print_info, print_warning


def get_audio_duration(audio_path: Path) -> Tuple[float, str]:
    """
    Get audio duration in seconds and formatted string
    
    Returns:
        Tuple of (duration_seconds, formatted_string)
    """
    audio = AudioSegment.from_file(audio_path)
    duration_seconds = len(audio) / 1000
    duration_minutes = duration_seconds / 60
    
    if duration_minutes < 60:
        formatted = f"{duration_minutes:.1f} minutes"
    else:
        hours = int(duration_minutes // 60)
        minutes = int(duration_minutes % 60)
        formatted = f"{hours}h {minutes}m"
    
    return duration_seconds, formatted


def chunk_audio(audio_path: Path, output_dir: Path, max_size_mb: int = 24) -> List[Path]:
    """
    Split audio into chunks under specified size for Whisper API
    
    Args:
        audio_path: Path to audio file
        output_dir: Directory to save chunks
        max_size_mb: Maximum chunk size in MB (default 24MB for Whisper)
    
    Returns:
        List of chunk file paths
    """
    print_info(f"Loading audio file: {audio_path.name}")
    audio = AudioSegment.from_file(audio_path)
    
    # Get duration info
    duration_seconds, duration_str = get_audio_duration(audio_path)
    print_info(f"Audio duration: {duration_str}")
    
    # Calculate chunk duration for target size
    # Assume 128 kbps bitrate for estimation
    bitrate_kbps = 128
    max_duration_ms = (max_size_mb * 8 * 1024) / bitrate_kbps * 1000
    chunk_duration_minutes = max_duration_ms / 1000 / 60
    
    # If audio is short enough, return as single chunk
    if len(audio) <= max_duration_ms:
        output_path = output_dir / "chunk_000.mp3"
        audio.export(output_path, format="mp3", bitrate=f"{bitrate_kbps}k")
        print_info("Audio is small enough - no chunking needed")
        return [output_path]
    
    print_info(f"Splitting into chunks of ~{chunk_duration_minutes:.1f} minutes each")
    
    chunks = []
    for i, start_ms in enumerate(range(0, len(audio), int(max_duration_ms))):
        chunk = audio[start_ms:start_ms + int(max_duration_ms)]
        chunk_path = output_dir / f"chunk_{i:03d}.mp3"
        
        # Calculate chunk duration
        chunk_duration_s = len(chunk) / 1000
        chunk_start_s = start_ms / 1000
        chunk_end_s = (start_ms + len(chunk)) / 1000
        
        print_info(f"Creating chunk {i+1}: {chunk_start_s:.1f}s - {chunk_end_s:.1f}s ({chunk_duration_s:.1f}s)")
        
        # Export with consistent bitrate
        chunk.export(chunk_path, format="mp3", bitrate=f"{bitrate_kbps}k")
        chunks.append(chunk_path)
    
    print_info(f"Created {len(chunks)} chunks")
    return chunks


def estimate_audio_size(duration_seconds: float, bitrate_kbps: int = 128) -> int:
    """
    Estimate audio file size in bytes
    
    Args:
        duration_seconds: Duration in seconds
        bitrate_kbps: Bitrate in kilobits per second
    
    Returns:
        Estimated size in bytes
    """
    return int((bitrate_kbps * duration_seconds * 1024) / 8)


def validate_audio_file(audio_path: Path) -> bool:
    """
    Validate that a file is a valid audio file
    
    Returns:
        True if valid, False otherwise
    """
    try:
        # Try to load a small portion to validate
        audio = AudioSegment.from_file(audio_path)
        # Just accessing duration validates the file
        _ = len(audio)
        return True
    except Exception as e:
        print_warning(f"Invalid audio file {audio_path.name}: {str(e)}")
        return False