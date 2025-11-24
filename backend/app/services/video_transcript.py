"""
Video transcript extraction service for recipe videos.
Uses yt-dlp to download audio and faster-whisper for speech-to-text transcription.
"""
import os
import tempfile
import subprocess
from typing import Optional
import asyncio
from app.core.logging import get_logger

logger = get_logger("services.video_transcript")


class VideoTranscriptExtractor:
    """
    Extract transcripts from video URLs (YouTube, TikTok, Instagram, etc.)
    Downloads audio and transcribes using faster-whisper (local STT).
    """
    
    def __init__(self):
        """Initialize the transcript extractor."""
        self.has_ytdlp = self._check_ytdlp()
        self.has_whisper = self._check_whisper()
    
    def _check_ytdlp(self) -> bool:
        """Check if yt-dlp is available."""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def _check_whisper(self) -> bool:
        """Check if faster-whisper is available."""
        try:
            import faster_whisper
            return True
        except ImportError:
            return False
    
    async def extract_transcript(self, url: str, platform: str = None) -> Optional[str]:
        """
        Extract transcript from video URL.
        
        Args:
            url: Video URL (YouTube, TikTok, Instagram, etc.)
            platform: Optional platform hint (youtube, tiktok, instagram)
        
        Returns:
            Transcript text or None if extraction failed
        """
        if not self.has_ytdlp:
            logger.warning("yt-dlp not installed - cannot extract video transcripts")
            logger.info("Install: pip install yt-dlp")
            return None
        
        if not self.has_whisper:
            logger.warning("faster-whisper not installed - cannot transcribe audio")
            logger.info("Install: pip install faster-whisper")
            return None
        
        logger.info(f"Attempting to extract transcript from video...")
        
        # Step 1: Try to get existing captions/subtitles first (faster)
        existing_transcript = await self._get_existing_captions(url)
        if existing_transcript:
            logger.info(f"Found existing captions/subtitles ({len(existing_transcript)} chars)")
            return existing_transcript
        
        # Step 2: Download audio and transcribe
        logger.info(f"No captions found, downloading audio for transcription...")
        audio_file = await self._download_audio(url)
        
        if not audio_file:
            logger.error(f"Failed to download audio from video")
            return None
        
        try:
            # Step 3: Transcribe audio
            logger.info(f"Transcribing audio (this may take a minute)...")
            transcript = await self._transcribe_audio(audio_file)
            
            if transcript:
                logger.info(f"Successfully transcribed {len(transcript)} chars from video audio")
            
            return transcript
            
        finally:
            # Clean up audio file
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)
    
    async def _get_existing_captions(self, url: str) -> Optional[str]:
        """Try to get existing captions/subtitles from video."""
        try:
            # Use yt-dlp to check for and download subtitles
            result = await asyncio.create_subprocess_exec(
                'yt-dlp',
                '--skip-download',
                '--write-auto-sub',
                '--write-sub',
                '--sub-lang', 'en',
                '--sub-format', 'txt',
                '--output', '%(id)s.%(ext)s',
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await result.communicate()
            
            # Try to find the subtitle file
            # yt-dlp saves as {video_id}.en.txt
            import glob
            subtitle_files = glob.glob('*.en.txt')
            
            if subtitle_files:
                subtitle_file = subtitle_files[0]
                with open(subtitle_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                os.remove(subtitle_file)  # Clean up
                return text
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not retrieve existing captions: {str(e)[:100]}")
            return None
    
    async def _download_audio(self, url: str) -> Optional[str]:
        """Download audio from video URL."""
        try:
            # Create temp file for audio
            temp_dir = tempfile.gettempdir()
            audio_path = os.path.join(temp_dir, f"recipe_audio_{os.getpid()}.mp3")
            
            # Use yt-dlp to download only audio
            result = await asyncio.create_subprocess_exec(
                'yt-dlp',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '5',  # Good quality but not huge
                '--max-filesize', '50M',  # Limit file size
                '--output', audio_path,
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0 and os.path.exists(audio_path):
                return audio_path
            else:
                logger.warning(f"yt-dlp error: {stderr.decode()[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            return None
    
    async def _transcribe_audio(self, audio_path: str) -> Optional[str]:
        """Transcribe audio file using faster-whisper with language auto-detection."""
        try:
            from faster_whisper import WhisperModel
            
            # Use base model (good balance of speed/accuracy)
            # Options: tiny, base, small, medium, large
            model_size = "base"
            
            logger.info(f"Loading Whisper {model_size} model...")
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            
            logger.info(f"Detecting language and transcribing audio...")
            
            # First pass: detect language without full transcription
            # This significantly improves quality
            segments, info = model.transcribe(
                audio_path,
                beam_size=5,
                language=None,  # Auto-detect language
                task="transcribe",
                vad_filter=True,  # Voice Activity Detection - removes silence/music
                vad_parameters=dict(
                    min_silence_duration_ms=500,  # Minimum silence duration
                ),
                condition_on_previous_text=True,  # Use context for better accuracy
                temperature=0.0,  # More deterministic (less random)
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6,
            )
            
            # Get detected language info
            detected_language = info.language
            language_probability = info.language_probability
            
            logger.info(f"Detected language: {detected_language} (confidence: {language_probability:.2%})")
            
            # Combine all segments
            transcript_parts = []
            for segment in segments:
                # Clean up the text
                text = segment.text.strip()
                if text:  # Only add non-empty segments
                    transcript_parts.append(text)
            
            transcript = ' '.join(transcript_parts).strip()
            
            if transcript:
                logger.info(f"Transcribed {len(transcript)} chars in {detected_language}")
            
            return transcript if transcript else None
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return None


# Global instance
_extractor = None

def get_transcript_extractor() -> VideoTranscriptExtractor:
    """Get or create global transcript extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = VideoTranscriptExtractor()
    return _extractor
