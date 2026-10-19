import os
from dotenv import load_dotenv
import google.generativeai as genai

print("Starting...")

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Creating model...")

model = genai.GenerativeModel("models/gemini-3.8-flash")

print("Sending request...")

response = model.generate_content("Say hello")

print("Response received!")
print(response.text)