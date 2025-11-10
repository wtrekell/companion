"""Audio transcription tool using faster-whisper."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import click
import yaml
from faster_whisper import WhisperModel
from pydub import AudioSegment

from tools._shared.filters import apply_content_filter
from tools._shared.security import sanitize_filename

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def validate_m4a_file(file_path: Path) -> bool:
    """
    Check if file exists and is in .m4a format.

    Args:
        file_path: Path to the file to validate

    Returns:
        True if file exists and has .m4a extension, False otherwise
    """
    return file_path.exists() and file_path.suffix.lower() == ".m4a"


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to [HH:MM:SS] format.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string in [HH:MM:SS] format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"


def get_audio_duration(file_path: Path) -> str:
    """
    Get duration of audio file using pydub.

    Args:
        file_path: Path to the audio file

    Returns:
        Formatted duration string in [HH:MM:SS] format
    """
    audio = AudioSegment.from_file(str(file_path), format="m4a")
    duration_seconds = len(audio) / 1000.0  # pydub returns milliseconds
    return format_timestamp(duration_seconds)


def create_markdown_output(
    filename: str,
    duration: str,
    segments: list[Any],
    include_timestamps: bool,
    paragraph_detection_enabled: bool = False,
    pause_threshold: float = 2.0,
    min_paragraph_chars: int = 100,
    created_date: str = "",
    collected_date: str = "",
    model: str = "medium",
    language: str = "en",
) -> str:
    """
    Generate markdown formatted transcription output.

    Args:
        filename: Name of the source audio file
        duration: Total duration of the audio file
        segments: List of transcription segments from faster-whisper
        include_timestamps: Whether to include timestamp markers in output
        paragraph_detection_enabled: Whether to use intelligent paragraph detection
        pause_threshold: Minimum pause duration (seconds) to trigger new paragraph
        min_paragraph_chars: Minimum characters before allowing a paragraph break
        created_date: ISO timestamp when audio file was created
        collected_date: ISO timestamp when transcription was performed
        model: Whisper model name used for transcription
        language: Language code used for transcription

    Returns:
        Markdown formatted string with YAML frontmatter and transcription
    """
    # Create YAML frontmatter
    frontmatter_dict = {
        "title": filename,
        "source": "transcribe",
        "created_date": created_date,
        "collected_date": collected_date,
        "duration": duration,
        "model": model,
        "language": language,
    }

    frontmatter_yaml = yaml.dump(frontmatter_dict, default_flow_style=False, allow_unicode=True)
    output_lines = [f"---\n{frontmatter_yaml}---\n"]

    # Timestamped mode: show each segment with timestamps (no paragraph detection)
    if include_timestamps:
        for segment in segments:
            text = segment.text.strip()
            start_time = format_timestamp(segment.start)
            end_time = format_timestamp(segment.end)
            output_lines.append(f"{start_time} -> {end_time}")
            output_lines.append(text)
            output_lines.append("")
    # Paragraph detection mode: combine segments into natural paragraphs
    elif paragraph_detection_enabled:
        paragraphs = _create_paragraphs(segments, pause_threshold, min_paragraph_chars)
        for paragraph in paragraphs:
            output_lines.append(paragraph)
            output_lines.append("")
    # Legacy mode: each segment on its own line
    else:
        for segment in segments:
            text = segment.text.strip()
            output_lines.append(text)
            output_lines.append("")

    return "\n".join(output_lines)


def _create_paragraphs(segments: list[Any], pause_threshold: float, min_paragraph_chars: int) -> list[str]:
    """
    Combine segments into paragraphs based on pause duration between segments.

    Args:
        segments: List of transcription segments from faster-whisper
        pause_threshold: Minimum pause duration (seconds) to trigger new paragraph
        min_paragraph_chars: Minimum characters before allowing a paragraph break

    Returns:
        List of paragraph strings, each combining multiple segments
    """
    if not segments:
        return []

    paragraphs: list[str] = []
    current_paragraph_segments: list[str] = []
    previous_segment_end: float = 0.0

    for segment in segments:
        text = segment.text.strip()
        current_segment_start = segment.start
        current_segment_end = segment.end

        # Calculate pause duration between previous segment end and current segment start
        pause_duration = current_segment_start - previous_segment_end if previous_segment_end > 0 else 0.0

        # Determine if we should start a new paragraph
        should_break = False
        if pause_duration >= pause_threshold:
            # Check if current paragraph meets minimum length requirement
            current_paragraph_text = " ".join(current_paragraph_segments)
            if len(current_paragraph_text) >= min_paragraph_chars:
                should_break = True

        # If breaking to new paragraph, save the current one and start fresh
        if should_break and current_paragraph_segments:
            paragraphs.append(" ".join(current_paragraph_segments))
            current_paragraph_segments = []

        # Add current segment to the paragraph being built
        current_paragraph_segments.append(text)
        previous_segment_end = current_segment_end

    # Add the final paragraph if it has content
    if current_paragraph_segments:
        paragraphs.append(" ".join(current_paragraph_segments))

    return paragraphs


def main(config_path: Path) -> None:
    """Main function to transcribe all .m4a files in the input directory.

    Args:
        config_path: Path to the YAML configuration file
    """
    # Calculate project root from config path
    # If config is "settings/transcribe.yaml", parent is project root
    project_root = config_path.parent.resolve()
    # If the parent is "settings", go up one more level to get project root
    if project_root.name == "settings":
        project_root = project_root.parent

    input_dir = project_root / "input" / "transcribe"

    # Validate input directory exists
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return

    # Load configuration
    try:
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        return
    except yaml.YAMLError as yaml_error:
        logger.error(f"Error parsing configuration file: {yaml_error}")
        return

    # Get output directory from config, or use default
    output_dir_config = config.get("output_dir", "output/transcriptions")
    # Construct output directory path relative to project root
    output_dir = project_root / output_dir_config

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Using output directory: {output_dir}")

    # Get configuration values
    model_name = config.get("model", "medium")
    language = config.get("language", "en")
    temperature = config.get("temperature", 0)
    include_timestamps = config.get("include_timestamps", True)

    # Get paragraph detection settings
    paragraph_config = config.get("paragraph_detection", {})
    paragraph_detection_enabled = paragraph_config.get("enabled", False)
    pause_threshold = paragraph_config.get("pause_threshold", 2.0)
    min_paragraph_chars = paragraph_config.get("min_paragraph_chars", 100)

    # Extract filter configuration
    filter_config = config.get("filters", {})
    max_age_days: int | None = filter_config.get("max_age_days")
    include_keywords: list[str] = filter_config.get("include_keywords", [])
    exclude_keywords: list[str] = filter_config.get("exclude_keywords", [])

    # Scan input directory for .m4a files
    m4a_files = list(input_dir.glob("*.m4a"))

    if not m4a_files:
        logger.info(f"No .m4a files found in {input_dir}")
        return

    logger.info(f"Found {len(m4a_files)} .m4a file(s) to transcribe")

    # Load the faster-whisper model once
    logger.info(f"Loading faster-whisper model: {model_name}")
    try:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
    except Exception as model_error:
        logger.error(f"Error loading model: {model_error}")
        return

    # Process each .m4a file
    for index, m4a_file in enumerate(m4a_files, start=1):
        logger.info(f"Processing file {index}/{len(m4a_files)}: {m4a_file.name}")

        # Validate file
        if not validate_m4a_file(m4a_file):
            logger.warning(f"Skipping invalid file: {m4a_file.name}")
            continue

        # Get audio duration
        try:
            duration = get_audio_duration(m4a_file)
        except Exception as duration_error:
            logger.error(f"Error getting duration for {m4a_file.name}: {duration_error}")
            continue

        # Transcribe the audio file
        try:
            logger.info(f"Transcribing {m4a_file.name}...")
            segments, info = model.transcribe(str(m4a_file), language=language, temperature=temperature)
            segments_list = list(segments)  # Convert generator to list
            logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
        except Exception as transcription_error:
            logger.error(f"Error transcribing {m4a_file.name}: {transcription_error}")
            continue

        # Get file metadata for filters and frontmatter
        file_stat = m4a_file.stat()
        created_date_ts = datetime.fromtimestamp(file_stat.st_mtime)

        # Apply content filters if configured
        if max_age_days or include_keywords or exclude_keywords:
            # Combine all segment text for filtering
            transcription_text = " ".join(segment.text for segment in segments_list)

            content_data = {
                "title": m4a_file.stem,
                "text": transcription_text,
                "body": "",  # Not applicable for audio
                "created_date": created_date_ts,
            }

            filter_criteria = {
                "max_age_days": max_age_days,
                "include_keywords": include_keywords,
                "exclude_keywords": exclude_keywords,
            }

            should_include = apply_content_filter(content_data, filter_criteria)

            if not should_include:
                logger.info(f"Filtered out {m4a_file.name}")
                continue

        created_date = created_date_ts.isoformat()
        collected_date = datetime.now().isoformat()

        # Create markdown output with frontmatter
        markdown_content = create_markdown_output(
            m4a_file.name,
            duration,
            segments_list,
            include_timestamps,
            paragraph_detection_enabled,
            pause_threshold,
            min_paragraph_chars,
            created_date,
            collected_date,
            model_name,
            language,
        )

        # Save to output directory
        output_file = output_dir / f"{sanitize_filename(m4a_file.stem)}.md"
        try:
            with open(output_file, "w", encoding="utf-8") as output_file_handle:
                output_file_handle.write(markdown_content)
            logger.info(f"Transcription saved to: {output_file.name}")
        except Exception as write_error:
            logger.error(f"Error writing output file {output_file.name}: {write_error}")
            continue

    logger.info("Transcription complete!")


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="settings/transcribe.yaml",
    help="Path to YAML configuration file (default: settings/transcribe.yaml)",
)
def cli(config: Path) -> None:
    """Audio transcription tool using faster-whisper.

    Transcribes all .m4a files in the input/transcribe directory and saves
    the output as markdown files with optional timestamps and paragraph detection.
    """
    main(config)


if __name__ == "__main__":
    cli()
