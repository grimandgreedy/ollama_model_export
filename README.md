# Ollama Model Transfer

A utility script which identifies all of the files that ollama associates with the selected model(s)--usually the model, modelfile, template, parameters, and license--and duplicates the files and directory structure to a target location for easy backup or transfer.

## Configuration


Note: the script tries to guess the default path based on your OS. You should only need to change the CUSTOM_OLLAMA_BASE_DIR if you (or your distro's package maintainer) have set it to a different location.

Edit the following variables at the top of `ollama_transfer.py`:

```python
CUSTOM_OUTPUT_DIR = ""           # Set custom output directory (default: ./ollama)
CUSTOM_OLLAMA_BASE_DIR = ""
```

### Default Paths

| Platform | Ollama Base Directory |
|----------|----------------------|
| macOS    | `~/.ollama/models` |
| Windows  | `~/.ollama/models` |
| Linux    | `/var/lib/ollama` `/var/lib/ollama/models` or `/usr/share/ollama` (auto-detected) |


## Usage

OPTIONAL: If you are using linux or macosx install listpick: `python -m pip install listpick` for user-friendly selection.

1. Clone the repo or download `ollama_transfer.py`.


2. Run the script: `python ollama_transfer.py`

3. Select the models you want to copy

4. Select (yes) you want to copy the models.

5. ... Do what you like with them.

## My use case

I made this script because I have multiple systems that run ollama and I want to easily transfer the models between my systems. So my use case is that I download models on system_a and I want to transfer them to system_b. The process here is:

1. Run the script and select the models I want to copy. Follow the prompts and simply copy them to the default ./ollama.

```bash
python ollama_transfer.py
```


2. Once the models I want have been copied to ./ollama I then transfer them via ssh to system_b

```bash
scp -r ./ollama/* system_b:/var/lib/ollama
```


3. Cleanup

```bash
rm -r ./ollama
```



## Output Directory Structure

The script creates the following structure in `OUTPUT_DIR=./ollama/`:

```
ollama/
├── manifests/
│   └── registry.ollama.ai/
│       └── library/
│           └── <model-name>/
│               └── <version>
└── blobs/
    ├── sha256-<hash1>
    ├── sha256-<hash2>
    └── ...
```

## Transferring Models

To transfer the exported models to another machine:

   ```bash
   # Linux
   cp -r ollama/* /var/lib/ollama/

   # macOS/Windows
   cp -r ollama/* ~/.ollama/

   # ssh linux/linux
   scp -r ./ollama/* system_b:/var/lib/ollama/
   ```

Run `ollama list` to verify the models appear
