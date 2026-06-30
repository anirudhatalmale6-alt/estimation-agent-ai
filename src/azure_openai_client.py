"""
Azure OpenAI client wrapper for the estimation agent.
Handles authentication, model selection, and structured output parsing.
"""

import os
import json
from openai import AzureOpenAI


class AzureOpenAIClient:
    def __init__(self, endpoint=None, api_key=None, api_version=None,
                 deployment_name=None):
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        self.deployment = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version
        )

    def chat(self, system_prompt, user_prompt, temperature=0.2, max_tokens=4000):
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    def chat_json(self, system_prompt, user_prompt, temperature=0.1, max_tokens=4000):
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)

    def chat_with_history(self, messages, temperature=0.2, max_tokens=4000):
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
