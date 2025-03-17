import serial
import csv
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import subprocess  # Import subprocess to run scripts
import os  # For file operations

# Serial configuration
arduino = serial.Serial('COM4', 115200)  # Update with your correct port
input_file = 'separated_commands.csv'
regression_file = 'regression_data.csv'  # New file for regression data

# Email configuration
email_from = ""  # Change to your email
email_password = ""  # Change to your email password

# Command mapping
command_mapping = {
    69: 1,         # 69 -> 1
    70: 2,         # 70 -> 2
    71: 3,         # 71 -> 3
    68: 4,         # 68 -> 4
    64: 5,         # 64 -> 5
    67: 6,         # 67 -> 6
    7: 7,          # 7 -> 7
    21: 8,         # 21 -> 8
    9: 9,          # 9 -> 9
    25: 0,         # 25 -> 0
    28: 'OK',      # OK button
    13: 'Enter',   # Enter button
    22: '.',       # Period (decimal point)
    82: '-',       # Dash (-)
    0x8: 'Backspace',  # Backspace action
    0xD: '#',      # Save and exit action
    0x5A: 'Email',  # Email trigger command (assign a correct hex value)
    0x18: 'ArrowUp',  # New command for Arrow Up (0x18)
    0x52: 'ArrowDown'
}

input_buffer = []  # Buffer for numbers entered
data_matrix = []   # Stores X, X2, Y values in rows
odd_even_flag = 0  # 0 for X, 1 for X2, 2 for Y
data_entered = False  # Check if in data entry mode
previous_command = None  # Track the last command
in_multiple_regression_mode = False  # Flag for multiple regression mode


def save_to_csv(data_matrix, file_name, in_multiple_regression_mode):
    """Save the current matrix of numbers to CSV, format depending on mode."""
    with open(file_name, 'w', newline='') as f:  # Open in write mode to clear file
        csv_writer = csv.writer(f)

        # Write the header based on the mode
        if in_multiple_regression_mode:
            csv_writer.writerow(["X", "X2", "Y"])  # Write header for multiple regression
        else:
            csv_writer.writerow(["X", "X2"])  # Write header for linear regression

        # Write the data rows based on the mode
        for row in data_matrix:
            if in_multiple_regression_mode:
                csv_writer.writerow(row)  # Save [X, X2, Y] for multiple regression
            else:
                csv_writer.writerow(row[:2])  # Save only [X, X2] for linear regression


def save_for_regression(data_matrix):
    """Save data in the format for multiple regression."""
    with open(regression_file, 'a', newline='') as f:
        csv_writer = csv.writer(f)
        for row in data_matrix:
            csv_writer.writerow([row[0], row[1], row[2]])  # Save in the format [['1','1.2','1150']] 


