from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# https://developers.openai.com/api/docs/guides/tools-computer-use

client = OpenAI()

response = client.responses.create(
    model="gpt-5.4",
    tools=[{"type": "computer"}],
    input="Check whether the Filters panel is open. If it is not open, click Show filters. Then type penguin in the search box. Use the computer tool for UI interaction.",
)

print(response.output)
