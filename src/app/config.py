# src/app/config.py

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")


def get_llm_client():


    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))