def send_email_with_results():
    """Send the CSV file content via email."""
    recipient_email = ""  # Update with recipient email

    # Create email
    msg = MIMEMultipart()
    msg['From'] = email_from
    msg['To'] = recipient_email
    msg['Subject'] = "Command Data CSV File"

    # Attach CSV file
    with open(input_file, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename={input_file}")
        msg.attach(part)

    # Send email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(email_from, email_password)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


def process_input_data(input_buffer, data_matrix, odd_even_flag, in_multiple_regression_mode):
    """Process the input data and update the matrix accordingly."""
    command_str = ''.join(map(str, input_buffer))  # Convert input buffer to a string

    if in_multiple_regression_mode:
        # In multiple regression mode (collect X, X2, Y)
        if odd_even_flag == 0:
            # If X column (first column) is empty, create a new row
            if len(data_matrix) == 0 or data_matrix[-1][0] is not None:
                data_matrix.append([command_str, None, None])  # New row with X value
            else:
                data_matrix[-1][0] = command_str  # Fill X (first column)
            odd_even_flag = 1  # Switch to X2 column
        elif odd_even_flag == 1:
            # If X2 column (second column) is empty, fill it
            if len(data_matrix) > 0 and data_matrix[-1][0] is not None:
                data_matrix[-1][1] = command_str  # Fill X2 (second column)
                odd_even_flag = 2  # Switch to Y column
            else:
                print("Error: No X value entered yet.")
        else:  # Y column (third column)
            if len(data_matrix) > 0 and data_matrix[-1][1] is not None:
                data_matrix[-1][2] = command_str  # Fill Y (third column)
                odd_even_flag = 0  # Reset to X column for next entry
            else:
                print("Error: No X2 value entered yet.")
                return odd_even_flag  # Skip if there's no X2 value

    else:
        # In linear regression mode (collect only X, X2)
        if odd_even_flag == 0:
            # If X column (first column) is empty, create a new row
            if len(data_matrix) == 0 or data_matrix[-1][0] is not None:
                data_matrix.append([command_str, None])  # New row with X value
            else:
                data_matrix[-1][0] = command_str  # Fill X (first column)
            odd_even_flag = 1  # Switch to X2 column
        elif odd_even_flag == 1:
            # If X2 column (second column) is empty, fill it
            if len(data_matrix) > 0 and data_matrix[-1][0] is not None:
                data_matrix[-1][1] = command_str  # Fill X2 (second column)
                odd_even_flag = 0  # Reset to X column for next entry
            else:
                print("Error: No X value entered yet.")
                return odd_even_flag  # Skip if there's no X value

    return odd_even_flag



while True:
    try:
        if arduino.in_waiting > 0:
            ir_data = arduino.readline().decode('utf-8').strip()
            if ir_data and "Command=0x" in ir_data:
                command_start_index = ir_data.find("Command=0x") + len("Command=0x")
                command_hex = ir_data[command_start_index:command_start_index + 2]
                command = int(command_hex, 16)
                mapped_command = command_mapping.get(command)

                if mapped_command is not None:
                    if mapped_command == 'OK':
                        print("Entering data entry mode...")
                        input_buffer = []
                        data_entered = True

                    elif mapped_command == '#':
                        if input_buffer:
                            odd_even_flag = process_input_data(input_buffer, data_matrix, odd_even_flag, in_multiple_regression_mode)

                            # Save the current matrix of numbers to CSV
                            save_to_csv(data_matrix, input_file, in_multiple_regression_mode)  # Save with mode formatting
                            print(f"Saved: {data_matrix}")
                            input_buffer = []  # Clear buffer
                        data_entered = False
                    elif mapped_command == 'ArrowUp':
                        # Toggle between multiple regression mode and linear regression mode
                        in_multiple_regression_mode = not in_multiple_regression_mode
                        
                        # Clear buffer and file entirely to reset
                        data_matrix.clear()  # Clear the data matrix
                        input_buffer.clear()  # Clear the input buffer
                        save_to_csv([], input_file, in_multiple_regression_mode)  # Clear the file and reset
                        
                        # Debugging print to track the mode
                        if in_multiple_regression_mode:
                            print("Switched to Multiple Regression mode.")
                        else:
                            print("Switched to Linear Regression mode.")
                        
                        # Print which mode is currently active
                        mode = "Multiple Regression" if in_multiple_regression_mode else "Linear Regression"
                        print(f"Current mode: {mode}.")

                    elif mapped_command == 'ArrowDown':
                        # Switch to Linear Regression mode explicitly when ArrowDown is pressed
                        in_multiple_regression_mode = False
                        
                        # Clear buffer and file entirely to reset
                        data_matrix.clear()  # Clear the data matrix
                        input_buffer.clear()  # Clear the input buffer
                        save_to_csv([], input_file, in_multiple_regression_mode)  # Clear the file and reset
                        
                        # Debugging print to track the mode
                        print("Switched to Linear Regression mode.")
                        
                        # Print the current mode (should be Linear Regression)
                        mode = "Linear Regression"
                        print(f"Current mode: {mode}.")



                    elif mapped_command == 'Email' and in_multiple_regression_mode == False:
                        print("Running IRCalculate.py script...")
                        # Run the IRCalculate.py script using subprocess
                        subprocess.Popen(["python", "IRCalculate.py"])

                    elif mapped_command == 'Email' and in_multiple_regression_mode == True:
                        print("Running saveIRMultipl.py script...")
                        # Run the IRCalculate.py script using subprocess
                        subprocess.Popen(["python", "saveIRMult/saveIRMultipl.py"])

                    elif mapped_command == 'Backspace':
                        if input_buffer:
                            input_buffer.pop()  # Remove last element
                            print(f"Data so far: {''.join(input_buffer)}")

                    elif isinstance(mapped_command, (int, str)):
                        if data_entered:
                            input_buffer.append(str(mapped_command))
                            print(f"Data so far: {''.join(input_buffer)}")

                    # Introduce delay to prevent duplicate inputs
                    time.sleep(0.1)

                previous_command = mapped_command

    except KeyboardInterrupt:
        print("Exiting program.")
        break
    except Exception as e:
        print(f"Error: {e}")
