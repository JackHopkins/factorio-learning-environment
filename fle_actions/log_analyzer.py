import json


def read_entities_log_as_dataframe(log_file_path: str = "logs/entities_log.jsonl"):
    """
    Read the entities log file as a pandas DataFrame.

    Args:
        log_file_path: Path to the entities log file

    Returns:
        pandas.DataFrame with columns 'tick' and 'data'

    Example:
        df = read_entities_log_as_dataframe()
        print(df.head())
        # Access entities at specific tick
        entities_at_tick_100 = df[df['tick'] == 100]['data'].iloc[0]
    """
    try:
        import pandas as pd

        data = []
        with open(log_file_path, "r") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))

        return pd.DataFrame(data)
    except ImportError:
        print("pandas is required to read log files as DataFrames")
        print("Install with: pip install pandas")
        return None
    except FileNotFoundError:
        print(f"Log file not found: {log_file_path}")
        return None


def read_inventory_log_as_dataframe(log_file_path: str = "logs/inventory_log.jsonl"):
    """
    Read the inventory log file as a pandas DataFrame.

    Args:
        log_file_path: Path to the inventory log file

    Returns:
        pandas.DataFrame with columns 'tick' and 'data'

    Example:
        df = read_inventory_log_as_dataframe()
        print(df.head())
        # Access inventory at specific tick
        inventory_at_tick_100 = df[df['tick'] == 100]['data'].iloc[0]
    """
    try:
        import pandas as pd

        data = []
        with open(log_file_path, "r") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))

        return pd.DataFrame(data)
    except ImportError:
        print("pandas is required to read log files as DataFrames")
        print("Install with: pip install pandas")
        return None
    except FileNotFoundError:
        print(f"Log file not found: {log_file_path}")
        return None


def analyze_logs_example():
    """
    Example function showing how to analyze the logged data.
    """
    try:
        # Read both log files
        entities_df = read_entities_log_as_dataframe()
        inventory_df = read_inventory_log_as_dataframe()

        if entities_df is not None and inventory_df is not None:
            print("=== Entities Log Analysis ===")
            print(f"Total ticks logged: {len(entities_df)}")
            print(
                f"Tick range: {entities_df['tick'].min()} to {entities_df['tick'].max()}"
            )
            print("\nFirst few entries:")
            print(entities_df.head())

            print("\n=== Inventory Log Analysis ===")
            print(f"Total ticks logged: {len(inventory_df)}")
            print(
                f"Tick range: {inventory_df['tick'].min()} to {inventory_df['tick'].max()}"
            )
            print("\nFirst few entries:")
            print(inventory_df.head())

            # Example: Find ticks where inventory changed
            print("\n=== Analysis Example ===")
            if len(inventory_df) > 1:
                inventory_changes = []
                for i in range(1, len(inventory_df)):
                    if inventory_df.iloc[i]["data"] != inventory_df.iloc[i - 1]["data"]:
                        inventory_changes.append(inventory_df.iloc[i]["tick"])

                print(
                    f"Inventory changed at ticks: {inventory_changes[:10]}..."
                )  # Show first 10

        else:
            print(
                "Could not load log files. Make sure they exist and pandas is installed."
            )

    except ImportError:
        print("pandas is required for log analysis")
        print("Install with: pip install pandas")
