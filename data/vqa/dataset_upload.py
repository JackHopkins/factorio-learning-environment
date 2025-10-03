#!/usr/bin/env python3
"""
Upload VQA dataset to Hugging Face with each JSONL file as a separate split.
"""

from pathlib import Path
from datasets import Dataset, DatasetDict, Features, Value, Image as HFImage
import pandas as pd
import json
from huggingface_hub import create_repo
from typing import Dict, List, Any

# Dataset configuration
DATASET_NAME = "factorio-vqa"  # Change this to your desired dataset name
DATASET_DIR = Path("dataset")
IMAGE_BASE_DIR = Path("../../../dataset/images")  # Adjust based on your setup


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file and return list of dictionaries."""
    data = []
    with open(file_path, "r") as f:
        for line in f:
            data.append(json.loads(line.strip()))
    return data


def get_split_name(filename: str) -> str:
    """Extract a clean split name from the filename."""
    # Remove the date suffix and .jsonl extension
    name = filename.replace(".jsonl", "")

    # Handle different naming patterns
    if "_2025-" in name:
        name = name.split("_2025-")[0]
    elif "_mc_2025-" in name:
        name = name.split("_mc_2025-")[0] + "_mc"

    return name


def prepare_dataset_splits() -> Dict[str, pd.DataFrame]:
    """Load all JSONL files and prepare them as dataset splits."""
    splits = {}

    # Find all JSONL files
    jsonl_files = list(DATASET_DIR.glob("*.jsonl"))
    print(f"Found {len(jsonl_files)} JSONL files")

    for jsonl_file in jsonl_files:
        split_name = get_split_name(jsonl_file.name)
        print(f"Processing {jsonl_file.name} as split '{split_name}'")

        # Load the data
        data = load_jsonl(jsonl_file)

        # Convert to DataFrame for easier handling
        df = pd.DataFrame(data)

        # Ensure all required columns exist
        required_columns = ["question", "answer", "image"]
        for col in required_columns:
            if col not in df.columns:
                print(f"Warning: Missing column '{col}' in {jsonl_file.name}")

        splits[split_name] = df
        print(f"  Loaded {len(df)} examples")

    return splits


def resolve_image_path(image_id: str) -> str:
    """Resolve the full path to an image given its ID."""
    # The image_id already contains the subdirectory (e.g., "blueprints/abc123.png")
    full_path = IMAGE_BASE_DIR / image_id

    if not full_path.exists():
        print(f"Warning: Image not found at {full_path}")
        return None

    return str(full_path)


def create_huggingface_dataset(splits: Dict[str, pd.DataFrame]) -> DatasetDict:
    """Create a HuggingFace DatasetDict from the splits."""
    dataset_dict = {}

    # Define features that are common across all splits
    features = Features(
        {
            "question": Value("string"),
            "answer": Value("string"),
            "image": HFImage(),  # This will handle image loading
            "image_id": Value("string"),  # Keep the original image ID
            "question_type": Value("string"),
            "metadata": Value("string"),  # Store as JSON string
        }
    )

    for split_name, df in splits.items():
        print(f"\nProcessing split: {split_name}")

        # Prepare the data
        split_data = []
        for idx, row in df.iterrows():
            # Resolve image path
            image_path = resolve_image_path(row["image"])
            if image_path is None:
                print(f"Skipping example {idx} due to missing image")
                continue

            # Prepare the example
            example = {
                "question": row["question"],
                "answer": str(row["answer"]),  # Ensure answer is string
                "image": image_path,  # HuggingFace will load this
                "image_id": row["image"],
                "question_type": row.get("question_type", "unknown"),
                "metadata": json.dumps(row.get("metadata", {})),
            }

            split_data.append(example)

        # Create dataset for this split
        if split_data:
            dataset = Dataset.from_list(split_data, features=features)
            dataset_dict[split_name] = dataset
            print(f"  Created dataset with {len(dataset)} examples")
        else:
            print(f"  Warning: No valid examples for split {split_name}")

    return DatasetDict(dataset_dict)


def upload_to_huggingface(
    dataset_dict: DatasetDict, repo_id: str, private: bool = True
):
    """Upload the dataset to Hugging Face Hub."""
    print(f"\nUploading dataset to {repo_id}")

    # Create the repository if it doesn't exist
    try:
        create_repo(repo_id, repo_type="dataset", private=private)
        print(f"Created new dataset repository: {repo_id}")
    except Exception as e:
        print(f"Repository might already exist or error creating: {e}")

    # Push the dataset
    dataset_dict.push_to_hub(
        repo_id,
        private=private,
        commit_message="Upload Factorio VQA dataset with multiple task splits",
    )

    print(f"Successfully uploaded dataset to {repo_id}")


def main():
    """Main function to prepare and upload the dataset."""
    print("=== Factorio VQA Dataset Upload ===\n")

    # Check if directories exist
    if not DATASET_DIR.exists():
        print(f"Error: Dataset directory {DATASET_DIR} not found")
        return

    if not IMAGE_BASE_DIR.exists():
        print(f"Error: Image directory {IMAGE_BASE_DIR} not found")
        return

    # Load all splits
    splits = prepare_dataset_splits()

    if not splits:
        print("Error: No valid splits found")
        return

    print(f"\nTotal splits: {len(splits)}")
    print("Splits:", list(splits.keys()))

    # Create HuggingFace dataset
    dataset_dict = create_huggingface_dataset(splits)

    # Print summary
    print("\n=== Dataset Summary ===")
    for split_name, dataset in dataset_dict.items():
        print(f"{split_name}: {len(dataset)} examples")

    # Upload to HuggingFace (uncomment to actually upload)
    # Replace with your HuggingFace username/organization
    # repo_id = "your-username/factorio-vqa"
    # upload_to_huggingface(dataset_dict, repo_id, private=True)

    # For now, just save locally
    print("\nSaving dataset locally for preview...")
    dataset_dict.save_to_disk("./factorio_vqa_dataset")
    print("Dataset saved to ./factorio_vqa_dataset")

    # Also save the dataset card
    readme_path = DATASET_DIR / "README.md"
    if readme_path.exists():
        print("\nDataset card found at", readme_path)
        print(
            "Remember to upload this README.md to your HuggingFace dataset repository"
        )


if __name__ == "__main__":
    main()
