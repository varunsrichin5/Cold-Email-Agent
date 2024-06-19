import os
import time
import requests
from mailjet_rest import Client
from crewai import Agent, Task, Crew
from openai import OpenAI
import streamlit as st

# Configuration with hardcoded API keys
HUNTER_API_KEY = '65b86f2c653f44b9d9a8ff77fdee6adca08232dd'
MAILJET_API_KEY = 'cef0f9951409ba2ca60c6eaf8249fc6c'
MAILJET_API_SECRET = '0e7e14a8a82f84228a5a95125b4081ae'
OPENAI_API_KEY = 'sk-proj-YGXiwFfuCEZdXXOvjKUXT3BlbkFJW5n9guKW8qXpfmwjgP1o'
FROM_EMAIL = 'daniel@usemassive.com'
FROM_NAME = 'Daniel Vykhopen'
ORGANIZATION = 'Massive'
POSITION = 'CEO'
WEBSITE = 'https://usemassive.com'
PHONE_NUMBER = '7813543192'

os.environ["HUNTER_API_KEY"] = HUNTER_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# Initialize OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)
GPT_MODEL = "gpt-4o"

# Predefined list of trusted university domains
TRUSTED_UNIVERSITY_DOMAINS = [
    "harvard.edu",
    "stanford.edu",
    "mit.edu",
    "caltech.edu",
    "uchicago.edu",
    "princeton.edu",
    "columbia.edu",
    "yale.edu",
    "upenn.edu",
    "cornell.edu"
]

# Define the Marketing Manager Agent
class MarketingManagerAgent(Agent):
    def __init__(self):
        super().__init__(role='Marketing Manager', goal='Ensure the smooth running of the email outreach campaign', backstory='A seasoned marketing manager with a keen eye for detail and process efficiency.')

    def run(self, user_input):
        st.write("**Marketing Manager:** Greetings! I'm here to assist you with your email outreach campaign. Let's get started!")
        st.write("**Marketing Manager:** First, I'll generate the campaign details based on your input.")
        start_time = time.time()
        campaign_details = self.generate_campaign_details(user_input)
        self.print_elapsed_time(start_time)
        
        if not campaign_details:
            st.error("**Marketing Manager:** Oops! It seems there was an issue generating the campaign details. Please check your inputs and try again.")
            return
        
        st.success(f"**Marketing Manager:** Great news! The campaign details have been generated successfully. Here's a summary:\nDetails: {campaign_details}")

        st.write("**Marketing Manager:** Next, I'll coordinate with our Leads Hunter to find potential leads for the campaign.")
        start_time = time.time()
        leads_hunter_agent = LeadsHunterAgent()
        leads = leads_hunter_agent.run(campaign_details["domain"])
        self.print_elapsed_time(start_time)
        
        if not leads:
            st.warning("**Marketing Manager:** Unfortunately, no valid leads were found for the specified domain. Please check the domain and try again.")
            return
        
        st.info(f"**Marketing Manager:** Fantastic! Our Leads Hunter has found {len(leads)} potential leads.\nLeads: {leads}")

        st.write("**Marketing Manager:** Now, I'll work on validating each lead to ensure they are suitable for our campaign.")
        start_time = time.time()
        validated_leads = self.validate_leads(leads)
        self.print_elapsed_time(start_time)
        
        if not validated_leads:
            st.warning("**Marketing Manager:** It appears that none of the leads passed the validation process. Please review the leads and try again.")
            return

        st.success(f"**Marketing Manager:** Excellent! {len(validated_leads)} leads have been successfully validated.\nValidated Leads: {validated_leads}")

        selected_leads = validated_leads[:5]  # Select up to 5 leads for demonstration

        st.write("**Marketing Manager:** I'll now collaborate with our talented Copy Writer to craft personalized email content for each lead.")
        start_time = time.time()
        copy_writer_agent = CopyWriterAgent()
        for lead in selected_leads:
            email_content = copy_writer_agent.run(lead, campaign_details["campaign_description"])
            st.info(f"**Copy Writer:** I've generated engaging email content for {lead['value']}. Here's a preview:\nContent: {email_content}")
            self.send_email(lead['value'], campaign_details["email_subject"], email_content)
        self.print_elapsed_time(start_time)

        st.balloons()
        st.success("**Marketing Manager:** Congratulations! The email campaign has been completed successfully. Thank you for your collaboration!")

    def generate_campaign_details(self, user_input):
        prompt = f"""
        Based on the following input, generate a domain, campaign description, and email subject for an email outreach campaign:
        '{user_input}'

        When generating the campaign details, consider the following:
        - The domain should be selected from the provided trusted list.
        - The campaign description should clearly explain the value proposition and the desired outcome of the campaign.
        - The email subject should be engaging, concise, and entice the recipient to open the email.

        Trusted domains: {', '.join(TRUSTED_UNIVERSITY_DOMAINS)}

        Please provide the domain, campaign description, and email subject in the following format:
        Domain: <domain>
        Campaign Description: <description>
        Email Subject: <subject>
        """

        messages = [
            {"role": "system", "content": "You answer questions about Web services."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=0
            )
            response_message = response.choices[0].message.content.strip().split('\n')

            # Filter out empty lines
            response_message = [line for line in response_message if line.strip()]

            if len(response_message) < 3:
                raise ValueError("Incomplete campaign details generated by the model.")

            domain = response_message[0].split(':')[1].strip()

            if domain not in TRUSTED_UNIVERSITY_DOMAINS:
                raise ValueError("Domain generated is not from the trusted list.")

            return {
                "domain": domain,
                "campaign_description": response_message[1].split(':')[1].strip(),
                "email_subject": response_message[2].split(':')[1].strip()
            }
        except Exception as e:
            st.error(f"Error generating campaign details: {str(e)}")
            return None

    def validate_leads(self, leads):
        st.write("**Marketing Manager:** I'm validating each lead to ensure their quality and suitability for our campaign.")
        valid_leads = []
        for lead in leads:
            email = lead['value']
            st.write(f"Validating {email}...")
            url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={HUNTER_API_KEY}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                validation = response.json().get('data', {}).get('status')
                if validation == 'valid':
                    valid_leads.append(lead)
                    st.success(f"Validation successful: {email}")
                else:
                    st.warning(f"Validation failed: {email} - {validation}")
            except requests.exceptions.RequestException as e:
                st.error(f"Error validating email {email}: {str(e)}")
        return valid_leads

    def send_email(self, to_email, subject, content):
        st.write(f"**Marketing Manager:** I'm sending a personalized email to {to_email}.")
        
        # Initialize Mailjet client
        mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3.1')

        # Email data
        data = {
            'Messages': [
                {
                    "From": {
                        "Email": FROM_EMAIL,
                        "Name": FROM_NAME
                    },
                    "To": [
                        {
                            "Email": to_email,
                            "Name": "Recipient"
                        }
                    ],
                    "Subject": subject,
                    "TextPart": content,
                    "HTMLPart": f"""
                    <p>{content}</p>
                    <p>Best regards,</p>
                    <p>{FROM_NAME}<br>
                    {POSITION}, {ORGANIZATION}<br>
                    {WEBSITE}<br>
                    Phone: {PHONE_NUMBER}</p>
                    """,
                    "CustomID": "AppGettingStartedTest"
                }
            ]
        }

        try:
            # Send email
            result = mailjet.send.create(data=data)
            st.success(f"Email sent successfully to {to_email}. Status code: {result.status_code}")
            st.json(result.json())
        except Exception as e:
            st.error(f"Error sending email to {to_email}: {str(e)}")

    def print_elapsed_time(self, start_time):
        elapsed_time = time.time() - start_time
        st.info(f"Time taken: {elapsed_time:.2f} seconds")

# Define the Leads Hunter Agent
class LeadsHunterAgent(Agent):
    def __init__(self):
        super().__init__(role='Leads Hunter', goal='Find potential leads based on the given domain', backstory='A skilled agent adept at uncovering valuable leads.')

    def run(self, domain):
        st.write(f"**Leads Hunter:** I'm on the hunt for leads in the domain {domain}. I'll use my advanced searching techniques to find the most promising contacts.")
        url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}&limit=5"
        try:
            response = requests.get(url)
            response.raise_for_status()
            leads = response.json().get('data', {}).get('emails', [])
            st.success(f"**Leads Hunter:** I've successfully identified potential leads in the {domain} domain. I'll pass them along to the Marketing Manager for validation.")
            return leads
        except requests.exceptions.RequestException as e:
            st.error(f"**Leads Hunter:** Oops! I encountered an error while searching for leads: {str(e)}. I'll inform the Marketing Manager.")
            return None

