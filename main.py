import os
import time
import requests
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from langchain.callbacks import LangChainTracer, ConsoleCallbackHandler
from langchain.smith import RunEvalConfig, run_on_dataset
from langchain.chat_models import ChatOpenAI
from mailjet_rest import Client
import streamlit as st

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
HUNTER_API_KEY = os.getenv('HUNTER_API_KEY')
MAILJET_API_KEY = os.getenv('MAILJET_API_KEY')
MAILJET_API_SECRET = os.getenv('MAILJET_API_SECRET')
LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY')
LANGCHAIN_PROJECT = os.getenv('LANGCHAIN_PROJECT', "Cold Email Agent")
FROM_EMAIL = os.getenv('FROM_EMAIL')
FROM_NAME = os.getenv('FROM_NAME')
ORGANIZATION = os.getenv('ORGANIZATION')
POSITION = os.getenv('POSITION')
WEBSITE = os.getenv('WEBSITE')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# LangSmith setup for monitoring
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT

# Initialize LangChain tracer and OpenAI chat model
tracer = LangChainTracer(project_name=LANGCHAIN_PROJECT)
console_handler = ConsoleCallbackHandler()
llm = ChatOpenAI(temperature=0.7, model_name="gpt-4")

# Initialize Mailjet client
mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version='v3.1')

# Predefined list of trusted university domains
TRUSTED_UNIVERSITY_DOMAINS = [
    "harvard.edu", "stanford.edu", "mit.edu", "caltech.edu", "uchicago.edu",
    "princeton.edu", "columbia.edu", "yale.edu", "upenn.edu", "cornell.edu"
]

# Define the Marketing Manager Agent
class MarketingManagerAgent(Agent):
    def __init__(self):
        super().__init__(
            role='Marketing Manager',
            goal='Ensure the smooth running of the email outreach campaign',
            backstory='A seasoned marketing manager with a keen eye for detail and process efficiency.',
            verbose=True
        )

    def run(self, user_input):
        campaign_details = self.generate_campaign_details(user_input)
        if not campaign_details:
            return "Error: Failed to generate campaign details."
        return f"Campaign strategy prepared: {campaign_details}"

    def generate_campaign_details(self, user_input):
        prompt = f"""
        Based on the following input, generate a domain, campaign description, and email subject for an email outreach campaign:
        '{user_input}'

        Consider the following:
        - The domain should be selected from the provided trusted list.
        - The campaign description should clearly explain the value proposition and the desired outcome of the campaign.
        - The email subject should be engaging, concise, and entice the recipient to open the email.

        Trusted domains: {', '.join(TRUSTED_UNIVERSITY_DOMAINS)}

        Provide the domain, campaign description, and email subject in the following format:
        Domain: <domain>
        Campaign Description: <description>
        Email Subject: <subject>
        """

        response = llm.predict(prompt)
        try:
            lines = response.strip().split('\n')
            domain = lines[0].split(':')[1].strip()
            campaign_description = lines[1].split(':')[1].strip()
            email_subject = lines[2].split(':')[1].strip()

            if domain not in TRUSTED_UNIVERSITY_DOMAINS:
                raise ValueError("Domain generated is not from the trusted list.")

            return {
                "domain": domain,
                "campaign_description": campaign_description,
                "email_subject": email_subject
            }
        except Exception as e:
            print(f"Error generating campaign details: {str(e)}")
            return None

# Define the Leads Hunter Agent
class LeadsHunterAgent(Agent):
    def __init__(self):
        super().__init__(
            role='Leads Hunter',
            goal='Find potential leads based on the given domain',
            backstory='A skilled agent adept at uncovering valuable leads.',
            verbose=True
        )

    def run(self, domain):
        leads = self.find_leads(domain)
        if not leads:
            return "Error: No leads found."
        return self.validate_leads(leads)

    def find_leads(self, domain):
        url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}&limit=5"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json().get('data', {}).get('emails', [])
        except requests.exceptions.RequestException as e:
            print(f"Error finding leads: {str(e)}")
            return None

    def validate_leads(self, leads):
        valid_leads = []
        for lead in leads:
            email = lead['value']
            url = f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={HUNTER_API_KEY}"
            try:
                response = requests.get(url)
                response.raise_for_status()
                validation = response.json().get('data', {}).get('status')
                if validation == 'valid':
                    valid_leads.append(lead)
            except requests.exceptions.RequestException as e:
                print(f"Error validating email {email}: {str(e)}")
        return valid_leads

