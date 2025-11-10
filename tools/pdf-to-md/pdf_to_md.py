"""PDF to Markdown conversion tool using marker-pdf."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import click
import yaml
from marker.convert import convert_single_pdf
from marker.models import load_all_models
from marker.settings import settings

from tools._shared.filters import apply_content_filter
from tools._shared.security import sanitize_filename

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def validate_pdf_file(file_path: Path) -> bool:
    """
    Check if file exists and is in .pdf format.

    Args:
        file_path: Path to the file to validate

    Returns:
        True if file exists and has .pdf extension, False otherwise
    """
    return file_path.exists() and file_path.suffix.lower() == ".pdf"


def output_folder_exists(output_dir: Path, pdf_stem: str) -> bool:
    """
    Check if output folder already exists for this PDF.

    Args:
        output_dir: Base output directory
        pdf_stem: PDF filename without extension

    Returns:
        True if output folder exists, False otherwise
    """
    folder = output_dir / pdf_stem
    return folder.exists()


def save_images(images_dict: dict[str, Any], output_folder: Path) -> None:
    """
    Save extracted images to the output folder.

    Args:
        images_dict: Dictionary mapping filenames to PIL Image objects
        output_folder: Directory to save images to
    """
    for filename, image in images_dict.items():
        image_path = output_folder / sanitize_filename(filename)
        try:
            image.save(image_path)
            logger.info(f"Saved image: {filename}")
        except Exception as save_error:
            logger.error(f"Error saving image {filename}: {save_error}")


def apply_config_to_settings(config: dict[str, Any], debug_data_folder: Path) -> None:
    """
    Apply configuration values to marker settings.

    Args:
        config: Configuration dictionary from config.yaml
        debug_data_folder: Directory for debug data files
    """
    # Apply general settings
    if "image_dpi" in config:
        settings.IMAGE_DPI = config["image_dpi"]
    if "extract_images" in config:
        settings.EXTRACT_IMAGES = config["extract_images"]
    if "paginate_output" in config:
        settings.PAGINATE_OUTPUT = config["paginate_output"]
    if "torch_device" in config and config["torch_device"] is not None:
        settings.TORCH_DEVICE = config["torch_device"]

    # Apply OCR settings
    if "ocr_all_pages_global" in config:
        settings.OCR_ALL_PAGES = config["ocr_all_pages_global"]
    if "ocr_engine" in config:
        settings.OCR_ENGINE = config["ocr_engine"]
    if "default_lang" in config:
        settings.DEFAULT_LANG = config["default_lang"]

    # Apply layout & structure settings
    if "bad_span_types" in config:
        settings.BAD_SPAN_TYPES = config["bad_span_types"]
    if "bbox_intersection_thresh" in config:
        settings.BBOX_INTERSECTION_THRESH = config["bbox_intersection_thresh"]

    # Set debug settings (not from config, hardcoded as specified)
    settings.DEBUG = True
    settings.DEBUG_DATA_FOLDER = str(debug_data_folder)
    settings.DEBUG_LEVEL = 1

    logger.info("Applied configuration to marker settings")
    logger.info(
        f"Debug enabled: {settings.DEBUG}, Debug folder: {settings.DEBUG_DATA_FOLDER}, "
        f"Debug level: {settings.DEBUG_LEVEL}"
    )


def main(config_path: Path) -> None:
    """Main function to convert all .pdf files in the input directory.

    Args:
        config_path: Path to the YAML configuration file
    """
    # Calculate project root from config path
    # If config is "settings/pdf-to-md.yaml", parent is project root
    project_root = config_path.parent.resolve()
    # If the parent is "settings", go up one more level to get project root
    if project_root.name == "settings":
        project_root = project_root.parent

    input_dir = project_root / "input" / "pdf-to-md"

    # Use the tools/pdf-to-md directory for debug data
    debug_data_folder = project_root / "tools" / "pdf-to-md"

    # Validate input directory exists
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return

    # Load configuration
    try:
        with open(config_path) as config_file:
            config = yaml.safe_load(config_file)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        return
    except yaml.YAMLError as yaml_error:
        logger.error(f"Error parsing configuration file: {yaml_error}")
        return

    # Get output directory from config, default to "output/pdf-to-md" relative to project root
    output_dir_config = config.get("output_dir", "output/pdf-to-md")
    output_dir = project_root / output_dir_config

    # Create output directory if it doesn't exist
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using output directory: {output_dir}")
    except Exception as mkdir_error:
        logger.error(f"Error creating output directory {output_dir}: {mkdir_error}")
        return

    # Apply configuration to marker settings
    apply_config_to_settings(config, debug_data_folder)

    # Extract function parameters from config
    max_pages: int | None = config.get("max_pages")
    start_page: int | None = config.get("start_page")
    metadata: dict[str, Any] | None = config.get("metadata")
    langs: list[str] | None = config.get("langs")
    batch_multiplier: int = config.get("batch_multiplier", 1)
    ocr_all_pages: bool = config.get("ocr_all_pages", False)

    # Extract filter configuration
    filter_config = config.get("filters", {})
    max_age_days: int | None = filter_config.get("max_age_days")
    include_keywords: list[str] = filter_config.get("include_keywords", [])
    exclude_keywords: list[str] = filter_config.get("exclude_keywords", [])

    # Scan input directory for .pdf files
    pdf_files = list(input_dir.glob("*.pdf"))

    if not pdf_files:
        logger.info(f"No .pdf files found in {input_dir}")
        return

    logger.info(f"Found {len(pdf_files)} .pdf file(s) to convert")

    # Load marker-pdf models once
    logger.info("Loading marker-pdf models...")
    try:
        model_list = load_all_models()
    except Exception as model_error:
        logger.error(f"Error loading models: {model_error}")
        return

    # Process each .pdf file
    for index, pdf_file in enumerate(pdf_files, start=1):
        logger.info(f"Processing file {index}/{len(pdf_files)}: {pdf_file.name}")

        # Validate file
        if not validate_pdf_file(pdf_file):
            logger.warning(f"Skipping invalid file: {pdf_file.name}")
            continue

        # Check if output folder already exists
        if output_folder_exists(output_dir, pdf_file.stem):
            logger.info(f"Output folder already exists for {pdf_file.name}, skipping")
            continue

        # Create output folder
        output_folder = output_dir / sanitize_filename(pdf_file.stem)
        try:
            output_folder.mkdir(parents=True, exist_ok=True)
        except Exception as mkdir_error:
            logger.error(f"Error creating output folder for {pdf_file.name}: {mkdir_error}")
            continue

        # Convert PDF to markdown
        try:
            logger.info(f"Converting {pdf_file.name}...")
            markdown_content, images_dict, output_metadata = convert_single_pdf(
                str(pdf_file),
                model_list,
                max_pages=max_pages,
                start_page=start_page,
                metadata=metadata,
                langs=langs,
                batch_multiplier=batch_multiplier,
                ocr_all_pages=ocr_all_pages,
            )
            logger.info(f"Conversion complete for {pdf_file.name}")
        except Exception as conversion_error:
            logger.error(f"Error converting {pdf_file.name}: {conversion_error}")
            continue

        # Get PDF file metadata
        pdf_stat = pdf_file.stat()
        created_date_ts = datetime.fromtimestamp(pdf_stat.st_mtime)

        # Apply content filters if configured
        if max_age_days or include_keywords or exclude_keywords:
            content_data = {
                "title": pdf_file.stem,
                "text": markdown_content,
                "body": "",  # Not applicable for PDFs
                "created_date": created_date_ts,
            }

            filter_criteria = {
                "max_age_days": max_age_days,
                "include_keywords": include_keywords,
                "exclude_keywords": exclude_keywords,
            }

            should_include = apply_content_filter(content_data, filter_criteria)

            if not should_include:
                logger.info(f"Filtered out {pdf_file.name}")
                # Remove the created output folder since we're not saving
                try:
                    output_folder.rmdir()
                except Exception:
                    pass
                continue

        # Create frontmatter with PDF metadata
        created_date = created_date_ts.isoformat()
        collected_date = datetime.now().isoformat()
        page_count = output_metadata.get("pages", None) if output_metadata else None

        frontmatter_dict = {
            "title": pdf_file.stem,
            "source": "pdf-to-md",
            "created_date": created_date,
            "collected_date": collected_date,
            "page_count": page_count,
        }

        frontmatter_yaml = yaml.dump(frontmatter_dict, default_flow_style=False, allow_unicode=True)
        full_content = f"---\n{frontmatter_yaml}---\n\n{markdown_content}"

        # Save markdown file with frontmatter
        markdown_file = output_folder / f"{pdf_file.stem}.md"
        try:
            with open(markdown_file, "w", encoding="utf-8") as markdown_file_handle:
                markdown_file_handle.write(full_content)
            logger.info(f"Markdown saved to: {markdown_file.name}")
        except Exception as write_error:
            logger.error(f"Error writing markdown file {markdown_file.name}: {write_error}")
            continue

        # Save extracted images
        if images_dict:
            logger.info(f"Saving {len(images_dict)} image(s)...")
            save_images(images_dict, output_folder)
        else:
            logger.info("No images extracted from PDF")

    logger.info("Conversion complete!")


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    default="settings/pdf-to-md.yaml",
    help="Path to YAML configuration file (default: settings/pdf-to-md.yaml)",
)
def cli(config: Path) -> None:
    """PDF to Markdown conversion tool using marker-pdf.

    Converts all .pdf files in the input/pdf-to-md directory and saves
    the output as markdown files with extracted images in organized folders.
    """
    main(config)


if __name__ == "__main__":
    cli()
