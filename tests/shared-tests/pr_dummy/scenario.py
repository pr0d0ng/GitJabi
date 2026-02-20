PR_SCENARIO_PROMPT = """
You are generating dummy GitHub Pull Request test scenarios.

* This PR is in {status} status.
* Context Language: Korean

Generate a JSON object with:
- title
- body (length: 500 ~ 1000 char)
- repo_name
- action (opened, closed)
- is_merged (true/false)
- language (Python/JavaScript/React/Go/Cpp/Java)
- risk_level (low, medium, high)
- contains_sensitive_data (true/false)
- contains_security_issue (true/false)
- change_type (bugfix, feature, refactor, docs, hotfix)
- additions (int)
- deletions (int)
- changed_files (int)

Make the scenario realistic.
If contains_sensitive_data=true, include:
- phone number
- email
- api key format

If contains_security_issue=true, include:
- hardcoded secret
- insecure code example

Also generate a realistic git diff patch.
- diff

Return JSON only. removes backtick ```.
"""

import openai
import os, json
import random
import uuid
from datetime import datetime, timezone

# client = openai.OpenAI()

from openai import AsyncAzureOpenAI

client = AsyncAzureOpenAI(
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
)

DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]


async def generate_pr_scenario():
    random_status = random.choice(
        ["Closed, Merged", "Opened, Not Merged", "Closed, Not Merged", "Opened, Not Merged"]
    )

    response = await client.chat.completions.create(
        model=DEPLOYMENT,
        temperature=0.9,
        messages=[
            {"role": "system", "content": "You generate test PR scenarios."},
            {"role": "user", "content": PR_SCENARIO_PROMPT.format(status=random_status)},
        ],
    )

    return json.loads(response.choices[0].message.content)

# def generate_pr_scenario():
#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         temperature=0.9,
#         messages=[
#             {"role": "system", "content": "You generate test PR scenarios."},
#             {"role": "user", "content": PR_SCENARIO_PROMPT},
#         ],
#     )

#     content = response.choices[0].message.content
#     return json.loads(content)


