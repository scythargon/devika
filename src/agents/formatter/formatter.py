from jinja2 import Environment, BaseLoader
from pathlib import Path

from src.llm import LLM

PROMPT = Path(__file__).parent.joinpath('prompt.jinja2').read_text().strip()

class Formatter:
    def __init__(self, base_model: str):
        self.llm = LLM(model_id=base_model)

    def render(self, raw_text: str) -> str:
        env = Environment(loader=BaseLoader())
        template = env.from_string(PROMPT)
        return template.render(raw_text=raw_text)
    
    def validate_response(self, response: str) -> bool:
        return True

    def execute(self, raw_text: str, project_name: str) -> str:
        raw_text = self.render(raw_text)
        response = self.llm.inference(raw_text, project_name)
        return response
