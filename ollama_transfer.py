
#!/usr/bin/env python3
import json
import subprocess
import os
import shutil
import platform
from pathlib import Path


############################################################################
### SET OLLAMA CUSTOM OUTPUT_DIR AND OLLAMA_BASE_DIR HERE
############################################################################
CUSTOM_OUTPUT_DIR = ""
CUSTOM_OLLAMA_BASE_DIR = ""

try:
    from listpick.listpick_app import Picker, start_curses, close_curses
    LISTPICK_AVAILABLE = True
except ImportError:
    LISTPICK_AVAILABLE = False

OUTPUT_DIR = Path("./ollama")

# Set OLLAMA_BASE_DIR based on operating system
system = platform.system()
if system == "Darwin":  # macOS
    OLLAMA_BASE_DIR = Path.home() / ".ollama/models"
elif system == "Windows":
    OLLAMA_BASE_DIR = Path.home() / ".ollama/models"
else:  # Linux and others
    # Check if /var/lib/ollama/models exists, otherwise use /usr/share/ollama/.ollama
    if (Path("/var/lib/ollama") / "blobs").exists():
        OLLAMA_BASE_DIR = Path("/var/lib/ollama")
    elif (Path("/var/lib/ollama/models") / "blobs").exists():
        OLLAMA_BASE_DIR = Path("/var/lib/ollama")
    else:
        OLLAMA_BASE_DIR = Path("/usr/share/ollama/models")

if CUSTOM_OUTPUT_DIR != "":
    OUTPUT_DIR = Path(CUSTOM_OUTPUT_DIR)
if CUSTOM_OLLAMA_BASE_DIR != "":
    OLLAMA_BASE_DIR = Path(CUSTOM_OLLAMA_BASE_DIR)


OLLAMA_MANIFEST_DIR = OLLAMA_BASE_DIR / "manifests/registry.ollama.ai/library"
OLLAMA_BLOB_DIR = OLLAMA_BASE_DIR / "blobs"

def get_installed_models():
    """Run `ollama list` and return a list of model details."""
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
    except FileNotFoundError:
        print("Error: `ollama` command not found. Ensure Ollama is installed and in PATH.")
        exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running `ollama list`: {e.stderr}")
        exit(1)

    lines = result.stdout.strip().splitlines()
    models = []
    for line in lines[1:]:  # Skip header
        parts = line.split()
        if len(parts) >= 4:
            # NAME, ID, SIZE (e.g., "5.2 GB"), MODIFIED (e.g., "2 months ago")
            name = parts[0]
            id_ = parts[1]
            size = parts[2] + " " + parts[3]
            modified = " ".join(parts[4:])
            models.append([name, id_, size, modified])

    # Sort alphabetically by name
    models.sort(key=lambda x: x[0].lower())
    return models

def choose_models_text(models):
    """Text-based model selection for Windows (fallback when listpick isn't available)."""
    print("\nAvailable models:")
    print(f"{'#':<4} {'Name':<30} {'ID':<15} {'Size':<10} {'Modified':<15}")
    print("-" * 75)
    for i, model in enumerate(models, start=1):
        name, id_, size, modified = model
        print(f"{i:<4} {name:<30} {id_:<15} {size:<10} {modified:<15}")

    while True:
        try:
            choice_input = input("\nSelect model number(s) (comma-separated for multiple, 'all' for all models, or press Enter to cancel): ").strip()
            if not choice_input:
                return []

            # Check if user wants all models
            if choice_input.lower() == "all":
                return [model[0] for model in models]

            choices = [int(c.strip()) for c in choice_input.split(",")]
            selected_models = []

            for choice in choices:
                if 1 <= choice <= len(models):
                    selected_models.append(models[choice - 1][0])  # Return just the name
                else:
                    print(f"Invalid choice: {choice}. Try again.")
                    break
            else:
                # All choices were valid
                if selected_models:
                    return selected_models
        except ValueError:
            print("Please enter valid number(s) or 'all'.")

