"""
Enhanced Media Utilities for Reel Processing
Handles video download, audio extraction, frame sampling
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import timedelta

def download_video(url: str, filename: str) -> Optional[str]:
    """Downloads a video from a CDN URL to a local temp folder."""
    temp_dir = Path("backend/temp")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_filename = "".join([c for c in filename if c.isalnum() or c in ('_', '-')]).rstrip()
    filepath = temp_dir / f"{safe_filename}.mp4"
    
    print(f"   📥 Downloading video...")
    try:
        import requests
        response = requests.get(url, stream=True, timeout=120)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            file_size = filepath.stat().st_size
            print(f"   ✅ Downloaded: {filepath.name} ({file_size / 1024 / 1024:.1f} MB)")
            return str(filepath)
        else:
            print(f"   ❌ Failed: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None

def extract_audio(video_path: str) -> Optional[str]:
    """Extract audio from video file using ffmpeg."""
    video_path = Path(video_path)
    audio_path = video_path.with_suffix('.mp3')
    
    if audio_path.exists():
        audio_path.unlink()
    
    try:
        print(f"   🔊 Extracting audio...")
        cmd = [
            'ffmpeg', '-y', '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'libmp3lame',
            '-q:a', '2',  # Good quality
            str(audio_path)
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=60
        )
        
        if result.returncode == 0 and audio_path.exists():
            file_size = audio_path.stat().st_size
            print(f"   ✅ Audio extracted: {audio_path.name} ({file_size / 1024:.1f} KB)")
            return str(audio_path)
        else:
            print(f"   ❌ FFmpeg failed: {result.stderr[:200]}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"   ❌ FFmpeg timeout")
        return None
    except FileNotFoundError:
        print(f"   ❌ ffmpeg not installed. Run: brew install ffmpeg")
        return None
    except Exception as e:
        print(f"   ❌ Error extracting audio: {e}")
        return None

def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    return 0.0

def extract_frames(video_path: str, interval_seconds: int = 5) -> List[Tuple[str, float]]:
    """
    Extract frames from video at specified intervals.
    
    Returns:
        List of (frame_path, timestamp_seconds) tuples
    """
    video_path = Path(video_path)
    frames_dir = video_path.parent / f"{video_path.stem}_frames"
    frames_dir.mkdir(exist_ok=True)
    
    duration = get_video_duration(str(video_path))
    if duration == 0:
        print(f"   ⚠️ Could not determine video duration")
        return []
    
    print(f"   🎬 Video duration: {duration:.1f}s, extracting frames every {interval_seconds}s...")
    
    frames = []
    try:
        for timestamp in range(0, int(duration), interval_seconds):
            # Format timestamp for ffmpeg
            time_str = str(timedelta(seconds=timestamp))
            frame_path = frames_dir / f"frame_{timestamp:04d}.jpg"
            
            cmd = [
                'ffmpeg', '-y', '-ss', time_str,
                '-i', str(video_path),
                '-vframes', '1',
                '-q:v', '2',  # High quality
                str(frame_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode == 0 and frame_path.exists():
                frames.append((str(frame_path), float(timestamp)))
        
        print(f"   ✅ Extracted {len(frames)} frames")
        return frames
        
    except Exception as e:
        print(f"   ❌ Error extracting frames: {e}")
        return []

def cleanup_media(filepath: str):
    """Delete media file and any associated files (audio, frames)."""
    path = Path(filepath)
    
    # Delete main file
    if path.exists():
        path.unlink()
        print(f"   🗑️  Cleaned up: {path.name}")
    
    # Delete audio file if exists
    audio_path = path.with_suffix('.mp3')
    if audio_path.exists():
        audio_path.unlink()
    
    # Delete frames directory if exists
    frames_dir = path.parent / f"{path.stem}_frames"
    if frames_dir.exists():
        import shutil
        shutil.rmtree(frames_dir)

def get_video_info(video_path: str) -> dict:
    """Get basic video information."""
    info = {
        'duration': get_video_duration(video_path),
        'size_mb': 0,
        'exists': os.path.exists(video_path)
    }
    
    if info['exists']:
        info['size_mb'] = os.path.getsize(video_path) / (1024 * 1024)
    
    return info

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        video = sys.argv[1]
        print(f"Testing media utils with: {video}")
        info = get_video_info(video)
        print(f"Info: {info}")
        
        audio = extract_audio(video)
        if audio:
            print(f"Audio: {audio}")
        
        frames = extract_frames(video, interval_seconds=5)
        print(f"Frames: {len(frames)} extracted")
