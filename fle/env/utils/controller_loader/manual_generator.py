import os


class ManualGenerator:
    """Generates manual from agent.md files in a directory."""

    @staticmethod
    def generate_manual(folder_path) -> str:
        """Generate schema from all Python files in the folder."""
        if "agent/" not in folder_path:
            agent_tool_path = os.path.join(folder_path, "agent")
        else:
            agent_tool_path = folder_path

        # get all the folders in tool_paths
        tool_folders = [
            f
            for f in os.listdir(agent_tool_path)
            if os.path.isdir(os.path.join(agent_tool_path, f))
        ]
        manual = ""
        for folder in tool_folders:
            # check if it has a agent.md file
            agent_path = os.path.join(agent_tool_path, folder, "agent.md")
            if os.path.exists(agent_path):
                with open(agent_path, "r") as f:
                    manual += f.read()
                    manual += "\n\n"
            else:
                continue
        # read in the agent.md in master_tool_path
        with open(os.path.join(folder_path, "agent.md"), "r") as f:
            manual += "## General useful patterns\n"
            manual += f.read()
        return manual
