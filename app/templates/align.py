import os
from datetime import datetime


def get_align_config(target_scripture_file, source_scripture_files):
    align_sources = "\n".join(["    - " + t for t in source_scripture_files]).strip()

    return f"""data:
  aligner: fast_align
  corpus_pairs:
  - type: train
    trg: {target_scripture_file}
    src:
    {align_sources}
    mapping: many_to_many
    test_size: 0
    val_size: 0
  tokenize: false
"""


def create_align_config_for(project_id, target_scripture_file, source_scripture_files):
    # check for folder like SILNLP_EXPERIMENTS_ROOT / project_id / {"align-" yymmdd} (and append "-1" or "-2" if that folder exists)
    # then create config.yml in that folder using get_align_config
    SILNLP_EXPERIMENTS_ROOT = os.environ.get(
        "SILNLP_EXPERIMENTS_ROOT", "/tmp/silnlp_experiments"
    )
    today_str = datetime.now().strftime("%y%m%d")
    base_folder = os.path.join(SILNLP_EXPERIMENTS_ROOT, project_id)
    align_folder_name = f"align-{today_str}"
    align_folder = os.path.join(base_folder, align_folder_name)

    suffix = 1
    while os.path.exists(align_folder):
        align_folder = os.path.join(base_folder, f"{align_folder_name}-{suffix}")
        suffix += 1

    os.makedirs(align_folder, exist_ok=True)

    config_path = os.path.join(align_folder, "config.yml")
    with open(config_path, "w") as f:
        f.write(get_align_config(target_scripture_file, source_scripture_files))

    experiment_name = f"{project_id}/{align_folder_name}-{suffix}"
    return experiment_name
