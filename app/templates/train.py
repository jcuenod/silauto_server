import os
from typing import List, Dict, Optional
from app.config import EXPERIMENTS_DIR


def get_train_config(
    target_scripture_file: str,
    source_scripture_files: List[str],
    lang_codes: Dict[str, str],
    training_corpus: Optional[str] = None,
    test_size: Optional[int] = 250,
    val_size: Optional[int] = 250,
):
    """Generate training configuration YAML content."""

    # Format source files
    sources_text = "\n".join([f"    - {source}" for source in source_scripture_files])

    # Format language codes
    lang_codes_text = ""
    for code, script in lang_codes.items():
        lang_codes_text += f"\n    {code}: {script}"

    # Default training corpus or use provided one
    if training_corpus is None or training_corpus == "":
        corpus_books = ""
    else:
        # List of books like: GEN-DEU;-LEV;NT
        corpus_books = f"""
    corpus_books: {training_corpus}"""

    # Configure test/val sets based on whether sizes are provided
    test_size_line = f"\n    test_size: {test_size}" if test_size else ""
    val_size_line = f"\n    val_size: {val_size}" if val_size else ""

    # Build data type string
    data_type_parts = ["train"]
    if test_size:
        data_type_parts.append("test")
    if val_size:
        data_type_parts.append("val")
    data_type = ",".join(data_type_parts)

    return f"""data:
  corpus_pairs:
  - mapping: mixed_src
    src:
{sources_text}{test_size_line}
    trg: {target_scripture_file}
    type: {data_type}{val_size_line}{corpus_books}
  lang_codes:{lang_codes_text}
  seed: 111
  terms:
    dictionary: false
    include_glosses: true
    train: true
  tokenizer:
    init_unk: false
    share_vocab: false
    src_vocab_size: 2000
    trained_tokens: 1000
    trg_vocab_size: 2000
    update_src: true
    update_trg: true
eval:
  early_stopping: null
  per_device_eval_batch_size: 16
infer:
  infer_batch_size: 8
model: facebook/nllb-200-distilled-1.3B
params:
  learning_rate: 0.0002
  lr_scheduler_type: cosine
  warmup_steps: 1000
train:
  auto_grad_acc: true
  max_steps: 5000
"""


def create_train_config_for(
    project_id: str,
    target_scripture_file: str,
    source_scripture_files: List[str],
    lang_codes: Dict[str, str],
    training_corpus: Optional[str] = None,
    experiment_suffix: Optional[str] = None,
    test_size: Optional[int] = 250,
    val_size: Optional[int] = 250,
):
    """Create training configuration file and return the experiment name."""

    if len(source_scripture_files) == 0:
        raise Exception("No source scripture files specified")

    base_folder = os.path.join(EXPERIMENTS_DIR, project_id)
    base_train_folder_name = (
        source_scripture_files[0].split("-", 1)[-1]
        if len(source_scripture_files) == 1
        else "mixed"
    )

    # Add suffix if provided (e.g., ".all")
    train_folder_name = (
        f"{base_train_folder_name}{experiment_suffix}"
        if experiment_suffix
        else base_train_folder_name
    )
    train_folder = os.path.join(base_folder, train_folder_name)

    # Handle folder conflicts by appending numeric suffix
    numeric_suffix = 1
    folder_name = train_folder_name
    while os.path.exists(train_folder):
        folder_name = f"{train_folder_name}_{numeric_suffix}"
        train_folder = os.path.join(base_folder, folder_name)
        numeric_suffix += 1

    # Create the folder
    os.makedirs(train_folder, exist_ok=True)

    # Write config file
    config_path = os.path.join(train_folder, "config.yml")
    with open(config_path, "w") as f:
        f.write(
            get_train_config(
                target_scripture_file,
                source_scripture_files,
                lang_codes,
                training_corpus,
                test_size=test_size,
                val_size=val_size,
            )
        )

    # Return the full experiment name
    final_experiment_name = f"{project_id}/{folder_name}"
    return final_experiment_name
