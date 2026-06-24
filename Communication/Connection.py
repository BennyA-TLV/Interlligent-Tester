import pandas as pd
from pathlib import Path
from email.message import EmailMessage
import subprocess
import csv
import tomllib
import smtplib
import time
import os
import sys
import logging
from datetime import datetime


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
        elif file_path.strip() == "bat_mircmd_path":
            return bat_mircmd_path
        elif file_path.strip() == "log_path":
            return log_path
        else:
            return None

    except FileNotFoundError:
        print(f"Error: The file {toml_path} was not found.")
    except KeyError as e:
        print(f"Error: Missing key in TOML file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# The get the url function - getting the url from the urls files
def get_urls(option, path_file):

    file_path = os.path.join(path_file, "url.csv")
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

    file_path = os.path.join(path_file, "option_descriptions.csv")
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exists in {file_path}")

    try:
        df = pd.read_csv(file_path, encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='ISO-8859-8')

    return [df[col].tolist() for col in df.columns]

# The find option descriptions function - finding the description in the option_descriptions.csv file
def find_option_descriptions(option_descriptions, option):

    for opt in range(len(option_descriptions[0])):
        if option.strip() == option_descriptions[0][opt].strip():
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

def send_test_started_email(recipients, device_type, slot, ip):
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

def send_test_ended_email(recipients, device_name, device_type, slot, ip, final_status, pdf_file):

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

sys.excepthook = handle_exception

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
    device_Model = "None"
    serial_number = "None"
    device_xsa = False
    start_time = time.time()

    while time.time() - start_time < timeout:

        try:
            if device.connect():
                idn = device.query("*IDN?")

                if idn:
                    print(f" > Instrument Ready: {idn}")
                    device_xsa = True
                    break

        except Exception:
            pass

        print(" > Waiting for XSA to finish loading...")
        report_step("Waiting for XSA to finish loading...", "INFO", 0, results_list, " ", None, worker, logger)
        time.sleep(30)

    if not device_xsa:
        print(" > Timeout waiting for XSA")
        return serial_number, device_Model, results_list

    else:
        if device.connect():
            report_step("Device is replaying", "PASS", 1, results_list, " ", None, worker, logger)
            device_Model = device.get_idn()[1]
            serial_number = device.get_idn()[2]
        else:
            report_step("Device isn't replaying", "FAIL", 1, results_list, " ", None, worker, logger)
        if check_progress(worker): return results_list

        device.disconnect()
        return  serial_number, device_Model, results_list

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
