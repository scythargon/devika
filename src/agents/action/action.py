import subprocess
from pathlib import Path

from jinja2 import Environment, BaseLoader
from termcolor import colored

from src.config import Config
from src.llm import LLM
from src.project import ProjectManager
from src.state import AgentState
from src.utils import parse_xml_llm_response, ensure_dir_exists

PROMPT = Path(__file__).parent.joinpath('prompt.jinja2').read_text().strip()

project_manager = ProjectManager()


class Action:
    REQUIRED_XML_TAGS = ["comment", "action", "next", "actionParams", "fileName"]

    def __init__(self, project_name: str, base_model: str):
        config = Config()
        self.project_name = project_name
        self.project_dir = config.get_projects_dir()
        self.project_path = project_manager.get_project_path(project_name)
        self.llm = LLM(model_id=base_model)

    def render(self) -> str:
        conversation = project_manager.get_all_messages_formatted(self.project_name)
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            conversation=conversation
        )

    def run_code(self, command: str):
        """
        Try to run the code from the LLM response.
        Add the command, its return code, output and stdout (if any) to the conversation via system messages.
        """
        ensure_dir_exists(self.project_path)
        project_manager.add_system_message(self.project_name, f"Executing Command: {command}\n")
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.project_path,
            shell=True
        )
        command_output = process.stdout.decode('utf-8')
        command_stderr = process.stderr.decode('utf-8')
        # command_succeeded = process.returncode == 0

        new_state = AgentState().new_state()
        new_state["internal_monologue"] = "Executing command..."
        new_state["terminal_session"]["title"] = "Terminal"
        new_state["terminal_session"]["command"] = command
        new_state["terminal_session"]["output"] = command_output
        if command_stderr:
            new_state["terminal_session"]["output"] += f"\n\nError:\n```\n{command_stderr}\n```"

        AgentState().add_to_current_state(self.project_name, new_state)
        conversation_message = f"Command output:\n```\n{command_output}\n```\n"
        if command_stderr:
            conversation_message += f"\n\nError:\n```\n{command_stderr}\n```"

        project_manager.add_system_message(self.project_name, conversation_message)

    def write_file(self, file_name: str, file_content: str):
        """
        Write the file to the project directory.
        """
        ensure_dir_exists(self.project_path)
        file_path = Path(self.project_path).joinpath(file_name)
        try:
            with open(file_path, 'w') as f:
                f.write(file_content)
        except Exception as e:
            project_manager.add_system_message(self.project_name, f"Error writing file {file_name}: {e}")
            return

        project_manager.add_system_message(
            self.project_name,
            f"File {file_name} written successfully.\nContent:\n```\n{file_content}\n```"
        )

    def validate_response(self, response: str):
        response = parse_xml_llm_response(response)

        for tag in self.REQUIRED_XML_TAGS:
            if tag not in response:
                print(colored(f"{self.__class__.__name__}: Missing tag in response: {tag}", "red"))
                return False

        if response["next"] not in ["proceed-to-next-step", "need-users-answer"]:
            print(colored(f"{self.__class__.__name__}: Invalid 'next' tag in response: {response['next']}", "red"))
            return False

        return response

    def execute(self) -> str:
        prompt = self.render()
        response = self.llm.inference(prompt, self.project_name)

        llm_response = self.validate_response(response)

        while not llm_response:
            print(colored(f"{self.__class__.__name__}: Invalid response from the model: \n{response}, trying again...",
                          "red"))
            ProjectManager().add_system_message(
                self.project_name, "Invalid response from the model, trying again..."
            )
            return self.execute()

        project_manager.add_message_from_devika(self.project_name, llm_response["comment"])

        # Execute the command if any.
        if llm_response["action"] == "execute":
            command = llm_response["actionParams"]
            self.run_code(command)
        elif llm_response["action"] == "write-file":
            file_name = llm_response["fileName"]
            file_content = llm_response["actionParams"]
            self.write_file(file_name, file_content)

        # Execute again if the model asks to continue.
        if llm_response["next"] == "proceed-to-next-step":
            return self.execute()

        AgentState().set_agent_completed(self.project_name, True)
        # return valid_response
