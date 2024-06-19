import os
import time
import requests
import sendgrid
from sendgrid.helpers.mail import Mail
from crewai import Agent, Task, Crew
from openai import OpenAI

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
        print("\nMarketing Manager: Preparing to generate campaign details...\n")
        start_time = time.time()
        campaign_details = self.generate_campaign_details(user_input)
        self.print_elapsed_time(start_time)
        
        if not campaign_details:
            print("Marketing Manager: Campaign failed. Please check the inputs and try again.")
            return
        
        print(f"Marketing Manager: Campaign details generated successfully!\nDetails: {campaign_details}\n")

        print("Marketing Manager: Initiating the search for leads...\n")
        start_time = time.time()
        leads_hunter_agent = LeadsHunterAgent()
        leads = leads_hunter_agent.run(campaign_details["domain"])
        self.print_elapsed_time(start_time)
        
        if not leads:
            print("Marketing Manager: No valid leads found. Please check the domain and try again.")
            return
        
        print(f"Marketing Manager: Found {len(leads)} leads.\nLeads: {leads}\n")

        print("Marketing Manager: Starting lead validation process...\n")
        start_time = time.time()
        validated_leads = self.validate_leads(leads)
        self.print_elapsed_time(start_time)
        
        if not validated_leads:
            print("Marketing Manager: No valid leads after validation. Please check the leads and try again.")
            return

        print(f"Marketing Manager: Successfully validated {len(validated_leads)} leads.\nValidated Leads: {validated_leads}\n")

        selected_leads = validated_leads[:5]  # Select up to 5 leads for demonstration

        print("Marketing Manager: Coordinating with the Copy Writer to generate email content...\n")
        start_time = time.time()
        copy_writer_agent = CopyWriterAgent()
        for lead in selected_leads:
            email_content = copy_writer_agent.run(lead, campaign_details["campaign_description"])
            print(f"Copy Writer: Email content generated for {lead['value']}.\nContent: {email_content}\n")
            self.send_email(lead['value'], campaign_details["email_subject"], email_content)
        self.print_elapsed_time(start_time)

        print("Marketing Manager: Email campaign completed successfully!\n")

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
            print(f"Error generating campaign details: {str(e)}")
            return None

    def validate_leads(self, leads):
        print("Marketing Manager: Validating each lead...\n")
        valid_leads = []
        for lead in leads:
            email = lead['value']
            print(f"Validating {email}...")
            url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={HUNTER_API_KEY}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                validation = response.json().get('data', {}).get('status')
                if validation == 'valid':
                    valid_leads.append(lead)
                    print(f"Validation successful: {email}\n")
                else:
                    print(f"Validation failed: {email} - {validation}\n")
            except requests.exceptions.RequestException as e:
                print(f"Error validating email {email}: {str(e)}\n")
        return valid_leads

    def send_email(self, to_email, subject, content):
        print(f"Marketing Manager: Sending email to {to_email}...\n")
        sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
        email = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            plain_text_content=content)
        try:
            response = sg.send(email)
            if response.status_code == 202:
                print(f"Email sent successfully to {to_email}.\n")
            else:
                print(f"Error sending email to {to_email}: {response.status_code} - {response.text}\n")
        except Exception as e:
            print(f"Error sending email to {to_email}: {str(e)}\n")

    def print_elapsed_time(self, start_time):
        elapsed_time = time.time() - start_time
        print(f"Time taken: {elapsed_time:.2f} seconds\n")

# Define the Leads Hunter Agent
class LeadsHunterAgent(Agent):
    def __init__(self):
        super().__init__(role='Leads Hunter', goal='Find potential leads based on the given domain', backstory='A skilled agent adept at uncovering valuable leads.')

    def run(self, domain):
        print(f"Leads Hunter: Initiating search for leads in the domain {domain}...\n")
        url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}&limit=5"
        try:
            response = requests.get(url)
            response.raise_for_status()
            leads = response.json().get('data', {}).get('emails', [])
            print(f"Leads Hunter: Successfully found leads in {domain}.\n")
            return leads
        except requests.exceptions.RequestException as e:
            print(f"Leads Hunter: Error in API call: {str(e)}\n")
            return None

# Define the Copy Writer Agent
class CopyWriterAgent(Agent):
    def __init__(self):
        super().__init__(role='Copy Writer', goal='Generate personalized email content', backstory='A creative agent with a flair for writing engaging and personalized email content.')

    def run(self, lead, campaign_description):
        print(f"Copy Writer: Generating email content for {lead['value']}...\n")
        prompt = f"""
        Generate a personalized email for the following campaign:
        Campaign Description: {campaign_description}

        The email should be addressed to {lead['first_name']} {lead['last_name']}.

        When generating the email content, consider the following:
        - Highlight the key benefits and value proposition of the campaign.
        - Personalize the email based on the recipient's information and role.
        - Use a friendly and professional tone to establish a connection with the recipient.
        - Include a clear call-to-action to encourage the recipient to take the desired action.

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
            print(f"Copy Writer: Successfully generated email content for {lead['value']}.\n")
            return email_content
        except Exception as e:
            print(f"Copy Writer: Error generating email content: {str(e)}\n")
            return ""

# Main Workflow
def main_workflow():
    print("Welcome to the automated email outreach campaign demo!\n")
    time.sleep(1)
    print("The Marketing Manager will guide you through each step of the process...\n")
    time.sleep(1)

    print("Describe your campaign needs: ")
    user_input = input()

    marketing_manager_agent = MarketingManagerAgent()
    marketing_manager_agent.run(user_input)

if __name__ == "__main__":
    main_workflow()