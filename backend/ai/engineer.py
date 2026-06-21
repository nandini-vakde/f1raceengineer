from ai.prompt_builder import build_prompt
from ai.llm_client import generate


class RaceEngineer:

    def process(self, telemetry_point):

        prompt = build_prompt(telemetry_point)

        return generate(prompt)