import csv
import numpy as np
import statsmodels.api as sm
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import sys

# Read data from the CSV file and extract Uinput and Uoutput
input_file = 'separated_commands.csv'

Uinput = []
Uoutput = []

with open(input_file, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)  # Skip header row
    for row in reader:
        try:
            Uin = float(row[0])  # First column (Uinput)
            Uout = float(row[1])  # Second column (Uoutput)
            Uinput.append(Uin)
            Uoutput.append(Uout)
        except ValueError:
            continue

# Convert lists to numpy arrays
Uinput = np.array(Uinput)
Uoutput = np.array(Uoutput)

# Add constant for intercept in regression model
X = sm.add_constant(Uinput)  # X = [1, Uinput]
Y = Uoutput

# Fit the regression model
model = sm.OLS(Y, X)
results = model.fit()

# Extract coefficients and standard errors
a0 = results.params[0]  # Intercept
a1 = results.params[1]  # Coefficient for Uinput

s0 = results.bse[0]  # Standard Error of Intercept
s1 = results.bse[1]  # Standard Error of Coefficient

# Redirect console output to a text file
console_output_file = 'console_output.txt'
with open(console_output_file, 'w') as output_file:
    sys.stdout = output_file  # Redirect stdout to file

    # Print regression coefficients and standard errors
    print(f"Intercept (a0): {a0:.9f}")
    print(f"Coefficient for Uinput (a1): {a1:.9f}")
    print(f"\nStandard Errors:")
    print(f"s0 (Standard Error of Intercept): {s0:.9f}")
    print(f"s1 (Standard Error of Coefficient): {s1:.9f}")

    # Calculate predicted values and differences
    Upredicted = results.predict(X)
    Diff = Uoutput - Upredicted

    # Prepare data for output with headers
    print("\nUinput\tUoutput\tUpredicted\tResidual")
    for uin, uout, upred, diff in zip(Uinput, Uoutput, Upredicted, Diff):
        print(f"{uin}\t{uout}\t{round(upred, 9)}\t{round(diff, 9)}")

    sys.stdout = sys.__stdout__  # Reset stdout back to console

# Prompt the user for an email address
email_to = input("Enter the email address to send the console output: ")

# Email configuration
email_from = ""  # Replace with your email
email_password = ""  # Replace with your email password (use environment variables or config file in production)
subject = "Console Output: Regression Results"

# Create the email message
msg = MIMEMultipart()
msg['From'] = email_from
msg['To'] = email_to
msg['Subject'] = subject

body = "Please find the attached console output file containing the regression results."
msg.attach(MIMEText(body, 'plain'))

# Attach the console output file
with open(console_output_file, 'rb') as attachment:
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename= {console_output_file}")
    msg.attach(part)

# Send the email
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)  # Adjust if using another email provider
    server.starttls()
    server.login(email_from, email_password)
    server.send_message(msg)
    server.quit()
    print(f"\nEmail sent successfully to {email_to}")
except Exception as e:
    print(f"\nFailed to send email: {e}")
