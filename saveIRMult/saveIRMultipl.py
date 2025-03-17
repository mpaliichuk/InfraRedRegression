import csv
import numpy as np
import statsmodels.api as sm
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import sys

# Read data from the CSV file and extract X1, X2, and Y
# input_file = 'separated_commands_for_mult.csv'   #This is test for correctness of data
input_file = 'separated_commands.csv'

X1 = []
X2 = []
Y = []

with open(input_file, 'r') as f:
    reader = csv.reader(f)
    header = next(reader)  # Skip header row
    for row in reader:
        try:
            x1 = float(row[0])  # First column (X1)
            x2 = float(row[1])  # Second column (X2)
            y = float(row[2])   # Third column (Y)
            X1.append(x1)
            X2.append(x2)
            Y.append(y)
        except ValueError:
            continue

# Convert lists to numpy arrays
X1 = np.array(X1)
X2 = np.array(X2)
Y = np.array(Y)

# Combine X1, X2 into the matrix X (with constant for intercept)
X = np.column_stack((np.ones(len(X1)), X1, X2))  # Add a column of ones for intercept

# Fit the regression model using statsmodels (OLS)
model = sm.OLS(Y, X)
results = model.fit()

# Extract coefficients and standard errors
a = results.params  # Coefficients a0, a1, a2
Se2 = np.sum(results.resid**2) / (len(Y) - X.shape[1])  # Residual variance Se^2
Sigma_a = Se2 * np.linalg.inv(X.T @ X)  # Variance-covariance matrix Sigma_a
S_a = np.sqrt(np.diag(Sigma_a))  # Standard errors for coefficients

# Print regression coefficients and standard errors
print(f"Regression coefficients: a0 = {a[0]:.9f}, a1 = {a[1]:.9f}, a2 = {a[2]:.9f}")
print(f"Residual variance (Se^2): {Se2:.9f}")
print(f"Variance-covariance matrix (Sigma_a):\n{Sigma_a}")
print(f"Standard errors for coefficients: {S_a}")

# Compute predicted values and differences
Y_pred = results.predict(X)
Diff = Y - Y_pred

# Prepare data for output with headers
output_file = 'console_output.txt'
with open(output_file, 'w') as f:
    f.write(f"Regression coefficients: a0 = {a[0]:.9f}, a1 = {a[1]:.9f}, a2 = {a[2]:.9f}\n")
    f.write(f"Residual variance (Se^2): {Se2:.9f}\n")
    f.write(f"Variance-covariance matrix (Sigma_a):\n{Sigma_a}\n")
    f.write(f"Standard errors for coefficients: {S_a}\n")
    f.write("\nX1\tX2\tY\tY_pred\tResidual\n")
    for x1, x2, y_val, y_pred, diff in zip(X1, X2, Y, Y_pred, Diff):
        f.write(f"{x1}\t{x2}\t{y_val}\t{round(y_pred, 9)}\t{round(diff, 9)}\n")

# Email configuration
email_from = ""  # Replace with your email
email_password = ""  # Replace with your email password
email_to = input("Enter the email address to send the console output: ")
subject = "Console Output: Multiple Regression Results"

# Create the email message
msg = MIMEMultipart()
msg['From'] = email_from
msg['To'] = email_to
msg['Subject'] = subject

body = "Please find the attached console output file containing the regression results."
msg.attach(MIMEText(body, 'plain'))

# Attach the console output file
with open(output_file, 'rb') as attachment:
    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment.read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename={output_file}")
    msg.attach(part)

# Send the email
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)  # Adjust if using another email provider
    server.starttls()
    server.login(email_from, email_password)
    server.send_message(msg)
    server.quit()
    print(f"Email sent successfully to {email_to}")
except Exception as e:
    print(f"Failed to send email: {e}")
