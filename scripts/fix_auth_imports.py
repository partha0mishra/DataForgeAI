"""Fix authentication import issues in all accelerators."""

import re
from pathlib import Path


def find_accelerator_apis():
    """Find all accelerator API files."""
    base_path = Path("/home/user/DataForgeAI/accelerators")
    api_files = []

    for accelerator_dir in sorted(base_path.glob("*")):
        if not accelerator_dir.is_dir():
            continue

        possible_paths = [
            accelerator_dir / "api" / "src" / "main.py",
            accelerator_dir / "src" / "api" / "main.py",
            accelerator_dir / "backend" / "src" / "api" / "main.py",
        ]

        for path in possible_paths:
            if path.exists():
                api_files.append(path)
                break

    return api_files


def fix_logger_init(content):
    """Fix logger initialization issues."""
    # Fix corrupted logger calls
    content = re.sub(
        r'get_logger\(__name__,\s*Request,\s*Depends\)',
        'get_logger(__name__)',
        content
    )
    return content


def ensure_request_depends_in_fastapi_import(content):
    """Ensure Request and Depends are in FastAPI import."""
    # Find the FastAPI import line
    pattern = r'from fastapi import ([^\n]+)'
    match = re.search(pattern, content)

    if match:
        imports = match.group(1)
        imports_list = [i.strip() for i in imports.split(',')]

        # Add Request and Depends if not present
        if 'Request' not in imports_list:
            imports_list.append('Request')
        if 'Depends' not in imports_list:
            imports_list.append('Depends')

        new_imports = ', '.join(imports_list)
        content = re.sub(pattern, f'from fastapi import {new_imports}', content, count=1)

    return content


def process_file(file_path):
    """Process a single file."""
    try:
        content = file_path.read_text()

        original_content = content

        # Apply fixes
        content = fix_logger_init(content)
        content = ensure_request_depends_in_fastapi_import(content)

        # Write back if changed
        if content != original_content:
            file_path.write_text(content)
            return True, "Fixed"
        else:
            return True, "No changes needed"

    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    """Fix all accelerator APIs."""
    print("Fixing authentication imports...")

    api_files = find_accelerator_apis()

    for api_file in api_files:
        accelerator_name = api_file.parts[-4 if "backend" in api_file.parts else -3]
        success, message = process_file(api_file)

        status = "✓" if success else "✗"
        print(f"{status} {accelerator_name}: {message}")

    print("Done!")


if __name__ == "__main__":
    main()
