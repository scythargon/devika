import time
import json
from pathlib import Path
import os
import subprocess

from termcolor import colored

from src.config import Config

from jinja2 import Environment, BaseLoader

from src.agents.patcher import Patcher

from src.llm import LLM
from src.state import AgentState
from src.project import ProjectManager
from src.utils import take_json_text_from_triple_quotes, parse_xml_llm_response_commands, parse_xml_llm_response

PROMPT = Path(__file__).parent.joinpath('prompt.jinja2').read_text().strip()
RERUNNER_PROMPT = Path(__file__).parent.joinpath('rerunner.jinja2').read_text().strip()


class Executor:
    def __init__(self, base_model: str):
        self.base_model = base_model
        self.llm = LLM(model_id=base_model)
        config = Config()
        self.projects_dir = config.get_projects_dir()

    def render(
        self,
        conversation: str,
        code_markdown: str,
        system_os: str
    ) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            conversation=conversation,
            code_markdown=code_markdown,
            system_os=system_os,
        )

    def render_rerunner(
        self,
        conversation: str,
        code_markdown: str,
        system_os: str,
        commands: list,
        error: str
    ):
        env = Environment(loader=BaseLoader())
        template = env.from_string(RERUNNER_PROMPT)
        return template.render(
            conversation=conversation,
            code_markdown=code_markdown,
            system_os=system_os,
            commands=commands,
            error=error
        )

    def validate_response(self, response: str):
        response = parse_xml_llm_response_commands(response)
        if "commands" not in response:
            return False
        else:
            return response["commands"]
        
    def validate_rerunner_response(self, response: str):
        response = parse_xml_llm_response(response)

        if "action" not in response and "response" not in response:
            return False
        else:
            return response

    def get_project_path(self, project_name: str):
        project_name = project_name.lower().replace(" ", "-")
        return f"{self.projects_dir}/{project_name}"

    def ensure_project_dir(self, project_name):
        path = self.get_project_path(project_name)
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

    def run_code(
        self,
        commands: list,
        project_path: str,
        project_name: str,
        conversation: list,
        code_markdown: str,
        system_os: str
    ):
        self.ensure_project_dir(project_name)
        retries = 0

        for command in commands:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=project_path,
                shell=True
            )
            command_output = process.stdout.decode('utf-8')
            command_stderr = process.stderr.decode('utf-8')
            command_failed = process.returncode != 0
            
            new_state = AgentState().new_state()
            new_state["internal_monologue"] = "Executing command..."
            new_state["terminal_session"]["title"] = "Terminal"
            new_state["terminal_session"]["command"] = command
            new_state["terminal_session"]["output"] = command_output
            if command_stderr:
                new_state["terminal_session"]["output"] += f"\n\nError:\n```\n{command_stderr}\n```"

            AgentState().add_to_current_state(project_name, new_state)
            conversation_message = f"Command output:\n```\n{command_output}\n```\n"
            if command_stderr:
                conversation_message += f"\n\nError:\n```\n{command_stderr}\n```"

            ProjectManager().add_message_from_devika(
                project_name, conversation_message
            )
            time.sleep(1)
            
            while command_failed and retries < 2:
                new_state = AgentState().new_state()
                new_state["internal_monologue"] = "Oh seems like there is some error... :("
                new_state["terminal_session"]["title"] = "Terminal"
                new_state["terminal_session"]["command"] = command
                new_state["terminal_session"]["output"] = command_output
                AgentState().add_to_current_state(project_name, new_state)
                ProjectManager().add_message_from_devika(
                    project_name, f"Command output:\n```\n{command_output}\n```\n"
                )

                time.sleep(1)
                
                prompt = self.render_rerunner(
                    conversation=conversation,
                    code_markdown=code_markdown,
                    system_os=system_os,
                    commands=commands,
                    error=command_output
                )
                
                response = self.llm.inference(prompt, project_name)
                
                valid_response = self.validate_rerunner_response(response)
                
                while not valid_response and not AgentState().is_agent_interruped(project_name):
                    print(colored(f"{self.__class__.__name__}: Invalid response from the model: {response}, trying again...", "red"))
                    return self.run_code(
                        commands,
                        project_path,
                        project_name,
                        conversation,
                        code_markdown,
                        system_os
                    )
                if AgentState().is_agent_interruped(project_name):
                    print(colored(f"{self.__class__.__name__}: Agent is interrupted", "yellow"))
                    break
                
                action = valid_response["action"]
                
                if action == "command":
                    command = valid_response["command"]
                    response = valid_response["response"]
                    
                    ProjectManager().add_message_from_devika(project_name, response)
                    
                    process = subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=project_path,
                        shell=True,
                    )
                    command_output = process.stdout.decode('utf-8')
                    command_failed = process.returncode != 0
                    
                    new_state = AgentState().new_state()
                    new_state["internal_monologue"] = "Executing command..."
                    new_state["terminal_session"]["title"] = "Terminal"
                    new_state["terminal_session"]["command"] = command
                    new_state["terminal_session"]["output"] = command_output
                    AgentState().add_to_current_state(project_name, new_state)
                    time.sleep(1)
                    
                    if command_failed:
                        retries += 1
                    else:
                        break
                elif action == "patch":
                    response = valid_response["response"]
                    
                    ProjectManager().add_message_from_devika(project_name, response)
                    
                    code = Patcher(base_model=self.base_model).execute(
                        conversation=conversation,
                        code_markdown=code_markdown,
                        commands=commands,
                        error=command_output,
                        system_os=system_os,
                        project_name=project_name
                    )
                    
                    Patcher(base_model=self.base_model).save_code_to_project(code, project_name)
                    
                    command_set = command.split(" ")
                    command_failed = False
                    
                    process = subprocess.run(
                        command_set,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=project_path
                    )
                    command_output = process.stdout.decode('utf-8')
                    command_failed = process.returncode != 0
                    
                    new_state = AgentState().new_state()
                    new_state["internal_monologue"] = "Executing command..."
                    new_state["terminal_session"]["title"] = "Terminal"
                    new_state["terminal_session"]["command"] = command
                    new_state["terminal_session"]["output"] = command_output
                    AgentState().add_to_current_state(project_name, new_state)
                    time.sleep(1)
                    
                    if command_failed:
                        retries += 1
                    else:
                        break

    def execute(
        self,
        conversation: list,
        code_markdown: str,
        os_system: str,
        project_path: str,
        project_name: str
    ) -> str:
        print(f"{self.__class__.__name__}: Executing...")
        prompt = self.render(conversation, code_markdown, os_system)
        response = self.llm.inference(prompt, project_name)
        
        valid_response = self.validate_response(response)
        
        while not valid_response and not AgentState().is_agent_interruped(project_name):
            print(colored(f"{self.__class__.__name__}: Invalid response from the model: {response}, trying again...", "red"))
            return self.execute(conversation, code_markdown, os_system, project_path, project_name)
        if AgentState().is_agent_interruped(project_name):
            print(colored(f"{self.__class__.__name__}: Agent is interrupted", "yellow"))
            return None
        
        print("=====" * 10)
        print(valid_response)
        
        self.run_code(
            valid_response,
            project_path,
            project_name,
            conversation,
            code_markdown,
            os_system
        )

        return valid_response
