import os
import asyncio
from dotenv import load_dotenv
from fle.commons.db_client import DBClient
from eval.open.plots.run_results import RunResults
import questionary
import neptune

# Load environment variables
os.environ.update({"FORCE_COLOR": "1", "TERM": "xterm-256color"})
load_dotenv()


async def main():
    # Initialize database connection
    try:
        db_client = DBClient(
            max_conversation_length=40,
            host=os.getenv("SKILLS_DB_HOST"),
            port=os.getenv("SKILLS_DB_PORT"),
            dbname=os.getenv("SKILLS_DB_NAME"),
            user=os.getenv("SKILLS_DB_USER"),
            password=os.getenv("SKILLS_DB_PASSWORD"),
        )
    except Exception:
        print(
            "\033[91mError connecting to the database. Please check your credentials and try again.\033[91m"
        )
        return

    try:
        # Get largest version from DB for default suggestion
        largest_version = await db_client.get_largest_version()

        # Get version from user
        version = int(
            questionary.text(
                "Enter the version number to analyze:",
                default=str(largest_version),
                instruction="The run version number to generate plots for",
            ).ask()
        )

        # Create RunResults instance and save plots
        print(f"\nGenerating plots for version {version}...")

        # Initialize Neptune run
        NEPTUNE_PROJECT = os.getenv("NEPTUNE_PROJECT")
        NEPTUNE_API_TOKEN = os.getenv("NEPTUNE_API_TOKEN")
        if not NEPTUNE_PROJECT or not NEPTUNE_API_TOKEN:
            raise ValueError(
                "Neptune project and API token must be set in the environment variables."
            )
        neptune_run = neptune.init_run(
            project="jackhopkins/factorio-mcts",
            api_token="eyJhcGlfYWRkcmVzcyI6Imh0dHBzOi8vYXBwLm5lcHR1bmUuYWkiLCJhcGlfdXJsIjoiaHR0cHM6Ly9hcHAubmVwdHVuZS5haSIsImFwaV9rZXkiOiIwMWYyMmEyZC1iNzFmLTQzNzEtYTNkOC04YTcyMmM4Mzk4OWUifQ==",
        )  # your credentials
        # neptune_run = neptune.init_run(
        #     project=NEPTUNE_PROJECT,
        #     api_token=NEPTUNE_API_TOKEN,
        #     name=f"Version {version} Analysis",
        #     tags=["analysis"]
        # )

        # Create RunResults instance with Neptune run
        run = RunResults(version=version, db_client=db_client, neptune_run=neptune_run)
        run.save_plots()

        # Stop Neptune run
        neptune_run.stop()

        print(
            "\n\033[92mPlots have been generated and uploaded to Neptune successfully!\033[0m"
        )

    except ValueError as e:
        print(f"\033[91mError: Invalid version number. {str(e)}\033[0m")
    except Exception as e:
        print(f"\033[91mError generating plots: {str(e)}\033[0m")


if __name__ == "__main__":
    asyncio.run(main())
