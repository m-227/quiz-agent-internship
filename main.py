import os
from openai import OpenAI
from dotenv import load_dotenv

# Load the secret variables from the hidden .env file
load_dotenv()

# Initialize the client by grabbing the key securely from the environment variables
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY")
)

# Call the OpenAI API
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system", 
            "content": "You are an assistant that creates clear, educational quizzes. Always format your output cleanly."
        },
        {
            "role": "user", 
            "content": "Generate 3 Yes/No Questions on RAG (Retrieval-Augmented Generation). Do not use markdown bold formatting or asterisks in your response. Directly below each question, add the text 'Ans: Yes/No' as a blank space for the user to answer."
        }
    ]
)

# Extract and print only the text content of the response
print(response.choices[0].message.content)