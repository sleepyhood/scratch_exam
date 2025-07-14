import os
import json


def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        raise FileNotFoundError("설정 파일(config.json)을 찾을 수 없습니다.")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    return config
