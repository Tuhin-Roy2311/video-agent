import os
import shutil
import uuid
from pydub import AudioSegment
from dotenv import load_dotenv
load_dotenv

DOWNLOAD_DIR = 'downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Locate ffmpeg/ffprobe on PATH. Works on Streamlit Cloud (Linux, installed via
# packages.txt) and locally on Windows (as long as ffmpeg's bin folder is on PATH).
# If you haven't added your local ffmpeg folder to PATH, set the FFMPEG_BIN env
# var (e.g. in a .env file) to point at it as a fallback.
_ffmpeg_path = shutil.which("ffmpeg")
_ffprobe_path = shutil.which("ffprobe")

_local_ffmpeg_dir = os.getenv("FFMPEG_BIN")
if _local_ffmpeg_dir:
    os.environ["PATH"] += os.pathsep + _local_ffmpeg_dir
    _ffmpeg_path = _ffmpeg_path or os.path.join(_local_ffmpeg_dir, "ffmpeg.exe")
    _ffprobe_path = _ffprobe_path or os.path.join(_local_ffmpeg_dir, "ffprobe.exe")

if not _ffmpeg_path or not _ffprobe_path:
    raise RuntimeError(
        "ffmpeg/ffprobe not found. Install ffmpeg and ensure it's on PATH, "
        "or set FFMPEG_BIN in your .env to the folder containing ffmpeg.exe/ffprobe.exe."
    )

AudioSegment.converter = _ffmpeg_path
AudioSegment.ffprobe = _ffprobe_path
FFMPEG_BIN = os.path.dirname(_ffmpeg_path)  # kept for the yt-dlp ffmpeg_location option below


def _disable_inherited_proxy() -> None:
    # yt-dlp can pick up these variables even when the downloader option is empty.
    for key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        os.environ.pop(key, None)
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"


def download_youtube_audio(url: str) -> str:
    _disable_inherited_proxy()
    import yt_dlp

    # Download into our own project folder rather than the Windows system
    # Temp directory. System Temp is what's been getting blocked (likely
    # antivirus/Defender real-time scanning locking the file on write);
    # the project's downloads/ folder is already proven to work fine.
    # Use a unique subfolder per run so concurrent runs never collide.
    youtube_dir = os.path.join(DOWNLOAD_DIR, f"yt_{uuid.uuid4().hex[:8]}")
    os.makedirs(youtube_dir, exist_ok=True)
    # Use the video ID instead of its title to avoid Windows filename and
    # path-length problems.
    output_path = os.path.join(youtube_dir, "youtube_%(id)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "proxy": "",
        "ffmpeg_location": FFMPEG_BIN,
        "outtmpl": {"default": output_path},
        "windowsfilenames": True,
        "restrictfilenames": True,
        # Avoid Windows/antivirus blocking yt-dlp's temporary .part file.
        "nopart": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        base, _ = os.path.splitext(ydl.prepare_filename(info))
        return base + ".mp3"


def convert_audio_to_wav(input_file: str, output_file: str) -> str:
    output_path = os.path.splitext(output_file)[0] + ".wav"
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(output_path, format="wav")
    return output_path


def chunk_audio_file(wav_path: str, chunk_mins: int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_length_ms = chunk_mins * 60 * 1000
    chunks = []
    for i, start in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[start:start + chunk_length_ms]
        chunk_path = os.path.join(DOWNLOAD_DIR, f"chunk_{i}.wav")
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)
    return chunks


def process_input(source: str) -> list:
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Downloading audio...")
        audio_path = download_youtube_audio(source)
        wav_path = convert_audio_to_wav(audio_path, os.path.join(DOWNLOAD_DIR, "output.wav"))
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_audio_to_wav(source, os.path.join(DOWNLOAD_DIR, "output.wav"))

    print("Chunking audio...")
    chunks = chunk_audio_file(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks