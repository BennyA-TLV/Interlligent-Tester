import pandas as pd
from pathlib import Path
from email.message import EmailMessage
import win32com.client
from pypdf import PdfReader
import subprocess
import csv
import tomllib
import smtplib
import time
import re
import os
import sys
import logging
import webbrowser
import mimetypes
from html import escape
from datetime import datetime
from dateutil.relativedelta import relativedelta


# Created by Benny Aberman - 054-3220104
# Connection functions
    # The load configuration toml file function
    # The get the url function
    # The get option descriptions function
    # The find option descriptions function
    # The find last file in folder function
    # The report procces/PDF/bar function
    # The check if STOP process function


sender_email="Intelligent.Tester.New@gmail.com"
app_password ="xiklxfudofbhavuh"

# The load configuration toml file function - loading the toml file to extract the paths for the files
def load_configFile(file_path):

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    toml_path = os.path.join(base_dir, "Files", "configs.toml")
    #base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
    #toml_path = os.path.join(base_dir, "Files", "configs.toml")
    #debug_print(f"toml_path = {toml_path}")
    #debug_print(f"toml exists = {os.path.exists(toml_path)}")

    try:
        with open(toml_path, "rb") as f:
            config = tomllib.load(f)

        output_path = config['output_files']['path_pdf_reports_root']
        screenshot_path = config['output_files']['screenShot_root']
        log_path = config['output_files']['log_root']

        bat_mircmd_path = config['input_files']['bat_mircmd_root']
        download_path = config['input_files']['path_download_root']
        url_path = config['input_files']['url_root']
        email_path = config['input_files']['email_root']
        option_path = config['input_files']['option_descriptions_root']
        license_path = config['input_files']['license_descriptions_root']
        password_path = config['input_files']['password_root']


        if file_path.strip() == "pdf_reports_path":
            return output_path
        elif file_path.strip() == "download_path":
            return download_path
        elif file_path.strip() == "screenShot_path":
            return screenshot_path
        elif file_path.strip() == "url_path":
            return url_path
        elif file_path.strip() == "email_path":
            return email_path
        elif file_path.strip() == "option_path":
            return option_path
        elif file_path.strip() == "license_path":
            return license_path
        elif file_path.strip() == "bat_mircmd_path":
            return bat_mircmd_path
        elif file_path.strip() == "log_path":
            return log_path
        elif file_path.strip() == "password_path":
            return password_path
        else:
            return None

    except FileNotFoundError:
        print(f"Error: The file {toml_path} was not found.")
    except KeyError as e:
        print(f"Error: Missing key in TOML file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# The get the passwords function - getting the admin password from the passwords files
def get_passwords(user, path_file):
    file_path = os.path.abspath(os.path.join(path_file, "Password.csv"))

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exist: {file_path}")

    try:
        df = pd.read_csv(file_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding="ISO-8859-8")

    df = df.fillna("")

    if "User" not in df.columns or "Password" not in df.columns:
        raise ValueError("CSV must contain columns: User,Password")

    passwords = df.loc[
        df["User"].astype(str).str.strip().str.lower() == user.strip().lower(),
        "Password"
    ].astype(str).str.strip().tolist()

    return passwords

# The get the url function - getting the url from the urls files
def get_urls(option, path_file):

    file_path = os.path.join(path_file, "Url.csv")
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exists in {file_path}")

    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='ISO-8859-8')

    urls =  [df[col].tolist() for col in df.columns]

    for opt in range(len(urls[0])):
        if option.strip() == urls[0][opt].strip():
            return urls[1][opt]
    return "No url"

# The get option descriptions function - getting the description form the option_descriptions.csv file
def get_option_descriptions(path_file):

    file_path = os.path.join(path_file, "Option_descriptions.csv")
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exists in {file_path}")

    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='ISO-8859-8')

    return [df[col].tolist() for col in df.columns]

# The get license descriptions function - getting the description form the license_descriptions.xlsx file
def get_license_descriptions(path_file):

    file_path = os.path.join(path_file, "License_descriptions.xlsx")
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exists in {file_path}")

    try:
        df = pd.read_excel(file_path, dtype=str)
    except UnicodeDecodeError:
        df = pd.read_excel(file_path, dtype=str)

    return [df[col].tolist() for col in df.columns]

# The find option descriptions function - finding the description in the option_descriptions.csv file
def find_option_descriptions(option_descriptions, option):

    for opt in range(len(option_descriptions[0])):
        if str(option.strip()) == str(option_descriptions[0][opt]).strip():
            return option_descriptions[1][opt]
    return "No Description"

# The find last file in folder function
def get_latest_file(folder_path, model, download, contains_text=None):

    path = Path(folder_path, model)

    if not path.exists() or not path.is_dir():
        return "None"
    files = [f for f in path.iterdir() if f.is_file()]

    if not files:
        return "None"

    if download:
        return max(files, key=lambda f: f.stat().st_mtime).name

    else:
        if contains_text:
            files = [f for f in files if contains_text.lower() in f.name.lower()]
            if not files:
                return "No file found in the directory."
            return max(files, key=lambda f: f.stat().st_mtime).name

        return "None"

def find_file_by_name(folder_path, model, download, contains_text=None):

    path = Path(folder_path, model)

    if not path.is_dir():
        return None

    files = [
        f for f in path.iterdir()
        if f.is_file() and contains_text.lower() in f.name.lower()
    ]

    if not files:
        return None

    if download:
        return max(files, key=lambda f: f.stat().st_mtime).name
    else:
        if contains_text:
            files = [f for f in files if contains_text.lower() in f.name.lower()]
            if not files:
                return "No file found in the directory."
            return max(files, key=lambda f: f.stat().st_mtime).name

        return "None"

# The report procces/PDF/bar function
def report_step(name, status, progress, results_list, value = "", image_path = None, worker=None, logger=None):

    step = {"type": "step", "name": name, "status": status, "value": value, "image_path": image_path, "time": time.strftime("%H:%M:%S")}

    results_list.append(step)
    if logger:
        logger.info(f"{name} | {status} | {value}")
    if worker:
        if status.upper() == "FAIL":
            worker.test_failed = True
        worker.table_update.emit(worker.current_row_index, name, status, value)
        worker.progress_update.emit(worker.current_row_index, progress)

# The check if STOP process function
def check_progress(worker=None):
    if worker and worker.is_killed:
        logging.warning(f"Test stopped by user | Slot={worker.current_row_index + 1}")
        print("Stopping now...")
        return True
    else:
        return False

def add_report_table(title, headers, rows, results_list):
    results_list.append({"type": "data_table", "title": title, "headers": headers, "rows": rows})

def create_data_table(title, headers):
    return {"type": "data_table", "title": title, "headers": headers, "rows": []}

def add_data_row(table_object, row_data):
    table_object["rows"].append(row_data)

def create_text_table(title):
    return {"type": "text_table", "title": title, "rows": []}

def add_text_row(table_object, text):
    table_object["rows"].append(text)

# The e-mails recipients for the csv file
def load_email_recipients(csv_file, notify_type):
    recipients = []
    with open(csv_file, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            enabled = row.get("Enabled", "").strip().upper()
            email = row.get("Email", "").strip()

            if notify_type == "start":
                notify = row.get("Notify Start", "").strip().upper()
            elif notify_type == "end":
                notify = row.get("Notify End", "").strip().upper()
            else:
                notify = "NO"

            if enabled == "YES" and notify == "YES" and email:
                recipients.append(email)
    return recipients

def send_test_started_email_gmail(recipients, device_type, slot, ip):
    if not recipients:
        return

    subject = f"TEST STARTED - {device_type}"
    html_body = f"""
    <html>
    <body style="font-family: Arial; direction:ltr;">
    <div style="max-width:650px; margin:auto; background:white; border-radius:10px; padding:25px; border:1px solid #ddd;">
    <h2 style="color:#1f4e79;">Test Started</h2>
    <p style="font-size:15px;">
    A new test has started on the Intelligent Tester system.
    </p>
    <table style="width:100%; border-collapse:collapse; direction:ltr;">
    <tr><td width="35%"><b>Unit</b></td><td>{device_type}</td></tr>
    <tr><td><b>Slot</b></td><td>{slot}</td></tr>
    <tr><td><b>IP Address</b></td><td>{ip}</td></tr>
    <tr><td><b>Start Time</b></td><td>{time.strftime('%H:%M:%S')}</td></tr>
    </table>
    <br>
    <div style="padding:12px; background:#dbeafe; color:#1e40af; border-radius:8px; font-weight:bold;">
    Status: RUNNING
    </div>
    <br>
    <p style="color:#777; font-size:12px;">
    This message was generated automatically by Intelligent Tester.
    </p>
    </div>
    </body>
    </html>
    """
    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content("Test started.")
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)

def send_test_ended_email_gmail(recipients, device_name, device_type, slot, ip, final_status, pdf_file):

    if not recipients:
        return

    subject = f"TEST {final_status} - {device_type} - {device_name}"

    status_color = "#16a34a" if final_status == "PASSED" else "#dc2626"

    html_body = f"""
    <html>
    <body style="font-family: Arial; direction:ltr;">
    <div style="max-width:650px; margin:auto; background:white; border-radius:10px; padding:25px; border:1px solid #ddd;">
    <h2 style="color:#1f4e79;">📄 Test Finished</h2>
    <p style="font-size:15px;">
    The test has completed. The PDF report is attached.
    </p>
    <table style="width:100%; border-collapse:collapse; direction:ltr;">
    <tr><td width="35%"><b>Unit</b></td><td>{device_name}</td></tr>
    <tr><td><b>Unit</b></td><td>{device_type}</td></tr>
    <tr><td><b>Slot</b></td><td>{slot}</td></tr>
    <tr><td><b>IP Address</b></td><td>{ip}</td></tr>
    <tr><td><b>Finished Time</b></td><td>{time.strftime('%H:%M:%S')}</td></tr>
    </table>
    <br>
    <div style="padding:14px; background:{status_color}; color:white; border-radius:8px; font-size:18px; font-weight:bold; text-align:center;">
    {final_status}
    </div>
    <br>
    <p style="color:#777; font-size:12px;">
    This message was generated automatically by Intelligent Tester.
    </p>
    </div>
    </body>
    </html>
    """

    msg = EmailMessage()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content("Test finished.")
    msg.add_alternative(html_body, subtype="html")

    if pdf_file and os.path.exists(pdf_file):
        with open(pdf_file, "rb") as file:
            msg.add_attachment(
                file.read(),
                maintype="application",
                subtype="pdf",
                filename=os.path.basename(pdf_file)
            )

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)

# Send email using the installed Microsoft Outlook.
def send_outlook_email(subject, html_body, recipients, attachment=None):
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)

        mail.To = ";".join(recipients)
        mail.Subject = subject
        mail.HTMLBody = html_body

        if attachment and os.path.exists(attachment):
            mail.Attachments.Add(os.path.abspath(attachment))

        mail.Send()

        print("Outlook email window opened successfully.")

    except Exception as e:
        print(f"Failed to create Outlook email: {e}")

def send_test_started_email(recipients, device_type, slot, ip, is_new_device):

    if not recipients:
        return

    subject = f"TEST STARTED - {device_type}"

    html_body = f"""
    <html>
    <body style="font-family: Arial;">
    <div style="max-width:650px;
                margin:auto;
                border:1px solid #cccccc;
                border-radius:10px;
                padding:25px;">
    <h2 style="color:#1f4e79;">
        Intelligent Tester
    </h2>
    <h3 style="color:#0f766e;">
        Test Started
    </h3>
    <p>
    A new automatic test has started.
    </p>
    <table style="width:100%; border-collapse:collapse;">
        <tr>
            <td width="35%"><b>Device Type</b></td>
            <td>{device_type}</td>
        </tr>
        <tr>
            <td><b>Slot</b></td>
            <td>{slot}</td>
        </tr>
        <tr>
            <td><b>IP Address</b></td>
            <td>{ip}</td>
        </tr>
        <tr>
            <td><b>Start Time</b></td>
            <td>{time.strftime("%Y-%m-%d %H:%M:%S")}</td>
        </tr>
    </table>
    <br>
    <div style="
        background:#2563eb;
        color:white;
        padding:12px;
        border-radius:6px;
        text-align:center;
        font-size:18px;
        font-weight:bold;">
        RUNNING
    </div>
    <br>
    <small style="color:gray;">
    This message was generated automatically by Intelligent Tester.
    </small>
    </div>
    </body>
    </html>
    """

    send_outlook_email(
        subject,
        html_body,
        recipients
    )

def calibExpartion(extra_data):
    try:
        # Calibration date
        calibration_date = datetime.strptime(extra_data[1],"%d/%m/%Y %H:%M")

        # Expiration date = Calibration date + 1 year
        calibration_expiration = calibration_date + relativedelta(years=1)

        # Days until expiration
        days_left = (calibration_expiration.date() - datetime.now().date()).days
        expiration_str = calibration_expiration.strftime("%d/%m/%Y %H:%M")

        # Red if expired or will expire within 60 days
        if days_left <= 60:
            expiration_html = (f'<span style="color:red; font-weight:bold;">'f'{expiration_str}'f'</span>')
        else:
            expiration_html = expiration_str

        return expiration_html

    except (ValueError, TypeError, IndexError):
        expiration_html = "Unknown"

def send_test_ended_email(recipients, device_name, device_type, slot, ip, final_status, pdf_file, extra_data, is_new_device):

    preview = False

    if not recipients:
        print("Email recipients list is empty.")
        return False

    try:
        pdf_info = extract_device_info_from_pdf(pdf_file)
        model = pdf_info.get("device_type", "Unknown")
        serial_number = pdf_info.get("device_name", "Unknown")

        if not model or model == "Unknown":
            model = device_name

        if not serial_number or serial_number == "Unknown":
            serial_number = device_name

        is_n90_family = (isinstance(model, str) and model.upper().startswith("N90"))

        print(f"Model from PDF: {model}")
        print(f"Serial from PDF: {serial_number}")
        print(f"is_new_device: {is_new_device}")
        print(f"is_n90_family: {is_n90_family}")

        system_images = []
        license_images = []

        if is_n90_family and is_new_device:

            system_images, license_images = get_n90_email_images(serial_number)
            subject, html_body = build_new_n90_device_email(pdf_info=pdf_info, system_images=system_images, license_images=license_images, preview=preview)

            # =====================================================
            # REGULAR DEVICE
            # =====================================================
        else:
            expiration_html = calibExpartion(extra_data)
            subject = (f"TEST ENDED - " f"{device_type} - " f"{device_name} - " f"{final_status}")
            html_body = f"""
                   <html>
                   <body style="
                       font-family:
                       Aptos,Calibri,Arial,sans-serif;
                       font-size:11pt;
                   ">
                       <h2>
                           Test Completed
                       </h2>
                       <p>
                           <b>Device:</b>
                           {device_type}
                           <br>
                           <b>Serial Number:</b>
                           {device_name}
                           <br>
                           <b>Slot:</b>
                           {slot}
                           <br>
                           <b>IP Address:</b>
                           {ip}
                           <br>
                           <b>Final Status:</b>
                           {final_status}
                           <br>
                           <b>Calibration_date:</b>
                           {extra_data[0]} - {extra_data[1]}
                           <br>
                           <b>Calibration expiration date:</b>
                           {expiration_html}
                       </p>
                       <p>
                           The test report
                           is attached.
                       </p>
                   </body>
                   </html>
                   """
            # =====================================================
            # PREVIEW MODE
            # =====================================================
        if preview:
            preview_email(subject=subject, html_body=html_body, recipients=recipients, pdf_file=pdf_file)
            return True

            # =====================================================
            # OUTLOOK
            # =====================================================
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        if isinstance(recipients, (list, tuple, set)):
            mail.To = "; ".join(recipients)
        else:
            mail.To = str(recipients)

        mail.Subject = subject
        mail.HTMLBody = html_body

        # =====================================================
        # NEW N90 INLINE IMAGES
        # =====================================================
        if is_n90_family and is_new_device:
            add_inline_images(mail=mail, image_paths=system_images, cid_prefix="system_image")
            add_inline_images(mail=mail, image_paths=license_images, cid_prefix="license_image")

        # =====================================================
        # PDF ATTACHMENT
        # =====================================================
        if pdf_file and os.path.isfile(pdf_file):
            mail.Attachments.Add(os.path.abspath(pdf_file))

        # =====================================================
        # SEND
        # =====================================================
        mail.Send()
        print(f"Email sent successfully: " f"{subject}")
        return True

    except Exception as error:
        print(f"Failed to create/send " f"email: {error}")
        return False

def create_test_logger(row_index):

    logFile = log_file(row_index)
    logger = logging.getLogger(f"Slot_{row_index + 1}_{datetime.now().strftime('%H_%M_%S')}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.handlers.clear()

    if not logger.handlers:
        handler = logging.FileHandler(logFile, encoding="utf-8")

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger, logFile

def log_file(row_index):

    log_dir = load_configFile("log_path")
    #debug_print(load_configFile("log_path"))
    if not log_dir:
        raise Exception("log_path not found in config.toml")
    #debug_print(f"log_dir = {log_dir}")
    os.makedirs(log_dir, exist_ok=True)

    return os.path.join(log_dir, f"Slot_{row_index + 1}_{datetime.now().strftime('%H%M%S')}.log")

def handle_exception(exc_type, exc_value, exc_traceback):

    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.critical(
        "Unhandled exception",
        exc_info=(exc_type, exc_value, exc_traceback)
    )

def resource_path(relative_path):

    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()

def debug_print(message):
    debug_file = os.path.join(app_base_dir(), "debug_startup.log")

    with open(debug_file, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} | {message}\n")

def device_information(device, worker=None, logger=None, timeout=600):
    results_list = []
    device_model = "None"
    serial_number = "None"
    instrument_ready = False

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            device.connect()

            idn = device.query("*IDN?")

            if idn and idn.strip():
                idn = idn.strip()
                print(f" > Instrument Ready: {idn}")
                instrument_ready = True
                break

        except Exception as error:
            print(f" > Instrument not ready: {type(error).__name__}: {error}")

            try:
                device.disconnect()
            except Exception:
                pass

        print(" > Waiting for app to finish loading...")

        report_step(
            "Waiting for app to finish loading...",
            "INFO",
            0,
            results_list,
            " ",
            None,
            worker,
            logger
        )

        if check_progress(worker):
            try:
                device.disconnect()
            except Exception:
                pass

            return serial_number, device_model, results_list

        time.sleep(30)

    if not instrument_ready:
        print(" > Timeout waiting for app")

        report_step(
            "Device isn't replying",
            "FAIL",
            1,
            results_list,
            "Timeout waiting for *IDN? response",
            None,
            worker,
            logger
        )

        try:
            device.disconnect()
        except Exception:
            pass

        return serial_number, device_model, results_list

    report_step(
        "Device is replying",
        "PASS",
        1,
        results_list,
        idn,
        None,
        worker,
        logger
    )

    # Keysight Technologies,E5061B,MY12345678,A.xx.xx
    idn_parts = [part.strip() for part in idn.split(",")]

    if len(idn_parts) >= 2:
        device_model = idn_parts[1]

    if len(idn_parts) >= 3:
        serial_number = idn_parts[2]

    try:
        device.disconnect()
    except Exception as error:
        print(f" > Disconnect warning: {error}")

    return serial_number, device_model, results_list

# Wait until remote device replies to ping, timeout: max wait time in seconds, interval: seconds between ping attempts
def wait_for_ping(ip, worker=None, logger=None, timeout=300, interval=5):

    results_list = []
    start_time = time.time()

    while time.time() - start_time < timeout:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print(f" > Device {ip} is online")
            report_step(f"Device {ip} is online", "PASS", 1, results_list, " ", None, worker, logger)

            return True

        print(f" > Waiting for ping from {ip}...")
        report_step(f"Waiting for ping from {ip}...", "INFO", 1, results_list, " ", None, worker, logger)

        time.sleep(interval)

    print(f" > Timeout: device {ip} did not reply to ping")
    report_step(f"Timeout: device {ip} did not reply to ping", "FAIL", 1, results_list, " ", None, worker, logger)

    return False

def extract_device_info_from_pdf(pdf_file):

    info = {
        "device_type": "Unknown",
        "device_name": "Unknown",
        "firmware_version": "Unknown",
        "calibration_date": "Unknown",
        "calibration expiration date": "Unknown",
        "device_options": "Unknown",
        "windows_version": "Unknown",
        "self_test_status": "Unknown"
    }

    if not pdf_file or not os.path.isfile(pdf_file):
        logging.error(f"PDF file was not found: {pdf_file}")
        return info

    try:
        reader = PdfReader(pdf_file)

        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)

        text = "\n".join(text_parts)
        flat_text = re.sub(r"\s+", " ", text)

        # =====================================================
        # DEVICE TYPE
        # =====================================================
        device_patterns = [
            r"\bUnit\s+([A-Z]\d{4}[A-Z])\b",
            r"Product\s+Number\s*:\s*([A-Z]\d{4}[A-Z])\b",
            r"\bModel\s*:\s*([A-Z]\d{4}[A-Z])\b"
        ]

        for pattern in device_patterns:
            match = re.search(pattern, flat_text, re.IGNORECASE)

            if match:
                info["device_type"] = match.group(1).upper()
                break

        # =====================================================
        # SERIAL NUMBER
        # =====================================================
        serial_patterns = [
            r"Serial\s+Number\s*:\s*([A-Z0-9-]+)",
            r"\bS/N\s*:\s*([A-Z0-9-]+)"
        ]

        for pattern in serial_patterns:
            match = re.search(pattern, flat_text, re.IGNORECASE)

            if match:
                info["device_name"] = match.group(1).strip()
                break

        # =====================================================
        # FIRMWARE VERSION
        # =====================================================
        firmware_patterns = [
            r"\bFirmware\s*:\s*([A-Z]\.\d+(?:\.\d+)*)",

            r"Instrument\s+S\s*/\s*W\s+Revision\s*[:\-]?\s*"
            r"([A-Z]\s*\.\s*\d+(?:\s*\.\s*\d+)*)",

            r"Firmware\s+(?:Revision|Version)\s*[:\-]?\s*"
            r"([A-Z]?\s*\.?\s*\d+(?:\s*\.\s*\d+)*)",
        ]

        for pattern in firmware_patterns:
            match = re.search(pattern, flat_text, re.IGNORECASE)

            if match:
                firmware = re.sub(r"\s+", "", match.group(1))
                info["firmware_version"] = firmware.upper()
                break

        # =====================================================
        # WINDOWS VERSION
        # =====================================================
        windows_match = re.search(
            r"\bWindows\s+(10|11)\b",
            flat_text,
            re.IGNORECASE
        )

        if windows_match:
            info["windows_version"] = (
                f"Windows {windows_match.group(1)}"
            )

        # =====================================================
        # CALIBRATION DATE
        # =====================================================
        calibration_patterns = [
            r"Calibration\s+Date\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"Cal\s+Date\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"Calibration[_\s]+date.*?File\s*Name\s*:\s*.*?-\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
        ]

        for pattern in calibration_patterns:
            match = re.search(pattern, flat_text, re.IGNORECASE)

            if match:
                info["calibration_date"] = match.group(1)
                break

        # =====================================================
        # CALIBRATION EXPIRATION DATE
        # =====================================================
        calibration_expiration_patterns = [
            r"Calibration\s+expiration\s+Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?:\s+\d{1,2}:\d{2})?)",
            r"Cal\s+Exp\s+Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?:\s+\d{1,2}:\d{2})?)",
            r"Calibration[_\s]+expiration[_\s]+date.*?File\s*Name\s*:\s*.*?-\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?:\s+\d{1,2}:\d{2})?)",
        ]

        for pattern in calibration_expiration_patterns:
            match = re.search(pattern, flat_text, re.IGNORECASE)

            if match:
                info["calibration expiration date"] = match.group(1)
                break

        # =====================================================
        # DEVICE OPTIONS
        # =====================================================
        info["device_options"] = extract_device_options(text=text, device_model=info.get("device_type"))

        # =====================================================
        # SELF-TEST
        # =====================================================
        if re.search(r"\bUnit\s+self[-\s]?test\s+passed\b", flat_text, flags=re.IGNORECASE):
            info["self_test_status"] = "PASSED"

        elif re.search(r"\bUnit\s+self[-\s]?test\s+failed\b", flat_text, flags=re.IGNORECASE):
            info["self_test_status"] = "FAILED"

        return info

    except Exception as error:
        logging.exception(f"Failed to extract device information from PDF: {error}")

    return info

# Create an HTML preview of the email and open it in the default browser.
def preview_email(subject, html_body, recipients=None, pdf_file=None):
    try:
        if pdf_file:
            folder = os.path.dirname( os.path.abspath(pdf_file))
        else:
            folder = os.getcwd()

        preview_file = os.path.join(folder, "Email_Preview.html")

        if isinstance(recipients, (list, tuple, set)):
            recipients_text = "; ".join(recipients)
        elif recipients:
            recipients_text = str(recipients)
        else:
            recipients_text = "(No recipients)"

        attachment_text = ""

        if pdf_file:
            attachment_text = f"""
            <hr>
            <p>
                <b>Attachment:</b>
                {escape(os.path.basename(pdf_file))}
            </p>
            """

        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{escape(subject)}</title>
        </head>

        <body style="
            background:#f4f4f4;
            margin:20px;
            font-family:Aptos,Calibri,Arial,sans-serif;
        ">

            <div style="
                background:white;
                border:1px solid #cccccc;
                border-radius:8px;
                padding:25px;
                max-width:900px;
                margin:auto;
            ">
                <p>
                    <b>To:</b>
                    {escape(recipients_text)}
                </p>
                <hr>
                <p>
                    <b>Subject:</b>
                    {escape(subject)}
                </p>
                <hr>
                {html_body}
                {attachment_text}
            </div>
        </body>
        </html>
        """

        with open(preview_file, "w", encoding="utf-8") as file:
            file.write(full_html)
        webbrowser.open("file:///" + preview_file.replace("\\", "/"))
        print(f"Email preview created: {preview_file}")
        return True

    except Exception as error:
        print(f"Failed to create email preview: {error}")
        return False

def build_new_n90_device_email(pdf_info, system_images=None, license_images=None, preview=False):

    system_images = system_images or []
    license_images = license_images or []

    model = pdf_info.get("device_type", "Unknown")
    serial_number = pdf_info.get("device_name", "Unknown")
    firmware_version = pdf_info.get("firmware_version", "Unknown")
    calibration_date = pdf_info.get("calibration_date", "Unknown")
    calibration_expiration_date = pdf_info.get("calibration expiration date", "Unknown")
    device_options = pdf_info.get("device_options", "Unknown")
    windows_version = pdf_info.get("windows_version", "Unknown")
    self_test_status = pdf_info.get("self_test_status", "Unknown")

    if not calibration_date or calibration_date == "Unknown":
        calibration_date = "Not available in report"

    if not calibration_expiration_date or calibration_expiration_date == "Unknown":
        calibration_expiration_date = "Not available in report"

    subject = (f"[INBOUND] {model},{serial_number} " f"add to main from Keysight")

    # =====================================================
    # SYSTEM IMAGES
    # =====================================================
    system_html = ""

    if system_images:
        system_html += """
        <hr>
        <h3>System Information</h3>
        """
        for index, image_path in enumerate(system_images, start=1):
            image_path = Path(image_path)

            if preview:
                image_src = image_path.resolve().as_uri()
            else:
                image_src = f"cid:system_image_{index}"

            system_html += f"""
            <p>
                <b>System Information #{index}</b>
            </p>
            <p>
                <img
                    src="{image_src}"
                    style="
                        max-width:900px;
                        width:100%;
                        height:auto;
                        border:1px solid #cccccc;
                    "
                >
            </p>
            """
    # =====================================================
    # LICENSE IMAGES
    # =====================================================
    license_html = ""

    if license_images:
        license_html += """
        <br>
        <hr>
        <h3>License Information</h3>
        """

        for index, image_path in enumerate(license_images, start=1):
            image_path = Path(image_path)

            if preview:
                image_src = image_path.resolve().as_uri()
            else:
                image_src = f"cid:license_image_{index}"

            license_html += f"""
            <p>
                <b>License Information #{index}</b>
            </p>
            <p>
                <img
                    src="{image_src}"
                    style="
                        max-width:900px;
                        width:100%;
                        height:auto;
                        border:1px solid #cccccc;
                    "
                >
            </p>
            """
    # =====================================================
    # HTML BODY
    # =====================================================
    html_body = f"""
    <html>
    <body style="
        font-family:Aptos,Calibri,Arial,sans-serif;
        font-size:11pt;
        direction:ltr;
        color:#000000;
    ">
        <p>
            <b>Info for Priority:</b>
        </p>
        <ol>
            <li style="margin-bottom:15px;">
                <b>Model:</b>
                {model}
            </li>
            <li style="margin-bottom:15px;">
                <b>S/N:</b>
                {serial_number}
            </li>
            <li style="margin-bottom:15px;">
                <b>FW version:</b>
                {firmware_version}
            </li>
            <li style="margin-bottom:15px;">
                <b>Cal date:</b>
                {calibration_date}
            </li>
             <li style="margin-bottom:15px;">
                <b>Cal expiration date:</b>
                {calibration_expiration_date}
            </li>
            <li style="margin-bottom:15px;">
                <b>Options:</b>
                {device_options}
            </li>
            <li style="margin-bottom:15px;">
                <b>{windows_version}</b>
            </li>
            <li style="margin-bottom:15px;">
                <b>Unit self-test:</b>
                {self_test_status}
            </li>
        </ol>
        {system_html}
        {license_html}
    </body>
    </html>
    """

    return subject, html_body

# Extract N90 options from the System Information option tables.
def extract_n90_system_information_options(text, device_model):

    normalized_text = normalize_pdf_text(text)

    if not normalized_text:
        return []

    section_match = re.search(r"System\s+Information\s+" r"Option\s+ID\s+" r"Name\s*/?\s*Description\s+" r"Option\s+Version" r"(.*?)" r"Keysight\s+License\s+Manager", normalized_text, flags=re.IGNORECASE | re.DOTALL)

    if not section_match:
        return []

    system_section = section_match.group(1)
    model = str(device_model or "").strip().upper()
    patterns = []

    if model:
        patterns.append(rf"\b{re.escape(model)}-[A-Z0-9]+\b")

    patterns.extend([r"\bN\d{4}[A-Z]{0,2}\d*[A-Z]*(?:-[A-Z0-9]+)?\b", r"\bN90[A-Z0-9_]+(?:-[A-Z0-9]+)?\b", r"\bU\d+[A-Z0-9_]+(?:-[A-Z0-9]+)?\b"])
    combined_pattern = "|".join(f"(?:{pattern})" for pattern in patterns)
    raw_options = re.findall(combined_pattern, system_section, flags=re.IGNORECASE)
    cleaned_options = []

    for raw_option in raw_options:
        option_id = clean_n90_option_id(raw_option, device_model)

        if option_id and option_id not in cleaned_options:
            cleaned_options.append(option_id)

    return cleaned_options

# Extract license/option IDs from the Keysight License Manager table
def extract_n90_license_manager_options(text, device_model=None):

    normalized_text = normalize_pdf_text(text)
    if not normalized_text:
        return []

    section_match = re.search(r"Keysight\s+License\s+Manager" r"(.*?)" r"firmware\s+Information", normalized_text, flags=re.IGNORECASE | re.DOTALL)

    if not section_match:
        return []

    license_section = section_match.group(1)
    model = str(device_model or "").strip().upper()
    cleaned_options = []

    for raw_line in license_section.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        model_specific_match = None
        if model:
            model_specific_match = re.fullmatch(rf"{re.escape(model)}-[A-Z0-9]+", line, flags=re.IGNORECASE)
        general_match = re.fullmatch(r"(?:" r"N\d{4}[A-Z]{0,2}\d*[A-Z]*(?:-[A-Z0-9]+)?" r"|N90[A-Z0-9_]+(?:-[A-Z0-9]+)?" r"|U\d+[A-Z0-9_]+(?:-[A-Z0-9]+)?" r")", line, flags=re.IGNORECASE)

        if not model_specific_match and not general_match:
            continue

        option_id = clean_n90_option_id(line, device_model)

        if option_id and option_id not in cleaned_options:
            cleaned_options.append(option_id)

    return cleaned_options

# Existing option extraction for E506x devices.
def extract_e506x_options(text):

    flat_text = re.sub(r"\s+", " ", text)
    options_section_match = re.search(r"Option\s+ID.*?Option\s+Version" r"(.*?)" r"firmware\s+Information", flat_text, re.IGNORECASE | re.DOTALL)

    if not options_section_match:
        return "Unknown"

    options_section = options_section_match.group(1)
    option_codes = re.findall(r"(?:^|\s)" r"([A-Z0-9]{3})" r"(?=\s+(?:LF-RF|High|Standard|GPIB|Handler|Impedance))", options_section, re.IGNORECASE)
    excluded_options = {"FOR", "AND", "THE", "NOT", "VNA", "GPI", "GPIB", "PORT", "TEST", "SET", "GAIN", "HIGH", "LOW", "BIAS"}
    option_codes = [code.upper() for code in option_codes if code.upper() not in excluded_options ]

    option_codes = list(dict.fromkeys(option_codes))

    if not option_codes:
        return "Unknown"

    return "; ".join(option_codes)

# Extract N90 options from both: System Information & License Manager
def extract_n90_options_from_pdf_text(text, device_model):

    system_options = extract_n90_system_information_options( text=text, device_model=device_model)

    license_options = extract_n90_license_manager_options(text=text, device_model=device_model)

    all_options = merge_unique_options(system_options, license_options)

    if not all_options:
        return "Unknown"

    return "; ".join(all_options)

# Merge option lists while preserving order and removing duplicates.
def merge_unique_options(*option_lists):

    merged_options = []
    for option_list in option_lists:

        if not option_list:
            continue

        for option in option_list:
            if option and option not in merged_options:
                merged_options.append(option)

    return merged_options

# Clean one N90 option ID.
def clean_n90_option_id(option_id, device_model):

    if not option_id:
        return None

    option_id = re.sub(r"\s+","",str(option_id)).upper()

    excluded_words = {"NONE", "FIXED", "UNLIMITED", "LOCAL", "FEATURE", "DESCRIPTION", "VERSION", "LICENSE", "NUMBER", "EXPIRATION", "TYPE", "COUNT", "LOCATION", "OPTION", "ID", "NAME"}

    if option_id in excluded_words:
        return None

    model = str(device_model or "").strip().upper()

    if model:
        model_prefix = model + "-"
        if option_id.startswith(model_prefix):
            option_id = option_id[len(model_prefix):]

    if not option_id:
        return None

    return option_id

# Normalize text extracted from a PDF.
def normalize_pdf_text(text):

    if not text:
        return ""

    text = (text.replace("\r\n", "\n").replace("\r", "\n").replace("\u200b", "").replace("\ufeff", "").replace("￾", "-"))
    text = re.sub(r"([A-Z0-9_]+-)\s*\n\s*([A-Z0-9]+)",r"\1\2", text, flags=re.IGNORECASE)
    return text

#  Extract device options according to the device family.
def extract_device_options(text, device_model):

    model = str(device_model or "").strip().upper()
    if model.startswith("N90"):
        return extract_n90_options_from_pdf_text(text=text, device_model=model)

    if re.fullmatch(r"E506\d[A-Z]?", model):
        return extract_e506x_options(text)

    return "Unknown"

"""def format_email_value(value, fallback="Not available in report"):
    if value is None:
        return fallback

    value = str(value).strip()

    if not value or value.lower() == "unknown":
        return fallback

    return value"""

def get_n90_email_images(serial_number):

    screenshot_path = load_configFile("screenShot_path")
    screenshot_root = Path(screenshot_path)
    valid_extensions = {".png", ".jpg", ".jpeg"}

    system_images = load_images(screenshot_root, serial_number, "System", valid_extensions)
    license_images = load_images(screenshot_root, serial_number,"License", valid_extensions)

    print("System images:")
    for image in system_images:
        print("   ", image)

    print("License images:")
    for image in license_images:
        print("   ", image)

    return system_images, license_images

def load_images(screenshot_root, serial_number, folder_name, valid_extensions):

    folder = (screenshot_root / serial_number / folder_name)

    if not folder.exists():
        print(f"Folder not found: {folder}")
        return []

    return sorted(
        [
            file
            for file in folder.iterdir()
            if file.is_file()
            and file.suffix.lower() in valid_extensions
        ]
    )

def get_n90_email_images(serial_number):

    screenshot_path = load_configFile("screenShot_path")
    base_path = Path(screenshot_path)
    device_folder = base_path / serial_number
    license_folder = device_folder / "License"
    system_folder = device_folder / "System"
    valid_extensions = {".png", ".jpg", ".jpeg"}
    license_images = []
    system_images = []
    if license_folder.exists():
        license_images = sorted(
            [
                str(file)
                for file in license_folder.iterdir()
                if file.is_file()
                and file.suffix.lower() in valid_extensions
            ]
        )
    if system_folder.exists():
        system_images = sorted(
            [
                str(file)
                for file in system_folder.iterdir()
                if file.is_file()
                and file.suffix.lower() in valid_extensions
            ]
        )

    print("System images:")
    for image in system_images:
        print("   ", image)

    print("License images:")
    for image in license_images:
        print("   ", image)

    return system_images, license_images


def add_inline_images(mail, image_paths, cid_prefix):

    for index, image_path in enumerate(image_paths, start=1):
        image_path = Path(image_path)

        if not image_path.is_file():

            print(f"Image not found: " f"{image_path}")
            continue

        attachment = (mail.Attachments.Add(str(image_path.resolve())))
        cid = (f"{cid_prefix}_{index}")

        # Content-ID
        attachment.PropertyAccessor.SetProperty("http://schemas.microsoft.com/mapi/proptag/0x3712001F", cid)
        mime_type, _ = (mimetypes.guess_type( str(image_path)))

        if not mime_type:
            mime_type = "image/png"

        attachment.PropertyAccessor.SetProperty("http://schemas.microsoft.com/mapi/proptag/0x370E001F", mime_type)


def main():

    recipients = [
         "Benny.a@tlv-mm.com"
    ]

    device_name = "N9041B"
    device_type = "Signal Analyzer"
    slot = "SLOT1"
    ip = "192.168.1.100"
    final_status = "PASS"
    pdf_file = r"C:\Users\benny\Documents\PycharmProjects\InterlligentTester\Results\MY57103319\MY57103319.pdf"

    pdf_info = extract_device_info_from_pdf(pdf_file)

    for key, value in pdf_info.items():
        print(f"{key}: {value}")

    reader = PdfReader(pdf_file)

    pdf_text = ""

    for page in reader.pages:
        page_text = page.extract_text() or ""
        pdf_text += page_text + "\n"

    debug_file = os.path.splitext(pdf_file)[0] + "_PDF_TEXT.txt"

    with open(debug_file, "w", encoding="utf-8") as file:
        file.write(pdf_text)

    print(f"PDF text saved to: {debug_file}")

    """print("Sending START email...")
    send_test_ended_email(
        recipients,
        device_name,
        device_type,
        slot,
        ip,
        final_status,
        pdf_file,
        is_new_device=True
    )"""

    input("Press ENTER to send END email...")

    print("Sending END email...")
    extra_data = [" CurrentPhysics_5012.bkz", "25/01/2026 11:54"]
    send_test_ended_email(recipients, device_name, device_type, slot, ip, "PASSED", pdf_file, extra_data, True)

    print("Done.")


if __name__ == "__main__":
    main()