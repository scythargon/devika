import json
from pathlib import Path

from jinja2 import Environment, BaseLoader

from src.config import Config
from src.llm import LLM
from src.utils import take_json_text_from_triple_quotes, parse_llm_response_to_json, parse_xml_llm_response

PROMPT = Path(__file__).parent.joinpath('prompt.jinja2').read_text().strip()


class Answer:
    def __init__(self, base_model: str):
        config = Config()
        self.project_dir = config.get_projects_dir()
        
        self.llm = LLM(model_id=base_model)

    def render(
        self, conversation: str, code_markdown: str
    ) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(
            conversation=conversation,
            code_markdown=code_markdown
        )

    def validate_response(self, response: str):
        response = parse_xml_llm_response(response)

        if "response" not in response:
            return False
        else:
            return response["response"]

    def execute(self, conversation: list, code_markdown: str, project_name: str) -> str:
        print(f"{self.__class__.__name__}: Executing...")
        prompt = self.render(conversation, code_markdown)
        response = self.llm.inference(prompt, project_name)
        
        valid_response = self.validate_response(response)
        
        while not valid_response:
            print(f"Answer: Invalid response from the model: {response}, trying again...")
            return self.execute(conversation, code_markdown, project_name)

        return valid_response
