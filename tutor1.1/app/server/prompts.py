import os

import config
from logging_utils import log_message


def load_prompt_file(filename):
    path = os.path.join(config.PROMPTS_ROOT, filename)
    try:
        with open(path, "r", encoding="utf-8") as prompt_file:
            return prompt_file.read().strip()
    except OSError as error:
        log_message(f"[prompt] Unable to load {filename}: {error}")
        raise
