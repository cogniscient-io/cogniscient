import os
print("LLM_MODEL from os.environ:", os.environ.get("LLM_MODEL"))

from src.config.settings import settings
print("Settings llm_model:", settings.llm_model)
print("All settings:", settings.model_dump())