def choose_models_picker(stdscr, models):
    """Interactive picker-based model selection for macOS/Linux."""
    picker_data = {
        "items": models,
        "title": "Select model(s) to export",
        "header": ["Name", "ID", "Size", "Modified"],
        "colour_theme_number": 3,
        "number_columns": False,
        "cell_cursor": False,
        # Sort methods: 0=Orig, 1=lex, 2=LEX, 3=alnum, 4=ALNUM, 5=time, 6=num, 7=size
        "columns_sort_method": [1, 1, 7, 6],  # Name: lex, ID: lex, Size: size, Modified: num
    }
    picker = Picker(stdscr, **picker_data)
    selected_indices, opts, data = picker.run()

    if not selected_indices:
        return []

    # Return just the model names (first column)
    return [models[i][0] for i in selected_indices]

def find_manifest_path(model_name):
    """Return the full path to the manifest file for a model."""
    model_name, model_version = str(model_name).split(":")
    manifest_path = OLLAMA_MANIFEST_DIR / model_name / model_version
    if not manifest_path.exists():
        print(f"Manifest not found for model: {model_name}")
        exit(1)
    return manifest_path

def parse_manifest(manifest_path):
    """Parse manifest JSON and return all digests."""
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    digests = []
    config_digest = manifest.get("config", {}).get("digest")
    if config_digest:
        digests.append(config_digest)

    for layer in manifest.get("layers", []):
        if "digest" in layer:
            digests.append(layer["digest"])
    return digests

def prompt_copy():
    """Ask the user if they want to copy the files."""
    while True:
        response = input("\nDo you want to copy these files to ./ollama/? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'.")

def copy_files(model_name, manifest_path, digests):
    """Copy manifest and blobs to ./ollama/ directory structure."""
    # Parse model name and version
    model_parts = model_name.split(":")
    if len(model_parts) != 2:
        print(f"Error: Invalid model name format: {model_name}")
        return

    model_base, version = model_parts

    # Create directory structure
    manifest_dir = OUTPUT_DIR / "manifests" / "registry.ollama.ai" / "library" / model_base
    blobs_dir = OUTPUT_DIR / "blobs"

    try:
        manifest_dir.mkdir(parents=True, exist_ok=True)
        blobs_dir.mkdir(parents=True, exist_ok=True)

        # Copy manifest (version becomes the filename, not a directory)
        dest_manifest = manifest_dir / version
        print(f"\nCopying manifest to {dest_manifest}...")
        shutil.copy2(manifest_path, dest_manifest)
        print("  ✓ Manifest copied")

        # Copy blobs
        print("\nCopying blobs...")
        for digest in digests:
            blob_file = OLLAMA_BLOB_DIR / digest.replace(":", "-")
            if blob_file.exists():
                dest_blob = blobs_dir / digest.replace(":", "-")
                shutil.copy2(blob_file, dest_blob)
                print(f"  ✓ {digest.replace(':', '-')}")
            else:
                print(f"  ✗ Skipped {digest.replace(':', '-')} (file not found)")

        print(f"\n✓ Files copied successfully to {OUTPUT_DIR.absolute()}")

    except Exception as e:
        print(f"\nError copying files: {e}")

def main():
    models = get_installed_models()
    if not models:
        print("No models found. Try running `ollama pull <model>` first.")
        return

    # Use text-based selection on Windows or when listpick is not available
    if platform.system() == "Windows" or not LISTPICK_AVAILABLE:
        selected_models = choose_models_text(models)
    else:
        stdscr = start_curses()
        try:
            selected_models = choose_models_picker(stdscr, models)
        finally:
            close_curses(stdscr)

    if not selected_models:
        print("No models selected.")
        return

    # Collect all model data
    model_data = []
    for model in selected_models:
        manifest_path = find_manifest_path(model)
        digests = parse_manifest(manifest_path)
        model_data.append((model, manifest_path, digests))

    # Display all paths
    print("\n--- Manifest and Blob Paths ---")
    for model, manifest_path, digests in model_data:
        print(f"\nModel: {model}")
        print(f"Manifest: {manifest_path}")
        print("Blobs:")
        for digest in digests:
            # Replace colon with dash for actual filename
            blob_file = OLLAMA_BLOB_DIR / digest.replace(":", "-")
            print(f"  {blob_file}")
            if not blob_file.exists():
                print(f"    ⚠️  Warning: blob file missing ({blob_file})")

    # Ask if user wants to copy files
    if prompt_copy():
        for model, manifest_path, digests in model_data:
            print(f"\n--- Copying {model} ---")
            copy_files(model, manifest_path, digests)

if __name__ == "__main__":
    main()