# Define the Copy Writer Agent
class CopyWriterAgent(Agent):
    def __init__(self):
        super().__init__(
            role='Copy Writer',
            goal='Generate personalized email content',
            backstory='A creative agent with a flair for writing engaging and personalized email content.',
            verbose=True
        )

    def run(self, lead, campaign_description):
        return self.generate_email_content(lead, campaign_description)

    def generate_email_content(self, lead, campaign_description):
        prompt = f"""
        Generate a personalized email for the following campaign:
        Campaign Description: {campaign_description}

        The email should be addressed to {lead['first_name']} {lead['last_name']}.

        Consider the following:
        - Highlight the key benefits and value proposition of the campaign.
        - Personalize the email based on the recipient's information and role.
        - Use a friendly and professional tone to establish a connection with the recipient.
        - Include a clear call-to-action to encourage the recipient to take the desired action.
        - The email is sent by {FROM_NAME}, the {POSITION} of {ORGANIZATION} ({WEBSITE}).

        Please provide the email content below:
        """

        response = llm.predict(prompt)
        return response.strip()

# Define the Outreach Coordinator Agent
class OutreachCoordinatorAgent(Agent):
    def __init__(self):
        super().__init__(
            role='Outreach Coordinator',
            goal='Manage the email campaign and ensure smooth execution',
            backstory='An experienced campaign manager overseeing the entire outreach process',
            verbose=True
        )

    def run(self, leads, email_contents, subject):
        return self.send_emails(leads, email_contents, subject)

    def send_emails(self, leads, email_contents, subject):
        results = []
        for lead, content in zip(leads, email_contents):
            result = self.send_email(lead['value'], subject, content)
            results.append(result)
        return results

    def send_email(self, to_email, subject, content):
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
                    "HTMLPart": f"<p>{content}</p><p>Best regards,</p><p>{FROM_NAME}<br>{POSITION}, {ORGANIZATION}<br>{WEBSITE}<br>Phone: {PHONE_NUMBER}</p>",
                    "CustomID": "ColdEmailCampaign"
                }
            ]
        }

        try:
            result = mailjet.send.create(data=data)
            return f"Email sent to {to_email}. Status: {result.status_code}"
        except Exception as e:
            return f"Error sending email to {to_email}: {str(e)}"

# Define tasks
def prepare_campaign_task(campaign_brief):
    return Task(
        description=f"Prepare campaign strategy based on: {campaign_brief}",
        agent=MarketingManagerAgent()
    )

def find_leads_task(campaign_details):
    return Task(
        description=f"Find potential leads for the domain: {campaign_details['domain']}",
        agent=LeadsHunterAgent()
    )

def create_email_content_task(leads, campaign_description):
    return Task(
        description=f"Create personalized email content for {len(leads)} leads",
        agent=CopyWriterAgent()
    )

def execute_campaign_task(leads, email_contents, subject):
    return Task(
        description=f"Execute the email campaign for {len(leads)} leads",
        agent=OutreachCoordinatorAgent()
    )

# Main workflow
def run_cold_email_campaign(campaign_brief):
    crew = Crew(
        agents=[MarketingManagerAgent(), LeadsHunterAgent(), CopyWriterAgent(), OutreachCoordinatorAgent()],
        tasks=[
            prepare_campaign_task(campaign_brief),
            find_leads_task("{{prepare_campaign_task.output}}"),
            create_email_content_task("{{find_leads_task.output}}", "{{prepare_campaign_task.output.campaign_description}}"),
            execute_campaign_task("{{find_leads_task.output}}", "{{create_email_content_task.output}}", "{{prepare_campaign_task.output.email_subject}}")
        ],
        verbose=2
    )

    result = crew.kickoff()
    return result

# LangSmith evaluation function
def evaluate_campaign(campaign_brief):
    eval_config = RunEvalConfig(
        evaluators=[
            "criteria",
            "embedding_distance",
        ],
        custom_evaluators=[],
    )

    dataset = [{"input": campaign_brief}]

    results = run_on_dataset(
        client=None,
        dataset=dataset,
        llm_or_chain_factory=lambda: run_cold_email_campaign(campaign_brief),
        evaluation=eval_config,
        project_name=LANGCHAIN_PROJECT,
        verbose=True,
    )

    return results

# Streamlit UI
def main():
    st.title("Advanced Cold Email Agent")
    st.write("Welcome to the Cold Email Agent powered by CrewAI and monitored by LangSmith!")

    campaign_brief = st.text_area("Enter your campaign brief:", height=150)
    
    if st.button("Run Campaign"):
        if campaign_brief:
            with st.spinner("Running cold email campaign..."):
                start_time = time.time()
                result = run_cold_email_campaign(campaign_brief)
                end_time = time.time()
                
                eval_results = evaluate_campaign(campaign_brief)
                
            st.success("Campaign completed!")
            st.write("Campaign Result:", result)
            st.write(f"Time taken: {end_time - start_time:.2f} seconds")
            st.write("LangSmith Evaluation Results:", eval_results)
        else:
            st.warning("Please enter a campaign brief.")

if __name__ == "__main__":
    main()
