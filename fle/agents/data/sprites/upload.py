import os

from huggingface_hub import HfApi

api = HfApi(token=os.getenv("HF_TOKEN"))
api.upload_folder(
    folder_path="./input",
    repo_id="Noddybear/fle_images",
    repo_type="dataset",
)
