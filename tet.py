from mailjet_rest import Client

# Mailjet API credentials
api_key = 'cef0f9951409ba2ca60c6eaf8249fc6c'
api_secret = '0e7e14a8a82f84228a5a95125b4081ae'

# Initialize Mailjet client
mailjet = Client(auth=(api_key, api_secret), version='v3.1')

# Email data
data = {
    'Messages': [
        {
            "From": {
                "Email": "varunsrichin1@gmail.com",
                "Name": "Varun"
            },
            "To": [
                {
                    "Email": "varunsrichin@gmail.com",
                    "Name": "Varun"
                }
            ],
            "Subject": "Greetings from Mailjet.",
            "TextPart": "My first Mailjet email",
            "HTMLPart": "<h3>Dear passenger 1, welcome to <a href='https://www.mailjet.com/'>Mailjet</a>!</h3><br />May the delivery force be with you!",
            "CustomID": "AppGettingStartedTest"
        }
    ]
}

# Send email
result = mailjet.send.create(data=data)

# Print result
print(result.status_code)
print(result.json())
