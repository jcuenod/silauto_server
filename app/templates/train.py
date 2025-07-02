import os
from typing import List, Dict, Optional
from app.constants import EXPERIMENTS_DIR


def get_train_config(
    target_scripture_file: str,
    source_scripture_files: List[str],
    lang_codes: Dict[str, str],
    training_corpus: Optional[str] = None,
):
    """Generate training configuration YAML content."""

    # Format source files
    sources_text = "\n".join([f"    - {source}" for source in source_scripture_files])

    # Format language codes
    lang_codes_text = ""
    for code, script in lang_codes.items():
        lang_codes_text += f"\n    {code}: {script}"

    # Default training corpus or use provided one
    if training_corpus is None:
        corpus_books = ""
    else:
        # Convert comma-separated string to list of books
        corpus_list = [
            book.strip() for book in training_corpus.split(",") if book.strip()
        ]
        if corpus_list:
            corpus_books = f"""
    corpus_books:
{"\n".join([f"    - {book}" for book in corpus_list])}"""
        else:
            corpus_books = ""

    return f"""data:
  corpus_pairs:
  - mapping: mixed_src
    src:
{sources_text}
    test_size: 250
    trg: {target_scripture_file}
    type: train,test,val
    val_size: 250{corpus_books}
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
):
    """Create training configuration file and return the experiment name."""

    if len(source_scripture_files) == 0:
        raise Exception("No source scripture files specified")

    base_folder = os.path.join(EXPERIMENTS_DIR, project_id)
    train_folder_name = (
        source_scripture_files[0].split("-", 1)[-1]
        if len(source_scripture_files) == 1
        else "mixed"
    )
    train_folder = os.path.join(base_folder, train_folder_name)

    # Handle folder conflicts by appending suffix
    suffix = 1
    folder_name = train_folder_name
    while os.path.exists(train_folder):
        folder_name = f"{train_folder_name}_{suffix}"
        train_folder = os.path.join(base_folder, folder_name)
        suffix += 1

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
            )
        )

    # Return the full experiment name
    final_experiment_name = f"{project_id}/{folder_name}"
    return final_experiment_name
