import os
import requests
import sendgrid
from sendgrid.helpers.mail import Mail
from openai import OpenAI
import streamlit as st

# Configuration with hardcoded API keys
HUNTER_API_KEY = '65b86f2c653f44b9d9a8ff77fdee6adca08232dd'
SENDGRID_API_KEY = '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'
OPENAI_API_KEY = 'sk-proj-YGXiwFfuCEZdXXOvjKUXT3BlbkFJW5n9guKW8qXpfmwjgP1o'
FROM_EMAIL = 'dan@usemassive.com'

os.environ["HUNTER_API_KEY"] = HUNTER_API_KEY
os.environ["SENDGRID_API_KEY"] = SENDGRID_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Initialize OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)
GPT_MODEL = "gpt-4"

# Streamlit Interface
def run_app():
    st.title("API Testing")

    if st.button("Test APIs"):
        test_hunter_api()
        test_openai_api()
        test_sendgrid_api()

# Test Hunter API
def test_hunter_api():
    st.write("Testing Hunter API...")
    domain = "example.com"
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}&limit=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if 'data' in data and 'emails' in data['data']:
            st.write("Hunter API is working correctly.")
        else:
            st.error("Unexpected response from Hunter API.")
    except requests.exceptions.RequestException as e:
        st.error(f"Error in Hunter API call: {str(e)}")

# Test OpenAI API
def test_openai_api():
    st.write("Testing OpenAI API...")
    user_message = "What are web services?"
    messages = [
        {"role": "system", "content": 'You answer questions about web services.'},
        {"role": "user", "content": user_message},
    ]
    try:
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            temperature=0
        )
        response_message = response.choices[0].message.content
        if response_message:
            st.write("OpenAI API is working correctly.")
            st.write(f"Response: {response_message}")
        else:
            st.error("Unexpected response from OpenAI API.")
    except Exception as e:
        st.error(f"Error in OpenAI API call: {str(e)}")

# Test SendGrid API
def test_sendgrid_api():
    st.write("Testing SendGrid API...")
    to_email = "test@example.com"
    subject = "Test Email"
    content = "This is a test email."
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    email = Mail(
        from_email=FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        plain_text_content=content)
    try:
        response = sg.send(email)
        if response.status_code == 202:
            st.write("SendGrid API is working correctly.")
        else:
            st.error(f"Unexpected response from SendGrid API: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Error in SendGrid API call: {str(e)}")

if __name__ == "__main__":
    run_app()