"""Script to add authentication to all accelerator APIs."""

import re
from pathlib import Path
from typing import List, Tuple


AUTH_IMPORTS = '''# Import authentication
try:
    from dataforge_common import (
        get_current_user,
        get_optional_user,
        require_roles,
        create_auth_router,
        User,
    )
    AUTH_ENABLED = True
except ImportError:
    print("Warning: dataforge-common not installed. Authentication disabled.")
    AUTH_ENABLED = False
'''

AUTH_ROUTER_SETUP = '''
# Include authentication router if available
if AUTH_ENABLED:
    auth_router = create_auth_router()
    app.include_router(auth_router)
'''


def find_accelerator_apis() -> List[Path]:
    """Find all accelerator API files.

    Returns:
        List of paths to main.py files
    """
    base_path = Path("/home/user/DataForgeAI/accelerators")
    api_files = []

    for accelerator_dir in sorted(base_path.glob("*")):
        if not accelerator_dir.is_dir():
            continue

        # Find main.py in various possible locations
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


def already_has_auth(content: str) -> bool:
    """Check if file already has authentication.

    Args:
        content: File content

    Returns:
        True if auth is already integrated
    """
    return "from dataforge_common import" in content and "create_auth_router" in content


def add_auth_imports(content: str) -> str:
    """Add authentication imports to file.

    Args:
        content: File content

    Returns:
        Updated content with auth imports
    """
    # Find the last import statement
    lines = content.split("\n")
    last_import_idx = 0

    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            last_import_idx = i

    # Insert auth imports after last import
    lines.insert(last_import_idx + 1, "\n" + AUTH_IMPORTS)

    return "\n".join(lines)


def add_auth_router(content: str) -> str:
    """Add authentication router to FastAPI app.

    Args:
        content: File content

    Returns:
        Updated content with auth router
    """
    # Find FastAPI app initialization
    pattern = r'app\s*=\s*FastAPI\([^)]*\)'

    def replace_app_init(match):
        app_init = match.group(0)
        # Add description if not present
        if "description=" not in app_init:
            app_init = app_init.replace(")", ', description="DataForge AI Accelerator")')
        return app_init + AUTH_ROUTER_SETUP

    content = re.sub(pattern, replace_app_init, content, count=1)

    return content


def add_request_import(content: str) -> str:
    """Add Request import to FastAPI imports.

    Args:
        content: File content

    Returns:
        Updated content
    """
    # Check if Request is already imported
    if "Request" in content and "from fastapi import" in content:
        return content

    # Add Request to FastAPI import
    pattern = r'from fastapi import ([^)]+)'

    def add_to_imports(match):
        imports = match.group(1)
        if "Request" not in imports:
            return f"from fastapi import {imports}, Request, Depends"
        return match.group(0)

    return re.sub(pattern, add_to_imports, content, count=1)


def process_accelerator_api(file_path: Path) -> Tuple[bool, str]:
    """Process an accelerator API file to add authentication.

    Args:
        file_path: Path to main.py

    Returns:
        Tuple of (success, message)
    """
    try:
        content = file_path.read_text()

        # Check if already has auth
        if already_has_auth(content):
            return True, f"Already has authentication"

        # Add imports
        content = add_request_import(content)
        content = add_auth_imports(content)
        content = add_auth_router(content)

        # Write back
        file_path.write_text(content)

        return True, "Added authentication imports and router"

    except Exception as e:
        return False, f"Error: {str(e)}"


def main():
    """Process all accelerator APIs."""
    print("=" * 70)
    print("Adding Authentication to DataForge Accelerators")
    print("=" * 70)

    api_files = find_accelerator_apis()
    print(f"\nFound {len(api_files)} accelerator APIs\n")

    results = []

    for api_file in api_files:
        accelerator_name = api_file.parent.parent.parent.name
        print(f"Processing {accelerator_name}...")

        success, message = process_accelerator_api(api_file)

        results.append((accelerator_name, success, message))

        status = "✓" if success else "✗"
        print(f"  {status} {message}")

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    successful = sum(1 for _, success, _ in results if success)
    print(f"✓ Successful: {successful}/{len(results)}")

    failed = [name for name, success, _ in results if not success]
    if failed:
        print(f"✗ Failed: {', '.join(failed)}")

    print("\nNote: Endpoint-level authentication must be added manually.")
    print("Use the pattern from accelerators/12-data-governance/src/api/main.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
