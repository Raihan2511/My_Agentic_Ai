# This is NOT main3.py. This is a new file.

# Import your compiled agent (the "smart employee")
from main3 import app 
from Backend.Tools.email.email_toolkit import EmailToolkit # Need this to check email

import time

def main_loop():
    print("Email agent is live. Watching for new emails...")
    email_checker = EmailToolkit().get_tool("Read_Email") # Get just the reading tool

    while True:
        # 1. Check for new, unread emails
        # You'd need to modify your Read_Email tool to only get UNREAD messages
        unread_emails = email_checker.check_for_unread_emails() 

        if unread_emails:
            for email in unread_emails:
                print(f"New email found: '{email['Subject']}'. Processing...")
                
                # 2. This is where you replace 'human_input'
                # Instead of a generic prompt, you give the *actual* email content
                task = f"A new email has arrived. Please process this text: {email['Message Body']}"

                # 3. Run the agent on this specific task
                for event in app.stream({"messages": [("user", task)]}):
                    # ... (you can print the output just like in main3)
                    print(event)
                
                # 4. (Optional) Mark the email as "Read" so you don't process it again

        else:
            print("No new emails. Waiting 5 minutes...")
            time.sleep(300) # Wait for 5 minutes (300 seconds)

if __name__ == "__main__":
    main_loop()