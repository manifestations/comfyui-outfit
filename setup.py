#!/usr/bin/env python3
"""
Setup script for ComfyUI Outfit Selection Node
"""

import json
from pathlib import Path


def setup_project():
    """Set up the project structure and verify installation"""
    print("Setting up ComfyUI Outfit Selection Node...")

    # Check if we're in the right directory
    current_dir = Path.cwd()
    if not (current_dir / "dynamic_outfit_node.py").exists():
        print("Error: Please run this script from the comfyui-outfit directory")
        return False

    # Verify data structure
    data_dir = current_dir / "data"
    if not data_dir.exists():
        print("Error: Data directory not found")
        return False

    # Check for required files
    required_files = [
        "dynamic_outfit_node.py",
        "__init__.py",
        "data/poses.json",
        "data/backgrounds.json",
        "data/race.json",
        "data/outfit/female",
    ]

    missing_files: list[str] = []
    for file_path in required_files:
        if not (current_dir / file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print("Error: Missing required files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False

    # Verify JSON files are valid
    json_files = ["data/poses.json", "data/backgrounds.json", "data/race.json"]

    # Add female outfit JSON files
    female_dir = current_dir / "data" / "outfit" / "female"
    if female_dir.exists():
        json_files.extend([str(f) for f in female_dir.glob("*.json")])

    for json_file in json_files:
        try:
            with open(current_dir / json_file, "r", encoding="utf-8") as f:
                json.load(f)
            print(f"✓ {json_file} is valid")
        except json.JSONDecodeError as e:
            print(f"✗ {json_file} has invalid JSON: {e}")
            return False
        except FileNotFoundError:
            print(f"✗ {json_file} not found")
            return False

    # Run tests
    print("\nRunning tests...")
    try:
        import subprocess

        result = subprocess.run(
            ["python", "-m", "unittest", "test_dynamic_outfit_updated.py", "-v"],
            cwd=current_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("✓ All tests passed")
        else:
            print("✗ Some tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"Warning: Could not run tests: {e}")

    print("\n✓ Setup complete!")
    print("\nTo use this node:")
    print("1. Make sure this directory is in your ComfyUI/custom_nodes/ folder")
    print("2. Restart ComfyUI")
    print("3. Look for 'Outfit/Female' category in the node browser")

    return True


if __name__ == "__main__":
    setup_project()
