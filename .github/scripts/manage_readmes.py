#!/usr/bin/env python3
"""
README Manager - Automated README maintenance using Gemini 2.5 Flash

Modes:
1. full-review: Complete review of all README files, updating or creating as needed
2. ensure-exists: Ensure README files exist in all directories, create where missing
3. auto-update: Update READMEs in directories with changed content (triggered by push)
"""

import os
import sys
import json
import pathlib
from typing import List, Dict, Tuple, Optional
import google.generativeai as genai


class READMEManager:
    """Manages README files across the repository using Gemini 2.5 Flash."""

    # Directories to exclude from README management
    EXCLUDED_DIRS = {
        '.git', '.github', 'node_modules', '__pycache__', '.venv', 'venv',
        '.pytest_cache', '.mypy_cache', 'dist', 'build', '.egg-info'
    }

    # File patterns to exclude
    EXCLUDED_FILES = {'.DS_Store', 'Thumbs.db', '.gitkeep'}

    def __init__(self, api_key: str, mode: str, changed_dirs: Optional[List[str]] = None):
        """Initialize the README Manager.

        Args:
            api_key: Google Gemini API key
            mode: Operation mode (full-review, ensure-exists, auto-update)
            changed_dirs: List of directories with changes (for auto-update mode)
        """
        self.mode = mode
        self.changed_dirs = changed_dirs or []
        self.repo_root = pathlib.Path.cwd()

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

        # Load templates
        self.index_template = self._load_template('09-templates/readme/index-directory-readme.md')
        self.content_template = self._load_template('09-templates/readme/content-directory-readme.md')

        print(f"Initialized README Manager in '{mode}' mode")
        if self.changed_dirs:
            print(f"Changed directories: {', '.join(self.changed_dirs)}")

    def _load_template(self, template_path: str) -> str:
        """Load a README template file."""
        try:
            full_path = self.repo_root / template_path
            return full_path.read_text()
        except FileNotFoundError:
            print(f"Warning: Template not found at {template_path}")
            return ""

    def _should_process_directory(self, dir_path: pathlib.Path) -> bool:
        """Check if a directory should be processed."""
        # Skip if directory name is in exclusion list
        if dir_path.name in self.EXCLUDED_DIRS:
            return False

        # Skip if any parent is in exclusion list
        for parent in dir_path.parents:
            if parent.name in self.EXCLUDED_DIRS:
                return False

        return True

    def _get_all_directories(self) -> List[pathlib.Path]:
        """Get all directories in the repository, sorted by depth (deepest first)."""
        directories = []

        for root, dirs, _ in os.walk(self.repo_root):
            root_path = pathlib.Path(root)

            # Remove excluded directories from traversal
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]

            # Add directories that should be processed
            for dir_name in dirs:
                dir_path = root_path / dir_name
                if self._should_process_directory(dir_path):
                    directories.append(dir_path)

        # Sort by depth (deepest first) and then alphabetically
        directories.sort(key=lambda p: (-len(p.parts), str(p)))

        return directories

    def _get_directories_to_process(self) -> List[pathlib.Path]:
        """Get directories to process based on the current mode."""
        if self.mode == 'auto-update' and self.changed_dirs:
            # For auto-update, get affected directories and their parents
            affected = set()

            for dir_str in self.changed_dirs:
                if not dir_str or dir_str == '.':
                    continue

                dir_path = self.repo_root / dir_str

                # Add the changed directory
                if dir_path.is_dir() and self._should_process_directory(dir_path):
                    affected.add(dir_path)

                # Add all parents up to repo root
                for parent in dir_path.parents:
                    if parent == self.repo_root:
                        break
                    if self._should_process_directory(parent):
                        affected.add(parent)

            # Sort by depth (deepest first)
            directories = sorted(affected, key=lambda p: (-len(p.parts), str(p)))

            print(f"Processing {len(directories)} affected directories")
            return directories

        else:
            # For full-review and ensure-exists, process all directories
            directories = self._get_all_directories()
            print(f"Processing {len(directories)} total directories")
            return directories

    def _analyze_directory(self, dir_path: pathlib.Path) -> Dict:
        """Analyze a directory's contents and structure."""
        analysis = {
            'path': dir_path,
            'relative_path': dir_path.relative_to(self.repo_root),
            'name': dir_path.name,
            'has_subdirs': False,
            'subdirs': [],
            'has_content_files': False,
            'content_files': [],
            'has_readme': False,
            'readme_content': None,
            'depth': len(dir_path.relative_to(self.repo_root).parts)
        }

        try:
            items = list(dir_path.iterdir())

            for item in items:
                if item.is_dir() and item.name not in self.EXCLUDED_DIRS:
                    analysis['has_subdirs'] = True
                    analysis['subdirs'].append(item.name)
                elif item.is_file() and item.name not in self.EXCLUDED_FILES:
                    if item.name.lower() == 'readme.md':
                        analysis['has_readme'] = True
                        try:
                            analysis['readme_content'] = item.read_text()
                        except Exception as e:
                            print(f"Warning: Could not read README at {item}: {e}")
                    else:
                        analysis['has_content_files'] = True
                        analysis['content_files'].append(item.name)

        except PermissionError:
            print(f"Warning: Permission denied accessing {dir_path}")

        return analysis

    def _determine_template_type(self, analysis: Dict) -> str:
        """Determine which template to use based on directory analysis."""
        # If has subdirectories but no significant content files, use index template
        if analysis['has_subdirs'] and not analysis['has_content_files']:
            return 'index'

        # If has content files (with or without subdirs), use content template
        if analysis['has_content_files']:
            return 'content'

        # If has subdirectories and content files, use content template
        if analysis['has_subdirs'] and analysis['has_content_files']:
            return 'content'

        # Default to index if only has subdirectories
        if analysis['has_subdirs']:
            return 'index'

        # If directory is empty or only has README, skip it
        return 'skip'

    def _collect_context(self, dir_path: pathlib.Path, analysis: Dict) -> str:
        """Collect context about the directory for Gemini."""
        context_parts = []

        context_parts.append(f"Directory: {analysis['relative_path']}")
        context_parts.append(f"Directory name: {analysis['name']}")
        context_parts.append(f"Depth level: {analysis['depth']}")

        # Add subdirectory information
        if analysis['subdirs']:
            context_parts.append(f"\nSubdirectories ({len(analysis['subdirs'])}):")
            for subdir in sorted(analysis['subdirs']):
                subdir_readme = dir_path / subdir / 'README.md'
                if subdir_readme.exists():
                    try:
                        readme_content = subdir_readme.read_text()
                        # Extract first line as summary
                        first_line = readme_content.split('\n')[0].strip('# ').strip()
                        context_parts.append(f"  - {subdir}/: {first_line}")
                    except Exception:
                        context_parts.append(f"  - {subdir}/")
                else:
                    context_parts.append(f"  - {subdir}/")

        # Add content file information
        if analysis['content_files']:
            context_parts.append(f"\nContent files ({len(analysis['content_files'])}):")
            for filename in sorted(analysis['content_files'])[:20]:  # Limit to first 20
                file_path = dir_path / filename
                try:
                    # Get file size and extension
                    size = file_path.stat().st_size
                    ext = file_path.suffix
                    context_parts.append(f"  - {filename} ({ext}, {size} bytes)")

                    # For markdown files, include a preview
                    if ext == '.md' and size < 50000:  # Only for reasonably sized files
                        try:
                            content = file_path.read_text()
                            lines = content.split('\n')[:10]  # First 10 lines
                            preview = '\n    '.join(lines)
                            context_parts.append(f"    Preview:\n    {preview}\n")
                        except Exception:
                            pass

                except Exception as e:
                    context_parts.append(f"  - {filename} (error reading: {e})")

        # Add parent context
        if dir_path.parent != self.repo_root:
            parent_readme = dir_path.parent / 'README.md'
            if parent_readme.exists():
                try:
                    parent_content = parent_readme.read_text()
                    first_lines = '\n'.join(parent_content.split('\n')[:5])
                    context_parts.append(f"\nParent directory context:\n{first_lines}")
                except Exception:
                    pass

        # Add existing README if present
        if analysis['has_readme'] and analysis['readme_content']:
            context_parts.append(f"\nExisting README content:\n{analysis['readme_content']}")

        return '\n'.join(context_parts)

    def _generate_readme_with_gemini(self, dir_path: pathlib.Path, analysis: Dict,
                                     template_type: str) -> Optional[str]:
        """Generate or update README content using Gemini."""
        template = self.index_template if template_type == 'index' else self.content_template
        context = self._collect_context(dir_path, analysis)

        # Determine if this is an update or creation
        action = "update" if analysis['has_readme'] else "create"

        prompt = f"""You are a technical documentation expert helping to maintain README files for a design and technology repository.

Repository Context:
This is the "Syntax & Empathy Companion" repository - a Jekyll-based site with structured content about design leadership, AI collaboration, and technical workflows for design professionals.

Task: {action.capitalize()} a README.md file for the following directory.

{context}

Template to use ({template_type} directory):
{template}

Instructions:
1. Analyze the directory structure and content provided above
2. {'Update the existing README to ensure accuracy and completeness' if action == 'update' else 'Create a new README using the appropriate template'}
3. Fill in all template sections with specific, accurate information based on the actual directory contents
4. Use clear, professional language appropriate for design professionals
5. Ensure the README helps visitors navigate and understand the content without guesswork
6. Maintain consistency with parent and sibling directory READMEs where applicable
7. For index directories: focus on navigation and structure
8. For content directories: focus on what's inside and why it matters
9. Remove any template comments (<!-- ... -->) from the final output
10. Keep the tone informative and professional, similar to existing content in the repository

Return ONLY the complete README.md content, with no preamble or explanation.
"""

        try:
            response = self.model.generate_content(prompt)
            readme_content = response.text.strip()

            # Basic validation
            if len(readme_content) < 100:
                print(f"Warning: Generated README for {dir_path} seems too short")
                return None

            return readme_content

        except Exception as e:
            print(f"Error generating README for {dir_path}: {e}")
            return None

    def _should_update_readme(self, analysis: Dict, new_content: str) -> bool:
        """Determine if README should be updated."""
        if not analysis['has_readme']:
            return True  # Always create if doesn't exist

        if self.mode == 'full-review':
            return True  # Always update in full-review mode

        if self.mode == 'ensure-exists':
            return False  # Only create, don't update

        if self.mode == 'auto-update':
            # Update if content has changed meaningfully
            old_content = analysis['readme_content'] or ""

            # Remove whitespace for comparison
            old_normalized = ' '.join(old_content.split())
            new_normalized = ' '.join(new_content.split())

            # Check if content is substantially different (>5% difference)
            if old_normalized == new_normalized:
                return False

            return True

        return False

    def _write_readme(self, dir_path: pathlib.Path, content: str) -> bool:
        """Write README content to file."""
        readme_path = dir_path / 'README.md'

        try:
            readme_path.write_text(content)
            print(f"✓ Written: {readme_path.relative_to(self.repo_root)}")
            return True
        except Exception as e:
            print(f"✗ Error writing {readme_path}: {e}")
            return False

    def process_directories(self):
        """Main processing logic for managing READMEs."""
        directories = self._get_directories_to_process()

        if not directories:
            print("No directories to process")
            return

        stats = {'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        for dir_path in directories:
            try:
                print(f"\n--- Processing: {dir_path.relative_to(self.repo_root)}")

                # Analyze directory
                analysis = self._analyze_directory(dir_path)

                # Skip if README exists in ensure-exists mode
                if self.mode == 'ensure-exists' and analysis['has_readme']:
                    print(f"  → README exists, skipping")
                    stats['skipped'] += 1
                    continue

                # Determine template type
                template_type = self._determine_template_type(analysis)

                if template_type == 'skip':
                    print(f"  → No content to document, skipping")
                    stats['skipped'] += 1
                    continue

                print(f"  → Template type: {template_type}")

                # Generate README content
                new_content = self._generate_readme_with_gemini(dir_path, analysis, template_type)

                if not new_content:
                    print(f"  → Failed to generate content")
                    stats['errors'] += 1
                    continue

                # Decide whether to write
                if self._should_update_readme(analysis, new_content):
                    if self._write_readme(dir_path, new_content):
                        if analysis['has_readme']:
                            stats['updated'] += 1
                        else:
                            stats['created'] += 1
                else:
                    print(f"  → No update needed")
                    stats['skipped'] += 1

            except Exception as e:
                print(f"✗ Error processing {dir_path}: {e}")
                stats['errors'] += 1

        # Print summary
        print("\n" + "="*60)
        print("README Management Summary")
        print("="*60)
        print(f"Created:  {stats['created']}")
        print(f"Updated:  {stats['updated']}")
        print(f"Skipped:  {stats['skipped']}")
        print(f"Errors:   {stats['errors']}")
        print("="*60)


def main():
    """Main entry point."""
    # Get configuration from environment
    api_key = os.getenv('GEMINI_API_KEY')
    mode = os.getenv('MODE', 'ensure-exists')
    changed_dirs_json = os.getenv('CHANGED_DIRS', '[]')

    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    # Parse changed directories
    try:
        changed_dirs = json.loads(changed_dirs_json) if changed_dirs_json else []
    except json.JSONDecodeError:
        print(f"Warning: Could not parse CHANGED_DIRS: {changed_dirs_json}")
        changed_dirs = []

    # Create and run manager
    manager = READMEManager(api_key, mode, changed_dirs)
    manager.process_directories()


if __name__ == '__main__':
    main()
