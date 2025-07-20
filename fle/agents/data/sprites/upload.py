import os

from huggingface_hub import HfApi

api = HfApi(token=os.getenv("HF_TOKEN"))
api.upload_large_folder(
    folder_path="/Users/jackhopkins/PycharmProjects/PaperclipMaximiser/.fle/spritemaps",
    repo_id="Noddybear/fle_images",
    repo_type="dataset",
)
