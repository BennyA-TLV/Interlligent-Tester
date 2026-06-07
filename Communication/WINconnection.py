from typing import Any

from PIL import Image, ImageChops, ImageStat
from Communication.Connection import *
from pathlib import Path
import subprocess
import shutil
import datetime
import base64
import winrm
import time
import sys
import os
import re

exe_path = r"C:\Program Files\Keysight\SignalAnalysis\Infrastructure\LaunchXSA.exe"
guide = Path.cwd().parent.parent

# Created by Benny Aberman - 054-3220104
# Windows connection functions
    # The init function
    # The setup for the local computer function
    # The connection function
    # The check Windows updates function
    # The log file function
    # The install Windows updates function
    # The reboot function
    # The main Windows updates function
    # The open the license manger function
    # The scroll license manger function
    # The any key function
    # The copy file function
    # The running the BAT file function
    # The check OS function
    # The minimize windows function
    # The active session ID function
    # The screenshot function
    # The last page function
    # The screenshot all licenses pages function
    # The screenshot all system information pages function


class WINconn:
    # The init function that contains all the parameters of the class.
    def __init__(self, target_ip, username, password):
        self.target_ip = target_ip
        self.username = username
        self.password = password
        self.session = None

    # The setup for the local computer function - operat the local computer to enable connection to the remote device
    def setup_local_machine(self):
        print(f"--- Starting Local Setup for {self.target_ip} ---")

        commands = [
            ('Starting WinRM Service', 'Set-Service WinRM -StartupType Automatic; Start-Service WinRM'),
            ('Configuring TrustedHosts', f'Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "{self.target_ip}" -Force'),
            ('Enabling CredSSP Client', f'Enable-WSManCredSSP -Role Client -DelegateComputer "{self.target_ip}" -Force'),
            ('Testing Port 5985', f'Test-NetConnection -ComputerName {self.target_ip} -Port 5985')
        ]

        for description, cmd in commands:
            print(f"[Task: {description}]")
            try:
                subprocess.run(["powershell", "-Command", cmd], check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except subprocess.CalledProcessError as e:
                print(f"Error: {e.stderr.strip()}")

    # The connection function - to the remote device
    def connect(self):
        try:
            self.session = winrm.Session(
                self.target_ip,
                auth=(self.username, self.password),
                transport='credssp',
                server_cert_validation='ignore'
            )
            result = self.session.run_cmd('hostname')
            print(f"--- Connection established to {self.target_ip} using CredSSP ---")
            return True
        except Exception as e:
            print(f"Connection Failed: {e}")
            self.session = None
            return False

    # The check Windows updates function - operat no the remote device getting the KB list in 180 second
    def check_updates(self):
        if not self.session:
            self.connect()

        run_id = int(time.time())
        temp_file = f"C:\\Windows\\Temp\\upd_check_{run_id}.txt"

        ps_script = f"""
        try {{
            $final_list = @()
            $timestamp = Get-Date -Format "HH:mm:ss"
            $final_list += "=== File updated at: $timestamp ==="
            $isWin10 = [Environment]::OSVersion.Version.Major -ge 10

            if ($isWin10) {{
                # Windows 10/11
                usoclient StartScan
                Start-Sleep -Seconds 5
            }} else {{
                # Windows 7
                wuauclt /detectnow
                Start-Sleep -Seconds 5
            }}

            $session = New-Object -ComObject Microsoft.Update.Session
            $searcher = $session.CreateUpdateSearcher()
            $searcher.Online = $false 

            $result = $searcher.Search("IsInstalled=0")

            $final_list = @()
            foreach ($u in $result.Updates) {{
                $title = $u.Title
                $kb = ""

                if ($u.KBArticleIDs.Count -gt 0) {{
                    $kb = "KB" + ($u.KBArticleIDs -join ",KB")
                }} 
                elseif ($title -match 'KB(\\d+)') {{
                    $kb = "KB" + $matches
                }}

                if ($kb -ne "") {{
                    $final_list += "$kb | $title"
                }}
            }}

            if ($final_list.Count -gt 0) {{
                $final_list | Sort-Object -Unique | Out-File -FilePath "{temp_file}" -Force -Encoding UTF8
            }} else {{
                "SUCCESS: No KB updates found (Checked at $timestamp)"  | Out-File -FilePath "{temp_file}" -Force -Encoding UTF8
            }}
        }} catch {{
            $_.Exception.Message | Out-File -FilePath "{temp_file}" -Force -Encoding UTF8
        }}
        """

        print(" > Checking for all missing KB updates...")
        print(" > Waiting for 180 sec for Update Status......")
        self.session.run_ps(ps_script)

        timeout = 180
        elapsed = 0
        content = ""

        try:
            while elapsed < timeout:
                check = self.session.run_ps(f"if (Test-Path '{temp_file}') {{ Get-Content '{temp_file}' -Raw }}")
                content = check.std_out.decode('utf-8', errors='ignore').strip()

                if content:
                    break

                time.sleep(1)
                elapsed += 1

        finally:
            self.session.run_ps(f"if (Test-Path '{temp_file}') {{ Remove-Item '{temp_file}' -Force }}")

        return content if content else "SUCCESS: No KB updates found."

    # The log file function - operat no the local computer, writing the update/install and reboot process
    """def log_local(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        with open("update_history.log", "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f" > Local Log: {message}")"""

    # The install Windows updates function - operat no the remote device in 5400 second
    def install_updates(self, kb_list):
        if not self.session: self.connect()

        kb_numbers = list(set(re.findall(r'\b\d{5,}\b', kb_list)))
        if not kb_numbers:
            kb_numbers = list(set(re.findall(r'KB(\d{5,})', kb_list)))
        if not kb_numbers:
            #self.log_local("No KBs found in input.")
            return "No KBs found. - Windows is Updated!"

        kb_query = ",".join([f"'{k}'" for k in kb_numbers])
        run_id = int(time.time())
        script_path = f"C:\\upd_{run_id}.ps1"
        temp_file = f"C:\\res_{run_id}.txt"
        task_name = f"UpdInst_{run_id}"

        #self.log_local(f"Starting installation for KBs: {', '.join(kb_numbers)}")

        ps_template = r"""
        try {
            $targets = @(REPLACE_KBS)
            $session = New-Object -ComObject Microsoft.Update.Session
            $searcher = $session.CreateUpdateSearcher()
            $all = $searcher.Search("IsInstalled=0").Updates
            $found = New-Object -ComObject Microsoft.Update.UpdateColl
            foreach($u in $all) {
                $id = $u.KBArticleIDs -join ""
                foreach($t in $targets) {
                    if($id -match $t -or $u.Title -match $t) { $found.Add($u); break }
                }
            }
            if ($found.Count -gt 0) {
                "START: Found $($found.Count) updates" | Out-File "REPLACE_PATH" -Force
                $downloader = $session.CreateUpdateDownloader(); $downloader.Updates = $found; $downloader.Download() | Out-Null
                $installer = $session.CreateUpdateInstaller(); $installer.Updates = $found; $res = $installer.Install()
                "DONE: ResultCode=$($res.ResultCode) RebootRequired=$($res.RebootRequired)" | Out-File "REPLACE_PATH" -Append
            } else { "EMPTY" | Out-File "REPLACE_PATH" -Force }
        } catch { "ERROR: $($_.Exception.Message)" | Out-File "REPLACE_PATH" -Force }
        """
        full_ps_content = ps_template.replace("REPLACE_KBS", kb_query).replace("REPLACE_PATH", temp_file)

        self.session.run_ps(f"New-Item -Path '{script_path}' -ItemType File -Force")
        for line in full_ps_content.strip().split('\n'):
            if line.strip():
                enc_line = base64.b64encode(line.strip().encode('utf-8')).decode('utf-8')
                write_cmd = f"$txt = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{enc_line}')); $txt | Out-File -FilePath '{script_path}' -Append -Encoding UTF8"
                self.session.run_ps(write_cmd)

        reg_cmd = (
            f'$a = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File {script_path}"; '
            f'$p = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest; '
            f'Register-ScheduledTask -TaskName "{task_name}" -Action $a -Principal $p -Force | Out-Null; '
            f'Start-ScheduledTask -TaskName "{task_name}"'
        )
        self.session.run_ps(reg_cmd)

        #An hour and a half for updates
        timeout, elapsed = 5400, 0
        final_result = "Timeout"

        try:
            while elapsed < timeout:
                check = self.session.run_ps(f"if (Test-Path '{temp_file}') {{ Get-Content '{temp_file}' -Raw }}")
                res = check.std_out.decode('utf-8', errors='ignore').strip()

                if res and ("DONE:" in res or "EMPTY:" in res or "ERROR:" in res):
                    final_result = res
                    break
                if hasattr(sys, "stdout") and sys.stdout:
                    sys.stdout.write(f"\r > Installing... {elapsed}s/{timeout}s")
                    sys.stdout.flush()
                else:
                    pass
                    #self.log_local(f"\r > Installing... {elapsed}s/{timeout}s")
                time.sleep(10)
                elapsed += 10
            else:
                #self.log_local("Timeout reached. Checking Registry for RebootRequired flag...")
                reg_check = self.session.run_ps(
                    "Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired'")
                if "True" in reg_check.std_out.decode():
                    final_result = "DONE: Timeout but RebootRequired=True (Found in Registry)"
                else:
                    final_result = "ERROR: Timeout without Reboot flag"

        finally:
            self.session.run_ps(
                f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false; rm '{script_path}', '{temp_file}' -Force -ErrorAction SilentlyContinue")
        print("\n")
        #self.log_local(f"Installation Result: {final_result}")

        if "RebootRequired=True" in final_result:
            #self.log_local("Reboot required. Initiating reboot now...")
            reboot_res = self.reboot_device()
            #self.log_local(f"Reboot process status: {reboot_res}")
        else:
            pass
            #self.log_local("No reboot required for these updates.")

        return final_result

    # The reboot function - operat no the remote device if reboot is needed
    def reboot_device(self):
        if not self.session: self.connect()

        run_id = int(time.time())
        task_name = f"RebootTask_{run_id}"

        print("\n > Creating Remote Reboot Task...")

        reboot_cmd = (
            f'$a = New-ScheduledTaskAction -Execute "shutdown.exe" -Argument "/r /f /t 5 /c ""Reboot by Automation"""; '
            f'$p = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest; '
            f'Register-ScheduledTask -TaskName "{task_name}" -Action $a -Principal $p -Force | Out-Null; '
            f'Start-ScheduledTask -TaskName "{task_name}"'
        )

        try:
            self.session.run_ps(reboot_cmd)
            print(" > Reboot command sent via Scheduled Task.")
        except Exception as e:
            print(f" > Note: Session disconnected as expected ({str(e)})")

        self.session = None

        print(" > Waiting for server to go down and come back up...")
        time.sleep(90)

        timeout, elapsed = 1200, 90
        while elapsed < timeout:
            try:
                self.setup_local_machine()
                self.connect()
                if self.session:
                    test = self.session.run_ps("hostname")
                    if test.std_out:
                        print(f"\n > Server is back online! (Hostname: {test.std_out.decode().strip()})")
                        print(f"\n > The Device is updating please wait... ")
                        self.session.run_ps(f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false")
                        return "Reboot Success"
            except:
                self.session = None

            if hasattr(sys, "stdout") and sys.stdout:
                sys.stdout.write(f"\r > Reconnecting... {elapsed}s/{timeout}s")
                sys.stdout.flush()
            else:
                pass
                #self.log_local(f"\r > Reconnecting... {elapsed}s/{timeout}s")
            time.sleep(20)
            elapsed += 20

        return "Error: Reboot Timeout. Server might be installing updates on boot."

    # The main Windows updates function - operat no the remote device for all check/install and reboot process
    def main_update_process(self, results_list, worker = None, logger = None, auto_reboot=False):
        external_results = []
        text_table = create_text_table(title="Windows Updates")
        print("--- Starting Automation: Windows Updates ---")
        report_step("Starting Automation: Windows Updates", "INFO", 76, results_list, "Starting Automation: Windows Updates", None, worker, logger)

        print(" > Step 1: Scanning for available updates...")
        available_updates = self.check_updates()
        report_step("Scanning for available updates", "INFO", 80, results_list, "Step 1", None, worker, logger)
        add_text_row(text_table, available_updates)

        if "No KB updates found" in available_updates or not available_updates:
            print(" > Result: System is up to date. Nothing to do.")
            report_step("System is up to date. Nothing to do.", "INFO", 90, results_list, "Step 2", None, worker, logger)
            add_text_row(text_table, "System is up to date. Nothing to do.")
            external_results.append(text_table)
            return "System Up-to-date", external_results

        print(f"\nResult: Updates found!\n{available_updates}")

        print("\n > Step 2: Starting installation (this might take a while)...")
        report_step("Starting installation (this might take a while)... 1:30 min", "INFO", 81, results_list, "Step 2", None, worker, logger)
        install_result = self.install_updates(available_updates)

        #print(f"\n > Installation Summary:\n{install_result}")
        if "DONE:" in install_result:
            match = re.search(r'ResultCode=(\d+)', install_result)
            if match:
                result_code = match.group(1)

                if result_code == "2":
                    #self.log_local("\n > Installation Summary:\nSUCCESS: All updates installed successfully.")
                    report_step("Installation Done", "INFO", 90, results_list, "Step 2", None, worker, logger)
                    add_text_row(text_table, "Installation SUCCESS")
                elif result_code == "3":
                    #self.log_local("\n > Installation Summary:\nPARTIAL SUCCESS: Some updates were installed, but others encountered minor issues.")
                    report_step("Installation PARTIAL SUCCESS", "INFO", 90, results_list, "Step 2", None, worker, logger)
                    add_text_row(text_table, "Installation PARTIAL SUCCESS")
                elif result_code == "4":
                    #self.log_local("\n > Installation Summary:\nFAILURE: The update installation failed.")
                    report_step("Installation FAILURE", "INFO", 90, results_list, "Step 2", None, worker, logger)
                    add_text_row(text_table, "Installation FAILURE")
                else:
                    #self.log_local(f"INFO: Installation finished with ResultCode: {result_code}")
                    report_step("Installation FAILURE", "INFO", 90, results_list, "Step 2", None, worker, logger)
                    add_text_row(text_table, "Installation FAILURE")
                    # Checking for Reboot flag
                if "RebootRequired=True" in install_result:
                    #self.log_local("REBOOT REQUIRED: The system needs a restart to complete the installation.")
                    report_step("The system needs a restart to complete the installation", "INFO", 95, results_list, "Step 3", None, worker, logger)
                    add_text_row(text_table, "The system needs a restart to complete the installation")
                else:
                    #self.log_local("NO REBOOT: System does not require a restart at this time.")
                    report_step("NO REBOOT: System does not require a restart at this time", "INFO", 95, results_list,"Step 3", None, worker, logger)
                    add_text_row(text_table, "NO REBOOT: System does not require a restart at this time")

            elif "EMPTY" in install_result:
                #self.log_local("SKIPPED: None of the requested KBs were found or needed.")
                report_step("SKIPPED: None of the requested KBs were found or needed", "INFO", 95, results_list,"Step 3", None, worker, logger)
                add_text_row(text_table, "SKIPPED: None of the requested KBs were found or needed")

            elif "ERROR:" in install_result:
                #self.log_local(f"CRITICAL: An error occurred during the update process: {install_result}")
                report_step("CRITICAL: An error occurred during the update process", "INFO", 95, results_list,install_result, None, worker, logger)
                add_text_row(text_table, "CRITICAL: An error occurred during the update process")

        if "RebootRequired: True" in install_result:
            print("\n > Step 3: Reboot is required to complete installation.")
            if auto_reboot:
                reboot_status = self.reboot_device()
                print(f" > {reboot_status}")
            else:
                print(" > Reboot skipped by user. Remember to manual reboot later.")
                report_step("Reboot skipped by user. Remember to manual reboot later", "INFO", 95, results_list,"Step 3", None, worker, logger)
                add_text_row(text_table, "Reboot skipped by user. Remember to manual reboot later")
        else:
            print("\n > Step 3: No reboot required. Process finished.")
            report_step("Step 3: No reboot required. Process finished.", "INFO", 95, results_list, "Step 3",None, worker, logger)
            add_text_row(text_table, "Step 3: No reboot required. Process finished.")
        external_results.append(text_table)
        print("\n--- Automation Completed ---")
        return "--- Automation Completed ---", external_results


    # The open the license manger function - operat no the remote device opening the license manger
    def open_license_manager(self):
        if not self.session: self.connect()

        check_user = self.session.run_ps("(Get-CimInstance Win32_ComputerSystem).UserName")
        current_user = check_user.std_out.decode().strip()

        if not current_user:
            return "Error: No active user session found."

        task_name = f"LicOpen_{int(time.time())}"
        remote_exe = r"C:\Program Files (x86)\Agilent\Agilent License Manager\KeysightLicenseManager.exe"

        inner_ps = (
            f"Stop-Process -Name 'KeysightLicenseManager' -Force -ErrorAction SilentlyContinue; "
            f"Start-Process '{remote_exe}'; "
            f"Start-Sleep -Seconds 3; "
            f"$w = New-Object -ComObject WScript.Shell; "
            f"if($w.AppActivate('Keysight License Manager')) {{ $w.SendKeys('%') }}"
        )
        encoded_payload = base64.b64encode(inner_ps.encode('utf-16-le')).decode('utf-8')

        reg_cmd = (
            f'$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_payload}"; '
            f'Register-ScheduledTask -TaskName "{task_name}" -Action $action -User "{current_user}" -RunLevel Highest -Force | Out-Null; '
            f'Start-ScheduledTask -TaskName "{task_name}"'
        )

        print(f" > Launching License Manager for {current_user}...")
        self.session.run_ps(reg_cmd)

        time.sleep(10)
        self.session.run_ps(f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false -ErrorAction SilentlyContinue")

        return f"Task triggered for {current_user}"

    # The scroll license manger function - operat no the remote device scrolling the license manger table down
    def scroll_license_list(self, steps=12):
        if not self.session: self.connect()

        check_user = self.session.run_ps("(Get-CimInstance Win32_ComputerSystem).UserName")
        current_user = check_user.std_out.decode().strip()

        if not current_user: return "Error: No user found."

        task_name = f"ScrollGrid_{int(time.time())}"

        tab_sequence = "{TAB}" * 4
        down_sequence = "{DOWN}" * steps
        full_keys = f"{tab_sequence}{down_sequence}"

        inner_ps = (
            f"$w = New-Object -ComObject WScript.Shell; "
            f"if($w.AppActivate('Keysight License Manager')) {{ "
            f"  Start-Sleep -Milliseconds 800; "
            f"  $w.SendKeys('{full_keys}'); "
            f"}}"
        )
        encoded_payload = base64.b64encode(inner_ps.encode('utf-16-le')).decode('utf-8')

        reg_cmd = (
            f'$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_payload}"; '
            f'Register-ScheduledTask -TaskName "{task_name}" -Action $action -User "{current_user}" -RunLevel Highest -Force | Out-Null; '
            f'Start-ScheduledTask -TaskName "{task_name}"'
        )

        print(f" > Navigating to grid and scrolling down {steps} steps...")
        self.session.run_ps(reg_cmd)

        time.sleep(4)
        self.session.run_ps(
            f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false -ErrorAction SilentlyContinue")

        return "Navigation and scroll triggered."

    # The any key function - operat no the remote device pressing any key on the keyboard
    def press_key_remote(self, direction='DOWN', steps=20):
        if not self.session: self.connect()

        check_user = self.session.run_ps("(Get-CimInstance Win32_ComputerSystem).UserName")
        current_user = check_user.std_out.decode().strip()
        if not current_user: return "Error: No user found."

        key_to_send = f"{{{direction.upper()}}}"
        task_name = f"SilentKey_{direction}_{int(time.time())}"

        inner_ps = (
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"Start-Sleep -Milliseconds 500; "
            f"for ($i=0; $i -lt {steps}; $i++) {{ "
            f"    [System.Windows.Forms.SendKeys]::SendWait('{key_to_send}'); "
            f"    Start-Sleep -Milliseconds 150; "
            f"}}"
        )

        encoded_payload = base64.b64encode(inner_ps.encode('utf-16-le')).decode('utf-8')

        silent_wrapper = (
            f'$cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_payload}"; '
            f'$w = New-Object -ComObject WScript.Shell; '
            f'$w.Run($cmd, 0, $false)'
        )

        wrapper_payload = base64.b64encode(silent_wrapper.encode('utf-16-le')).decode('utf-8')

        reg_cmd = (
            f'$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -EncodedCommand {wrapper_payload}"; '
            f'Register-ScheduledTask -TaskName "{task_name}" -Action $action -User "{current_user}" -RunLevel Highest -Force | Out-Null; '
            f'Start-ScheduledTask -TaskName "{task_name}"'
        )

        self.session.run_ps(reg_cmd)

        time.sleep(2 + (steps * 0.3))
        self.session.run_ps(
            f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false -ErrorAction SilentlyContinue")

        return f"Sent {steps} {direction} keys."

    # The copy file function - operat no the remote device
    def copy_file_to_remote(self, target_ip, user, password, source_file, file_name, model = None, destination_file = r"D$\Users\InterlligentTester"):

        remote_folder = Path(rf"\\{target_ip}\{destination_file}")
        destination = remote_folder / file_name
        if model:
            source = Path(source_file, model) / file_name
        else:
            source = Path(source_file) / file_name
        share_name = destination_file.split("\\")[0]

        try:
            print(f"Connecting to {target_ip}...")
            auth_cmd = rf'net use \\{target_ip}\{share_name} {password} /user:{user} /persistent:no'
            subprocess.run(auth_cmd, shell=True, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

            if not remote_folder.exists():
                print(f"Creating directory: {remote_folder}")
                remote_folder.mkdir(parents=True, exist_ok=True)

            found_files = [f.name for f in remote_folder.iterdir() if f.is_file() and file_name.lower() in f.name.lower()]

            if found_files:
                print(f"Found file in remote folder: {found_files[0]} - no need to copy")
                return False

            if not source.exists():
                print(f"Source file not found: {source}")
                return False

            print("Copying file...")
            shutil.copy2(source, destination)
            print(f"Successfully copied to {destination}")
            return True

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('cp1255', errors='ignore') if e.stderr else str(e)
            print(f"Connection failed: {error_msg}")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False
        finally:
            share_name = destination_file.split("\\")[0]
            subprocess.run(rf'net use \\{target_ip}\{share_name} /delete /y', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    # The running the BAT file function - operat no the remote device getting BAt file running so the local can take control
    def run_bat_file(self, bat_path=r"D:\Users\InterlligentTester\InterlligentTester.bat"):

        if not self.session: self.connect()

        run_id = int(time.time())
        task_name = f"VisibleBat_{run_id}"

        get_user = self.session.run_ps("(Get-CimInstance Win32_ComputerSystem).UserName")
        current_user = get_user.std_out.decode().strip()

        if not current_user:
            return f"Error: No user \"{current_user}\" is currently logged in to a visible session."

        print(f" > Opening BAT for user: {current_user}")

        cmd = (
            f'$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c start cmd.exe /k ""{bat_path}"""; '
            f'Register-ScheduledTask -TaskName "{task_name}" -Action $action -User "{current_user}" -RunLevel Highest -Force | Out-Null; '
            f'Start-ScheduledTask -TaskName "{task_name}"'
        )

        self.session.run_ps(cmd)

        print("Waiting 40 second to running BAT file")
        time.sleep(40)
        self.session.run_ps(f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false")
        return f"BAT started visibly for {current_user}"

    # The check OS function - operat no the remote device
    def get_remote_os(self, ip, user, password):

        auth_cmd = f'net use \\\\{ip}\\C$ {password} /user:{user} /persistent:no'
        subprocess.run(auth_cmd, shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

        try:
            remote_file = rf"\\{ip}\C$\Windows\System32\ntoskrnl.exe"

            if not os.path.exists(remote_file):
                return "Could not access System32 (Check if XP share is enabled)"

            cmd = f'powershell -Command "(Get-Item \'{remote_file}\').VersionInfo.ProductVersion"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            v = result.stdout.strip()

            if v.startswith("10.0.2"): return "Windows 11"
            if v.startswith("10.0"):   return "Windows 10"
            if v.startswith("6.3"):    return "Windows 8.1"
            if v.startswith("6.2"):    return "Windows 8"
            if v.startswith("6.1"):    return "Windows 7"
            if v.startswith("6.0"):    return "Windows Vista"
            if v.startswith("5.2"):    return "Windows XP"
            if v.startswith("5.1"):    return "Windows XP"
            if v.startswith("5.0"):    return "Windows 2000"

            return f"Unknown Version ({v})"

        except Exception as e:
            return f"Error: {e}"
        finally:
            subprocess.run(f'net use \\\\{ip}\\C$ /delete /y', shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

    # The minimize windows function - operat no the remote device
    def minimize_window(self):
        if not self.session: self.connect()

        check_user = self.session.run_ps("(Get-CimInstance Win32_ComputerSystem).UserName")
        current_user = check_user.std_out.decode().strip()

        if not current_user:
            return "Error: No active user session found."

        run_id = int(time.time())
        task_name = f"WinD_Task_{run_id}"

        ps_payload = "(New-Object -ComObject Shell.Application).ToggleDesktop()"
        cmd = (
            f'$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -Command {ps_payload}"; '
            f'Register-ScheduledTask -TaskName "{task_name}" -Action $action -User "{current_user}" -RunLevel Highest -Force | Out-Null; '
            f'Start-ScheduledTask -TaskName "{task_name}"'
        )

        print(f" > Sending MinimizeAll (Win+D) to {current_user}...")
        self.session.run_ps(cmd)

        time.sleep(2)
        self.session.run_ps(f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false")

        return f"Command sent to {current_user}"

    # The active session ID function - operat no the remote device getting ID so the commands will be on the right session
    def get_active_session_id(self):
        try:
            cmd = "query session | Select-String 'Active' | ForEach-Object { $_.ToString().Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)[2] }"
            response = self.session.run_ps(cmd)

            if hasattr(response, 'std_out'):
                raw_output = response.std_out.decode('utf-8')
            elif isinstance(response, (list, tuple)):
                raw_output = response[1].decode('utf-8') if isinstance(response[1], bytes) else str(response[1])
            else:
                raw_output = str(response)

            match = re.search(r'(\d+)', raw_output)
            if match:
                session_id = match.group(1).strip()
                print(f" > Found Session ID: {session_id}")
                return session_id

        except Exception as e:
            print(f" > Exception in get_active_session_id: {e}")

        return "1"

    # The screenshot function - operat no the remote device
    def screenshot(self, folder, serial_number, picture_name="License Manager", shot=1):
        if not self.session: self.connect()

        session_id = self.get_active_session_id()
        print(f" > Capturing on Active Session: {session_id}")

        run_id = int(time.time())
        remote_temp = "C:\\Windows\\Temp"
        remote_nircmd = f"{remote_temp}\\nircmd.exe"
        remote_image = f"{remote_temp}\\pure_{run_id}.png"
        screenshot_path = load_configFile("screenShot_path")

        base_path = Path(screenshot_path)
        local_dir = base_path / serial_number / folder
        local_dir.mkdir(parents=True, exist_ok=True)
        local_image = local_dir / f"{serial_number}_{picture_name}_{shot}.png"

        current_dir = os.path.dirname(os.path.abspath(__file__))
        psexec_path = os.path.join(current_dir, "psexec.exe")

        p_cmd = [
            psexec_path, "-accepteula", "-s", "-i", session_id,
            f"\\\\{self.target_ip}",
            "-u", self.username, "-p", self.password,
            "-d",
            remote_nircmd, "savescreenshot", remote_image
        ]

        subprocess.run(p_cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

        network_path = f"\\\\{self.target_ip}\\C$\\Windows\\Temp\\pure_{run_id}.png"
        found = False
        for _ in range(15):
            if os.path.exists(network_path) and os.path.getsize(network_path) > 0:
                found = True
                break
            time.sleep(1)

        if found:
            time.sleep(2)
            try:
                shutil.copy2(network_path, str(local_image))
                print(f" > SUCCESS! Saved to: {local_image}")
                self.session.run_ps(f"Remove-Item '{remote_image}' -Force")
                return str(local_image)
            except Exception as e:
                print(f" > Error copying file: {e}")
                return None
        else:
            print(" > Error: Screenshot resulted in black screen or file not found.")
            return None

    # The last page function - operat no the remote device checking if it is the lase page by scrolling
    def is_last_page(self, img_path1, img_path2):
        img1 = Image.open(img_path1).convert('RGB')
        img2 = Image.open(img_path2).convert('RGB')

        table_area = (75, 235, 750, 450)
        crop1 = img1.crop(table_area)
        crop2 = img2.crop(table_area)
        crop2.save("debug_current_crop.png")

        diff = ImageChops.difference(crop1, crop2)

        stat = ImageStat.Stat(diff)
        diff_score = sum(stat.mean) / len(stat.mean)

        threshold = 1.0

        if diff_score < threshold:
            return True
        else:
            return False

    # The screenshot all licenses pages function - operat no the remote device
    def capture_all_licenses(self, serial_number, results_list, worker, logger):
        all_captured = False
        page_count = 1
        steps = 21

        prev_img = self.screenshot("License", serial_number, "License Manager", page_count)
        report_step(name=f"License ScreenShot #N{page_count}", status="INFO", progress=40, results_list=results_list, value=f"License ScreenShot #N{page_count}", image_path=prev_img, worker=worker, logger=logger)


        while not all_captured:
            print(f" > Processing page {page_count}...")

            self.scroll_license_list(steps)
            print(" > Waiting 5 seconds to Image recovered .....")
            time.sleep(5)

            page_count += 1
            steps = 12
            curr_img = self.screenshot("License", serial_number, "License Manager", page_count)
            if self.is_last_page(prev_img, curr_img):
                print(" !!! Reached the end of the list (Images are identical).")
                if os.path.exists(curr_img):
                    os.remove(curr_img)
                all_captured = True
            else:
                prev_img = curr_img
                report_step(name=f"License ScreenShot #N{page_count}", status="INFO", progress=40,results_list=results_list, value=f"License ScreenShot #N{page_count}", image_path=curr_img,worker=worker, logger=logger)

        print("Done. All licenses captured.")

    # The screenshot all system information pages function - operat no the remote device
    def capture_all_systems(self, serial_number, results_list, worker, logger):
        all_captured = False
        page_count = 1
        steps = 20

        print(" > System Information All ScreenShots .....")
        self.press_key_remote("UP", 60)
        prev_img = self.screenshot("System", serial_number,"SYSTem", page_count)
        report_step(name=f"System Information ScreenShot #N{page_count}", status="INFO", progress=40, results_list=results_list, value=f"System Information ScreenShot #N{page_count}", image_path=prev_img, worker=worker, logger=logger)
        while not all_captured:
            print(f" > Processing page {page_count}...")

            print(f" > Moving list {steps} steps Down.....")
            self.press_key_remote("DOWN", steps)
            print(" > Waiting 5 seconds to Image recovered .....")
            time.sleep(5)

            page_count += 1
            curr_img = self.screenshot("System", serial_number, "SYSTem", page_count)

            if self.is_last_page(prev_img, curr_img):
                print(" !!! Reached the end of the list (Images are identical).")
                if os.path.exists(curr_img):
                    os.remove(curr_img)
                all_captured = True
            else:
                prev_img = curr_img
                report_step(name=f"System Information ScreenShot #N{page_count}", status="INFO", progress=40,results_list=results_list, value=f"System Information ScreenShot #N{page_count}", image_path=curr_img, worker=worker, logger=logger)

        print("Done. All system information captured.")


if __name__ == "__main__":

    target_ip = "192.168.1.200"
    user = "Administrator"
    password = "Keysight4u!"
    source = r'C:\Users\benny aberman\Documents\PycharmProjects\InterlligentTester'
    file_name = "InterlligentTester"

    updater = WINconn(target_ip, user, password)
    #updater.copy_to_remote(target_ip,user,password,source,file_name)
    #updater.setup_local_machine()
    #print(updater.run_bat_file())
    #updater.get_remote_os(target_ip,user,password)

    #results = updater.check_updates()
    #print("\n--- Update Results ---")
    #print(results)
    #print(updater.install_updates(results))
    #updater.reboot_device()
    #updater.main_update_process()
    #print(updater.run_bat_file())
    #print(updater.minimize_window())

    #history = updater.get_update_history(last=5)
    #print(history)

    #print(updater.open_license_manager())
    #updater.capture_all_licenses("MY57120121")
    #updater.press_key_remote()




