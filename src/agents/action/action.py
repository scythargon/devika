from pathlib import Path

from jinja2 import Environment, BaseLoader
from termcolor import colored

from src.config import Config
from src.llm import LLM
from src.utils import parse_xml_llm_response

PROMPT = Path(__file__).parent.joinpath('prompt.jinja2').read_text().strip()


class Action:
    def __init__(self, base_model: str):
        config = Config()
        self.project_dir = config.get_projects_dir()
        
        self.llm = LLM(model_id=base_model)

    def render(
        self, conversation: str
    ) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            conversation=conversation
        )

    def validate_response(self, response: str):
        response = parse_xml_llm_response(response)

        if "response" not in response and "action" not in response:
            return False
        else:
            return response["response"], response["action"]

    def execute(self, conversation: list, project_name: str) -> str:
        prompt = self.render(conversation)
        response = self.llm.inference(prompt, project_name)
        
        valid_response = self.validate_response(response)
        
        while not valid_response:
            print(colored(f"{self.__class__.__name__}: Invalid response from the model: {response}, trying again...", "red"))
            return self.execute(conversation, project_name)
        
        print("===" * 10)
        print(valid_response)

        return valid_response
