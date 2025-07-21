#!/usr/bin/env python3
"""
Simple version bumping script for dbome
Updates version in both pyproject.toml and dbome/__init__.py
"""

import sys
import re
from pathlib import Path


def bump_version(version_type='patch'):
    """Bump version based on type: major, minor, or patch"""
    
    # Read current version from pyproject.toml
    pyproject_path = Path('pyproject.toml')
    content = pyproject_path.read_text()
    
    # Extract current version
    version_match = re.search(r'version = "(\d+)\.(\d+)\.(\d+)"', content)
    if not version_match:
        print("Error: Could not find version in pyproject.toml")
        return False
    
    major, minor, patch = map(int, version_match.groups())
    
    # Bump version based on type
    if version_type == 'major':
        major += 1
        minor = 0
        patch = 0
    elif version_type == 'minor':
        minor += 1
        patch = 0
    elif version_type == 'patch':
        patch += 1
    else:
        print(f"Error: Unknown version type '{version_type}'. Use major, minor, or patch.")
        return False
    
    new_version = f"{major}.{minor}.{patch}"
    
    # Update pyproject.toml
    new_content = re.sub(
        r'version = "\d+\.\d+\.\d+"',
        f'version = "{new_version}"',
        content
    )
    pyproject_path.write_text(new_content)
    print(f"✓ Updated pyproject.toml to version {new_version}")
    
    # Update dbome/__init__.py fallback version
    init_path = Path('dbome/__init__.py')
    init_content = init_path.read_text()
    new_init_content = re.sub(
        r'__version__ = "\d+\.\d+\.\d+"',
        f'__version__ = "{new_version}"',
        init_content
    )
    init_path.write_text(new_init_content)
    print(f"✓ Updated dbome/__init__.py fallback to version {new_version}")
    
    return new_version


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Bump dbome version",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python bump_version.py                  # Bump patch version (0.2.0 -> 0.2.1)
  python bump_version.py minor            # Bump minor version (0.2.0 -> 0.3.0)
  python bump_version.py major            # Bump major version (0.2.0 -> 1.0.0)
  
After bumping, remember to:
  1. Commit the changes
  2. Create a git tag: git tag v0.2.1
  3. Push the tag: git push origin v0.2.1
        """
    )
    
    parser.add_argument(
        'type',
        nargs='?',
        default='patch',
        choices=['major', 'minor', 'patch'],
        help='Version component to bump (default: patch)'
    )
    
    args = parser.parse_args()
    
    new_version = bump_version(args.type)
    if new_version:
        print(f"\n🎉 Version bumped to {new_version}")
        print("\nNext steps:")
        print(f"  1. Review and commit: git add -A && git commit -m 'Bump version to {new_version}'")
        print(f"  2. Create tag: git tag v{new_version}")
        print(f"  3. Push changes: git push origin main v{new_version}")


if __name__ == '__main__':
    main()