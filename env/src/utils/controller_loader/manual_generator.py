import os


class ManualGenerator:
    """Generates manual from agent.md files in a directory."""

    @staticmethod
    def generate_agent_manual(folder_path) -> str:
        """Generate schema from all Python files in the folder."""
        agent_tool_path = os.path.join(folder_path, "agent")
        manual = "Here is the manual for the tools available to you\n\n"
        # get all the folders in tool_paths
        manual = ManualGenerator.get_tool_descriptions(agent_tool_path, manual)
        # read in the agent.md in master_tool_path
        with open(os.path.join(folder_path, "agent.md"), "r") as f:
            manual += f"## General tips\n"
            manual += f.read()
        return manual
    
    @staticmethod
    def get_tool_descriptions(folder_path, manual):
        # get all the folders in tool_paths
        tool_folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
        for folder in tool_folders:
            # check if it has a agent.md file
            agent_path = os.path.join(folder_path, folder, "agent.md")
            if os.path.exists(agent_path):
                with open(agent_path, "r") as f:
                    manual += f.read()
                    manual += "\n\n"
            else:
                continue
        return manual


    @staticmethod
    def generate_rag_manual(folder_path):
        """Generate schema from all Python files in the folder."""
        agent_tool_path = os.path.join(folder_path, "rag")
        manual = "Here are information gathering tools available to you\n\n"
        # get all the folders in tool_paths
        manual = ManualGenerator.get_tool_descriptions(agent_tool_path, manual)
        # read in the agent.md in master_tool_path
        return manual