# Define the Copy Writer Agent
class CopyWriterAgent(Agent):
    def __init__(self):
        super().__init__(role='Copy Writer', goal='Generate personalized email content', backstory='A creative agent with a flair for writing engaging and personalized email content.')

    def run(self, lead, campaign_description):
        st.write(f"**Copy Writer:** I'm excited to craft a compelling email for {lead['value']}. I'll showcase my creative writing skills to engage the recipient.")
        prompt = f"""
        Generate a personalized email for the following campaign:
        Campaign Description: {campaign_description}

        The email should be addressed to {lead['first_name']} {lead['last_name']}.

        When generating the email content, consider the following:
        - Highlight the key benefits and value proposition of the campaign.
        - Personalize the email based on the recipient's information and role.
        - Use a friendly and professional tone to establish a connection with the recipient.
        - Include a clear call-to-action to encourage the recipient to take the desired action.
        - The email is sent by Daniel Vykhopen, the CEO of Massive (https://usemassive.com).

        Please provide the email content below:
        """

        messages = [
            {"role": "system", "content": "You answer questions about Web services."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=messages,
                temperature=0
            )
            email_content = response.choices[0].message.content.strip()
            st.success(f"**Copy Writer:** I've crafted a personalized email for {lead['value']} that effectively communicates the value of our campaign. I'll send it to the Marketing Manager for review.")
            return email_content
        except Exception as e:
            st.error(f"**Copy Writer:** Oh no! I encountered an error while generating the email content: {str(e)}. I'll notify the Marketing Manager.")
            return ""

# Main Workflow
def main_workflow():
    st.title("Automated Email Outreach Campaign")
    st.write("Welcome to the automated email outreach campaign demo!")
    st.write("The Marketing Manager will guide you through each step of the process.")

    user_input = st.text_input("Please describe your campaign needs:")

    if st.button("Start Campaign"):
        marketing_manager_agent = MarketingManagerAgent()
        marketing_manager_agent.run(user_input)

if __name__ == "__main__":
    main_workflow()