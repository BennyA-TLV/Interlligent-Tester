from PIL import Image, ImageChops, ImageStat
from Communication.Connection import *
from pathlib import Path
import subprocess
import socket
import shutil
import base64
import winrm
import uuid
import time
import json
import sys
import os
import re

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
    # Set remote Windows to Auto Login as Administrator, reboot, reconnect, and verify active user


class WINconn:
    # The init function that contains all the parameters of the class.
    def __init__(self, target_ip, username, password):
        self.target_ip = target_ip
        self.username = username
        self.password = password
        self.session = None

    # The setup for the local computer function - operat the local computer to enable connection to the remote device
    def setup_local_machine(self, worker = None, logger = None):
        print(f"--- Starting Local Setup for {self.target_ip} ---")
        results_list = []

        commands = [
            ('Starting WinRM Service', 'Set-Service WinRM -StartupType Automatic; Start-Service WinRM'),
            ('Configuring TrustedHosts', f'Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "{self.target_ip}" -Force'),
            ('Enabling CredSSP Client', f'Enable-WSManCredSSP -Role Client -DelegateComputer "{self.target_ip}" -Force'),
            ('Testing Port 5985', f'Test-NetConnection -ComputerName {self.target_ip} -Port 5985')
        ]

        for description, cmd in commands:
            print(f"[Task: {description}]")
            report_step(f"[Task: {description}]", "INFO", 0, results_list, " ", None, worker, logger)

            try:
                subprocess.run(["powershell", "-Command", cmd], check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except subprocess.CalledProcessError as e:
                print(f"Error: {e.stderr.strip()}")

    # The connection function - to the remote device
    def connect(self):
        for transport in ["credssp", "ntlm"]:
            try:
                self.session = winrm.Session(
                    self.target_ip,
                    auth=(self.username, self.password),
                    transport=transport,
                    server_cert_validation='ignore'
                )

                result = self.session.run_cmd('hostname')

                print(f"--- Connection established to {self.target_ip} using {transport.upper()} ---")
                return True

            except Exception as e:
                print(f"Connection Failed using {transport.upper()}: {e}")
                self.session = None

        return False

    def disconnect(self):
        self.session = None

    def check_password(self, username, passwords):
        for password in passwords:
            print(f"Trying SMB login: {username} / {password}")

            cmd = rf'net use \\{self.target_ip}\C$ {password} /user:{username} /persistent:no'

            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            output = (result.stdout or "") + (result.stderr or "")

            subprocess.run(
                rf'net use \\{self.target_ip}\C$ /delete /y',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            if result.returncode == 0:
                print(f"Password found: {password}")
                self.username = username
                self.password = password
                return password

            if "System error 5" in output or "Access is denied" in output:
                print(f"Password is correct but user has no C$ admin access: {username} / {password}")
                return password

            print(output.strip())

        print(f"No {username} password worked")
        return None

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
    def install_updates(self, kb_list, results_list, worker = None, logger = None):
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
                    report_step(f"\r Installing... {elapsed}s/{timeout}s", "INFO", 81, results_list, "Step 2", None, worker, logger)
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
        install_result = self.install_updates(available_updates, external_results, worker, logger)

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
    def open_license_manager(self, timeout=90):
        if not self.session: self.connect()

        check_user = self.session.run_ps("(Get-CimInstance Win32_ComputerSystem).UserName")
        current_user = check_user.std_out.decode().strip()

        if not current_user:
            return False, "No active user session found."

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

        reg_cmd = f"""
        $user = "{current_user}"
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_payload}"
        $principal = New-ScheduledTaskPrincipal `
            -UserId $user `
            -LogonType Interactive `
            -RunLevel Highest
        $task = New-ScheduledTask `
            -Action $action `
            -Principal $principal
        Register-ScheduledTask `
            -TaskName "{task_name}" `
            -InputObject $task `
            -Force | Out-Null
        Start-ScheduledTask `
            -TaskName "{task_name}"
        """

        print(f" > Launching License Manager for {current_user}...")
        #self.session.run_ps(reg_cmd)
        #time.sleep(10)

        result = self.session.run_ps(reg_cmd)

        if result.status_code != 0:
            error = result.std_err.decode(errors="ignore").strip()
            return False, f"Failed to start scheduled task: {error}"

        try:
            ready, message = self.wait_for_license_manager_window(timeout=timeout)
            return ready, message
        finally:
            self.session.run_ps(f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false -ErrorAction SilentlyContinue")

        #return f"Task triggered for {current_user}"

    def wait_for_license_manager_window(self, timeout=120, poll_interval=2, stable_checks_required=3):

        if not self.session:
            self.connect()

        task_name = "CHECK_LICENSE_WINDOW"
        script_file = r"C:\Windows\Temp\check_license_window.ps1"
        result_file = r"C:\Windows\Temp\license_window.txt"
        result = self.session.run_ps("(Get-CimInstance Win32_ComputerSystem).UserName")
        current_user = result.std_out.decode(errors="ignore").strip()

        if not current_user:
            return False, "No interactive Windows user found."
        print(f" > Checking License Manager for {current_user}...")

        cleanup_ps = (
            f'Remove-Item "{result_file}" '
            f'-Force -ErrorAction SilentlyContinue; '
            f'Remove-Item "{script_file}" '
            f'-Force -ErrorAction SilentlyContinue; '
            f'Unregister-ScheduledTask '
            f'-TaskName "{task_name}" '
            f'-Confirm:$false '
            f'-ErrorAction SilentlyContinue'
        )

        self.session.run_ps(cleanup_ps)

        create_script_ps = rf"""
        $lines = @(
        '$ErrorActionPreference = "SilentlyContinue"'
        '$p = Get-Process -Name "KeysightLicenseManager" -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1'
        'if ($p) {{'
        '    $result = "FOUND|" + $p.Id + "|" + $p.SessionId + "|" + $p.MainWindowHandle.ToInt64() + "|" + $p.MainWindowTitle'
        '    Set-Content -Path "{result_file}" -Value $result -Encoding ASCII'
        '}} else {{'
        '    Set-Content -Path "{result_file}" -Value "NOT_FOUND" -Encoding ASCII'
        '}}'
        )
    
        Set-Content `
            -Path "{script_file}" `
            -Value $lines `
            -Encoding UTF8
        """

        result = self.session.run_ps(create_script_ps)
        error = result.std_err.decode( errors="ignore").strip()

        if (error and "CLIXML" not in error and "Preparing modules" not in error):
            print(f" > Error creating check script: {error}")

        result = self.session.run_ps(
            rf"""
        if (Test-Path "{script_file}")
        {{
            Write-Output "OK"
        }}
        else
        {{
            Write-Output "FAILED"
        }}
        """
        )

        script_status = result.std_out.decode(errors="ignore").strip()
        if script_status != "OK":
            print(" > Failed to create remote PowerShell script.")
            return False, ("Could not create License Manager check script.")
        print(" > Remote window check script created.")

        create_task_ps = rf"""
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{script_file}"'
    
        $principal = New-ScheduledTaskPrincipal `
            -UserId "{current_user}" `
            -LogonType Interactive `
            -RunLevel Highest
    
        $settings = New-ScheduledTaskSettingsSet `
            -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
    
        Register-ScheduledTask `
            -TaskName "{task_name}" `
            -Action $action `
            -Principal $principal `
            -Settings $settings `
            -Force | Out-Null
        """

        result = self.session.run_ps(create_task_ps)
        create_error = result.std_err.decode(errors="ignore").strip()
        result = self.session.run_ps(
            rf"""
        if (Get-ScheduledTask `
                -TaskName "{task_name}" `
                -ErrorAction SilentlyContinue)
        {{
            Write-Output "OK"
        }}
        else
        {{
            Write-Output "FAILED"
        }}
        """
        )

        task_status = result.std_out.decode(errors="ignore").strip()
        if task_status != "OK":
            print(" > Failed to create interactive check task.")
            if create_error:
                print(f" > Error: {create_error}")
            return False, ("Could not create License Manager " "window check task.")

        print(" > Interactive check task created.")
        start_time = time.time()
        stable_checks = 0
        previous_signature = None

        try:
            while time.time() - start_time < timeout:
                self.session.run_ps(
                    f'Remove-Item "{result_file}" '
                    f'-Force -ErrorAction SilentlyContinue'
                )
                start_result = self.session.run_ps(
                    f'Start-ScheduledTask '
                    f'-TaskName "{task_name}"'
                )

                start_error = start_result.std_err.decode(errors="ignore").strip()
                if (start_error and "CLIXML" not in start_error and "Preparing modules" not in start_error):
                    print(f" > Start task error: {start_error}")

                output = ""

                for _ in range(20):
                    time.sleep(0.5)

                    result = self.session.run_ps(
                        rf"""
                    if (Test-Path "{result_file}")
                    {{
                        Get-Content "{result_file}" -Raw
                    }}
                    """
                    )

                    output = result.std_out.decode(errors="ignore").strip()
                    if output:
                        break
                if not output:
                    print(" > Waiting for interactive window check...")

                    task_info = self.session.run_ps(
                        rf"""
                    $t = Get-ScheduledTask `
                        -TaskName "{task_name}" `
                        -ErrorAction SilentlyContinue
                
                    $i = Get-ScheduledTaskInfo `
                        -TaskName "{task_name}" `
                        -ErrorAction SilentlyContinue
                
                    if ($t -and $i)
                    {{
                        Write-Output (
                            "State=" +
                            $t.State +
                            ";LastResult=" +
                            $i.LastTaskResult
                        )
                    }}
                    """
                    )

                    task_output = task_info.std_out.decode(errors="ignore").strip()
                    if task_output:
                        print(f" > Task status: {task_output}")
                    stable_checks = 0
                    previous_signature = None
                    time.sleep(poll_interval)
                    continue

                if output == "NOT_FOUND":
                    print(" > Waiting for License Manager window...")
                    stable_checks = 0
                    previous_signature = None
                    time.sleep(poll_interval)
                    continue

                if not output.startswith("FOUND|"):
                    print(f" > Unexpected result: {output}")
                    stable_checks = 0
                    previous_signature = None
                    time.sleep(poll_interval)
                    continue

                parts = output.split("|", 4)
                if len(parts) != 5:
                    print(f" > Invalid result: {output}")
                    stable_checks = 0
                    previous_signature = None
                    time.sleep(poll_interval)
                    continue

                pid = parts[1].strip()
                session_id = parts[2].strip()
                handle = parts[3].strip()
                title = parts[4].strip()

                try:
                    handle_value = int(handle)
                except ValueError:
                    handle_value = 0

                if handle_value == 0:
                    print(" > License Manager found, but Handle=0.")

                    stable_checks = 0
                    previous_signature = None
                    time.sleep(poll_interval)
                    continue

                print(
                    f" > License Manager window: "
                    f"PID={pid}, "
                    f"Session={session_id}, "
                    f"Handle={handle}, "
                    f"Title='{title}'"
                )

                current_signature = (pid, session_id, handle, title)
                if current_signature == previous_signature:
                    stable_checks += 1
                else:
                    stable_checks = 1
                    previous_signature = current_signature
                print(
                    f" > License Manager detected: "
                    f"stable={stable_checks}/"
                    f"{stable_checks_required}"
                )

                if stable_checks >= stable_checks_required:
                    print(" > License Manager window is READY.")
                    return True, ("License Manager window is open " "in interactive Windows session.")
                time.sleep(poll_interval)

        finally:
            cleanup_final = (
                f'Remove-Item "{result_file}" '
                f'-Force -ErrorAction SilentlyContinue; '
                f'Remove-Item "{script_file}" '
                f'-Force -ErrorAction SilentlyContinue; '
                f'Unregister-ScheduledTask '
                f'-TaskName "{task_name}" '
                f'-Confirm:$false '
                f'-ErrorAction SilentlyContinue'
            )

            self.session.run_ps(cleanup_final)

        return False, (f"License Manager interactive window " f"was not detected within {timeout} seconds.")

    def wait_for_license_manager_window_old(self, timeout=120, poll_interval=2, stable_checks_required=5):

        start_time = time.time()
        stable_checks = 0
        previous_window_info = None

        check_window_ps = r"""
        Add-Type @"
        using System;
        using System.Runtime.InteropServices;

        public static class Win32Window
        {
            [DllImport("user32.dll")]
            public static extern bool IsWindowVisible(IntPtr hWnd);

            [DllImport("user32.dll")]
            public static extern bool GetWindowRect(
                IntPtr hWnd,
                out RECT rect
            );

            public struct RECT
            {
                public int Left;
                public int Top;
                public int Right;
                public int Bottom;
            }
        }
    "@

        $process = Get-Process -Name "KeysightLicenseManager" `
            -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowHandle -ne 0 } |
            Select-Object -First 1

        if (-not $process)
        {
            Write-Output "NOT_FOUND"
            exit
        }

        $handle = $process.MainWindowHandle
        $visible = [Win32Window]::IsWindowVisible($handle)

        $rect = New-Object Win32Window+RECT
        $rectResult = [Win32Window]::GetWindowRect(
            $handle,
            [ref]$rect
        )

        if ($rectResult)
        {
            $width = $rect.Right - $rect.Left
            $height = $rect.Bottom - $rect.Top
        }
        else
        {
            $width = 0
            $height = 0
        }

        $result = [PSCustomObject]@{
            ProcessId = $process.Id
            Title = $process.MainWindowTitle
            Handle = $handle.ToInt64()
            Responding = $process.Responding
            Visible = $visible
            Left = $rect.Left
            Top = $rect.Top
            Width = $width
            Height = $height
        }

        $result | ConvertTo-Json -Compress
        """

        while time.time() - start_time < timeout:
            result = self.session.run_ps(check_window_ps)

            output = result.std_out.decode(
                errors="ignore"
            ).strip()

            if not output or output == "NOT_FOUND":
                print(" > Waiting for License Manager process/window...")
                stable_checks = 0
                previous_window_info = None
                time.sleep(poll_interval)
                continue

            try:
                import json
                window_info = json.loads(output)

            except Exception:
                print(f" > Unexpected window check response: {output}")
                stable_checks = 0
                time.sleep(poll_interval)
                continue

            title = window_info.get("Title", "")
            responding = bool(window_info.get("Responding"))
            visible = bool(window_info.get("Visible"))
            width = int(window_info.get("Width", 0))
            height = int(window_info.get("Height", 0))
            handle = int(window_info.get("Handle", 0))

            basic_ready = (handle != 0 and responding and visible and width >= 300 and height >= 200)
            if not basic_ready:
                print(
                    " > Window exists but is not ready: "
                    f"title='{title}', "
                    f"responding={responding}, "
                    f"visible={visible}, "
                    f"size={width}x{height}"
                )

                stable_checks = 0
                previous_window_info = None
                time.sleep(poll_interval)
                continue

            current_signature = (title, window_info.get("Left"), window_info.get("Top"), width, height,)
            if current_signature == previous_window_info:
                stable_checks += 1
            else:
                stable_checks = 1
                previous_window_info = current_signature

            print(
                f" > License Manager window detected: "
                f"'{title}', size={width}x{height}, "
                f"stable={stable_checks}/{stable_checks_required}"
            )

            if stable_checks >= stable_checks_required:
                time.sleep(2)
                self.activate_license_manager_window()
                return True, ("License Manager window is visible, responding and stable.")
            time.sleep(poll_interval)

        return False, (f"License Manager window was not fully ready within {timeout} seconds.")

    def activate_license_manager_window(self):
        activate_ps = r"""
        $process = Get-Process -Name "KeysightLicenseManager" `
            -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowHandle -ne 0 } |
            Select-Object -First 1

        if (-not $process)
        {
            Write-Output "NOT_FOUND"
            exit
        }

        $shell = New-Object -ComObject WScript.Shell

        $activated = $shell.AppActivate($process.Id)

        if ($activated)
        {
            Start-Sleep -Milliseconds 500
            Write-Output "ACTIVATED"
        }
        else
        {
            Write-Output "ACTIVATE_FAILED"
        }
        """

        result = self.session.run_ps(activate_ps)

        return result.std_out.decode(
            errors="ignore"
        ).strip() == "ACTIVATED"

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

        print("Waiting 90 second to running BAT file....Please wait doing somethings in the background")
        time.sleep(90)
        self.session.run_ps(f"Unregister-ScheduledTask -TaskName '{task_name}' -Confirm:$false")
        return f"BAT started visibly for {current_user}"

    def get_model(self):

        if not self.session:
            if not self.connect():
                return None
        model = None
        result = self.session.run_ps("(Get-CimInstance Win32_ComputerSystem).UserName")
        full_user = result.std_out.decode(errors="ignore").strip()

        if not full_user:
            return None

        print(f"User: {full_user}")

        computer_name, username = full_user.split("\\", 1)
        match = re.search(r"(E\d{4}[A-Z]|N\d{4}[A-Z])", computer_name)

        if match:
            model = match.group(1)
            #print(model)

        return model


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

    def screenshot_network_old(self, folder, serial_number, picture_name="Firmware Revision", shot=1, window_title="About E5061B", full_screen=False):
        if not self.session:
            self.connect()

        session_id = self.get_active_session_id()
        print(f" > Capturing E50xx Firmware window on Session: {session_id}")
        run_id = int(time.time())
        remote_temp = r"C:\Windows\Temp"
        remote_nircmd = f"{remote_temp}\\nircmd.exe"
        remote_image = f"{remote_temp}\\e50xx_firmware_{run_id}.png"
        screenshot_path = load_configFile("screenShot_path")
        base_path = Path(screenshot_path)
        local_dir = (base_path / serial_number / folder)
        local_dir.mkdir(parents=True, exist_ok=True)
        local_image = (local_dir / f"{serial_number}_{picture_name}_{shot}.png")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        psexec_path = os.path.join(current_dir, "psexec.exe")

        nircmd_args = (["savescreenshot", remote_image] if full_screen else ["savescreenshotwin", remote_image, window_title])
        p_cmd = [psexec_path, "-accepteula", "-s", "-i", str(session_id), f"\\\\{self.target_ip}", "-u", self.username, "-p", self.password,
            "-d", remote_nircmd, *nircmd_args]
        result = subprocess.run(p_cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

        if result.returncode != 0:
            print(" > PsExec error:", result.stderr.decode(errors="ignore"))

        network_path = (f"\\\\{self.target_ip}" f"\\C$\\Windows\\Temp" f"\\e5061_firmware_{run_id}.png")

        found = False

        for _ in range(15):
            try:
                if (os.path.exists(network_path) and os.path.getsize(network_path) > 0):
                    found = True
                    break
            except OSError:
                pass
            time.sleep(1)
        if found:
            time.sleep(1)
            try:
                shutil.copy2(network_path, str(local_image))
                print(f" > SUCCESS! Firmware saved to: {local_image}")

                # Remove remote temporary file
                self.session.run_ps(
                    f"Remove-Item "
                    f"'{remote_image}' "
                    f"-Force "
                    f"-ErrorAction SilentlyContinue"
                )
                return str(local_image)

            except Exception as e:

                print(f" > Error copying file: {e}")
                return None
        else:
            print(
                " > Error: About E5061B screenshot was not created.")
            return None

    def screenshot_network(self, folder, serial_number, picture_name="Firmware Revision",  shot=1,  window_title="About E5061B", full_screen=False):
        if not self.session:
            self.connect()

        session_id = self.get_active_session_id()
        print(f" > Capturing screenshot on Session: {session_id}")
        run_id = uuid.uuid4().hex[:10]
        remote_temp = r"C:\Windows\Temp"
        remote_nircmd = rf"{remote_temp}\nircmd.exe"
        remote_image = rf"{remote_temp}\network_{run_id}.png"
        screenshot_path = load_configFile("screenShot_path")
        base_path = Path(screenshot_path)
        local_dir = base_path / serial_number / folder
        local_dir.mkdir(parents=True, exist_ok=True)
        local_image = ( local_dir / f"{serial_number}_{picture_name}_{shot}.png")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        psexec_path = os.path.join(current_dir, "psexec.exe")

        if full_screen:
            print(" > Screenshot mode: FULL SCREEN")
            nircmd_args = ["savescreenshot", remote_image]
        else:
            print(f" > Screenshot mode: WINDOW ({window_title})")
            nircmd_args = [ "savescreenshotwin", remote_image, window_title]

        p_cmd = [psexec_path, "-accepteula",  "-s", "-i", str(session_id), f"\\\\{self.target_ip}", "-u", self.username, "-p", self.password,
            "-d", remote_nircmd, *nircmd_args]

        result = subprocess.run(p_cmd, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
        print(f" > PsExec return code: {result.returncode}")
        if result.returncode != 0:
            print(" > PsExec error:", result.stderr.decode(errors="replace"))
        network_path = (
            f"\\\\{self.target_ip}"
            f"\\C$\\Windows\\Temp"
            f"\\network_{run_id}.png"
        )

        print(f" > Waiting for screenshot: {network_path}")
        found = False
        for _ in range(20):
            try:
                if (os.path.exists(network_path) and os.path.getsize(network_path) > 0):
                    found = True
                    break
            except OSError:
                pass
            time.sleep(1)

        if found:
            time.sleep(0.5)
            try:
                shutil.copy2(network_path, str(local_image))
                print(f" > SUCCESS! Screenshot saved: {local_image}")
                # Remove remote temporary image
                self.session.run_ps(
                    f"Remove-Item -LiteralPath '{remote_image}' "
                    f"-Force -ErrorAction SilentlyContinue"
                )
                return str(local_image)

            except Exception as e:
                print(f" > Error copying screenshot: {e}")
                return None

        print(" > ERROR: Screenshot file was not created or is inaccessible.")
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
        capture_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        screenshot_name = f"License Manager_{capture_id}"

        prev_img = self.screenshot("License", serial_number, screenshot_name, page_count)
        report_step(name=f"License ScreenShot #N{page_count}", status="INFO", progress=40, results_list=results_list, value=f"License ScreenShot #N{page_count}", image_path=prev_img, worker=worker, logger=logger)


        while not all_captured:
            print(f" > Processing page {page_count}...")

            self.scroll_license_list(steps)
            print(" > Waiting 5 seconds to Image recovered .....")
            time.sleep(5)

            page_count += 1
            steps = 12
            curr_img = self.screenshot("License", serial_number, screenshot_name, page_count)
            if self.is_last_page(prev_img, curr_img):
                print(" !!! Reached the end of the list (Images are identical).")
                if os.path.exists(curr_img):
                    os.remove(curr_img)
                all_captured = True
            else:
                prev_img = curr_img
                report_step(name=f"License ScreenShot {serial_number}_{screenshot_name}_#N{page_count}", status="INFO", progress=40,results_list=results_list, value=f"License ScreenShot #N{page_count}", image_path=curr_img,worker=worker, logger=logger)

        print("Done. All licenses captured.")

    # The screenshot all system information pages function - operat no the remote device
    def capture_all_systems(self, serial_number, results_list, worker, logger):
        all_captured = False
        page_count = 1
        steps = 20
        capture_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        screenshot_name = f"System_{capture_id}"

        print(" > System Information All ScreenShots .....")
        self.press_key_remote("UP", 60)
        prev_img = self.screenshot("System", serial_number,screenshot_name, page_count)
        report_step(name=f"System Information ScreenShot #N{page_count}", status="INFO", progress=40, results_list=results_list, value=f"System Information ScreenShot #N{page_count}", image_path=prev_img, worker=worker, logger=logger)
        while not all_captured:
            print(f" > Processing page {page_count}...")

            print(f" > Moving list {steps} steps Down.....")
            self.press_key_remote("DOWN", steps)
            print(" > Waiting 5 seconds to Image recovered .....")
            time.sleep(5)

            page_count += 1
            curr_img = self.screenshot("System", serial_number, screenshot_name, page_count)

            if self.is_last_page(prev_img, curr_img):
                print(" !!! Reached the end of the list (Images are identical).")
                if os.path.exists(curr_img):
                    os.remove(curr_img)
                all_captured = True
            else:
                prev_img = curr_img
                report_step(name=f"System Information ScreenShot {serial_number}_{screenshot_name}_#N{page_count}", status="INFO", progress=40,results_list=results_list, value=f"System Information ScreenShot #N{page_count}", image_path=curr_img, worker=worker, logger=logger)

        print("Done. All system information captured.")

    # The screenshot all system information windows function - operat no the remote device
    def capture_all_system_information(self, serial_number, results_list, worker, logger):
        all_captured = False
        page_count = 1
        steps = 1
        capture_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        screenshot_name = f"System_Info_{capture_id}"

        print(" > System Information ScreenShots .....")
        #self.press_key_remote("UP", 60)
        prev_img = self.screenshot("System Info", serial_number, screenshot_name, page_count)
        report_step(name=f"System Information ScreenShot #N{page_count}", status="INFO", progress=29,
                    results_list=results_list, value=f"System Information ScreenShot #N{page_count}",
                    image_path=prev_img, worker=worker, logger=logger)
        self.press_key_remote("PGDN", 3)
        while not all_captured:
            print(f" > Processing page {page_count}...")

            print(f" > Moving list {steps} Page Down.....")
            self.press_key_remote("PGDN", steps)
            print(" > Waiting 5 seconds to Image recovered .....")
            time.sleep(5)

            page_count += 1
            curr_img = self.screenshot("System Info", serial_number, screenshot_name, page_count)

            if self.is_last_page(prev_img, curr_img):
                print(" !!! Reached the end of the list (Images are identical).")
                if os.path.exists(curr_img):
                    os.remove(curr_img)
                all_captured = True
            else:
                prev_img = curr_img
                report_step(name=f"System Information ScreenShot {serial_number}_{screenshot_name}_#N{page_count}",
                            status="INFO", progress=29, results_list=results_list,
                            value=f"System Information ScreenShot #N{page_count}", image_path=curr_img,
                            worker=worker, logger=logger)

        print("Done. All system information captured.")

    # Set remote Windows to Auto Login as Administrator, reboot, reconnect, and verify active user
    def switch_remote_to_administrator(self, worker, logger, admin_user="Administrator", admin_password=None, domain="."):
        if admin_password is None:
            admin_password = self.password

        if not self.session:
            if not self.wait_for_winrm_port(timeout=300):
                print(" > WinRM port is not ready. Cannot switch user.")
                return False

            self.setup_local_machine()

            if not self.connect():
                print(" > Failed to connect before setting Auto Login")
                return False

        if self.session is None:
            print(" > Session is None. Cannot continue.")
            return False

        ps_script = f"""
        $reg = "HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon"

        Set-ItemProperty -Path $reg -Name "AutoAdminLogon" -Value "1"
        Set-ItemProperty -Path $reg -Name "DefaultUserName" -Value "{admin_user}"
        Set-ItemProperty -Path $reg -Name "DefaultPassword" -Value "{admin_password}"
        Set-ItemProperty -Path $reg -Name "DefaultDomainName" -Value "{domain}"

        shutdown.exe /r /f /t 5 /c "Switching to Administrator by Automation"
        """

        print(f" > Setting Auto Login to {admin_user} and rebooting remote PC...")
        self.session.run_ps(ps_script)
        self.session = None

        print(" > Waiting for reboot...")
        time.sleep(90)

        timeout = 1200
        elapsed = 90

        while elapsed < timeout:
            if not self.wait_for_winrm_port(timeout=60, worker=worker, logger=logger):
                elapsed += 60
                continue

            self.setup_local_machine()

            self.username = admin_user
            self.password = admin_password

            if self.connect():
                current_user = self.get_current_user()
                print(f" > Current active user: {current_user}")

                if current_user and admin_user.lower() in current_user.lower():
                    print(" > Remote PC is now logged in as Administrator.")
                    return True

            self.session = None
            time.sleep(20)
            elapsed += 20

        print(" > Failed to switch remote PC to Administrator")
        return False

    # Disable the auto login on the device
    def disable_auto_login(self):
        if not self.session:
            self.connect()

        ps = r"""
        $reg = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
        Set-ItemProperty -Path $reg -Name "AutoAdminLogon" -Value "0"
        Remove-ItemProperty -Path $reg -Name "DefaultPassword" -ErrorAction SilentlyContinue
        $auto = (Get-ItemProperty -Path $reg).AutoAdminLogon
        if ($auto -eq "0") {
            Write-Output "SUCCESS"
        }
        else {
            Write-Output "FAILED"
        }
        """

        result = self.session.run_ps(ps)
        return result.std_out.decode().strip()

    # Current user on the device
    def get_current_user(self):
        if not self.session:
            if not self.connect():
                return None
        try:
            result = self.session.run_ps(
                "(Get-CimInstance Win32_ComputerSystem).UserName"
            )
            current_user = result.std_out.decode(errors="ignore").strip()
            if "\\" in current_user:
                current_user = current_user.split("\\")[-1]
            return current_user

        except Exception as e:
            print(f"Error getting current user: {e}")
            self.session = None
            return None

    def bootstrap_winrm_via_schtasks(self, admin_user="Administrator", admin_password=None):
        if admin_password is None:
            admin_password = self.password

        remote_temp_unc = rf"\\{self.target_ip}\C$\TEMP"
        remote_bat_unc = rf"{remote_temp_unc}\enable_winrm.bat"
        done_file_unc = rf"{remote_temp_unc}\enable_winrm_done.txt"

        remote_bat_path = r"C:\TEMP\enable_winrm.bat"
        done_file_path = r"C:\TEMP\enable_winrm_done.txt"

        task_name = "EnableWinRM_ByAutomation"

        bat_content = r"""@echo off
        setlocal

        set LOG=C:\TEMP\enable_winrm_log.txt

        echo ====================================== > %LOG%
        echo Starting WinRM Bootstrap >> %LOG%
        echo ====================================== >> %LOG%

        echo ---- Changing WinRM Policies ---- >> %LOG%

        reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service" /v AllowAutoConfig /t REG_DWORD /d 1 /f >> %LOG% 2>&1
        reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service" /v AllowBasic /t REG_DWORD /d 1 /f >> %LOG% 2>&1
        reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service" /v AllowUnencryptedTraffic /t REG_DWORD /d 1 /f >> %LOG% 2>&1
        reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service" /v DisableRunAs /t REG_DWORD /d 0 /f >> %LOG% 2>&1

        reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service\WinRS" /v AllowRemoteShellAccess /t REG_DWORD /d 1 /f >> %LOG% 2>&1

        reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Client" /v AllowBasic /t REG_DWORD /d 1 /f >> %LOG% 2>&1
        reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Client" /v AllowUnencryptedTraffic /t REG_DWORD /d 1 /f >> %LOG% 2>&1

        echo ---- Restarting WinRM Service ---- >> %LOG%

        sc config WinRM start= auto >> %LOG% 2>&1
        net stop WinRM /y >> %LOG% 2>&1
        net start WinRM >> %LOG% 2>&1

        echo ---- Creating WinRM Listener ---- >> %LOG%

        winrm delete winrm/config/Listener?Address=*+Transport=HTTP >> %LOG% 2>&1
        winrm create winrm/config/Listener?Address=*+Transport=HTTP >> %LOG% 2>&1

        echo ---- Configuring WinRM Auth ---- >> %LOG%

        winrm set winrm/config/service/auth @{Basic="true"} >> %LOG% 2>&1
        winrm set winrm/config/service/auth @{CredSSP="true"} >> %LOG% 2>&1
        winrm set winrm/config/service @{AllowUnencrypted="true"} >> %LOG% 2>&1
        winrm set winrm/config/winrs @{AllowRemoteShellAccess="true"} >> %LOG% 2>&1

        echo ---- Firewall ---- >> %LOG%

        netsh advfirewall firewall set rule group="Windows Remote Management" new enable=yes >> %LOG% 2>&1
        netsh advfirewall firewall add rule name="WinRM 5985" dir=in action=allow protocol=TCP localport=5985 >> %LOG% 2>&1

        echo ---- Verify ---- >> %LOG%

        winrm enumerate winrm/config/listener >> %LOG% 2>&1
        netstat -ano | find ":5985" >> %LOG% 2>&1

        echo DONE > C:\TEMP\enable_winrm_done.txt
        echo Bootstrap Completed >> %LOG%

        endlocal
        exit /b 0
        """

        print(" > Bootstrapping WinRM using remote Scheduled Task...")

        try:
            subprocess.run(
                rf'net use \\{self.target_ip}\C$ {admin_password} /user:{admin_user} /persistent:no',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            Path(remote_temp_unc).mkdir(parents=True, exist_ok=True)

            with open(remote_bat_unc, "w", encoding="utf-8") as f:
                f.write(bat_content)

            if os.path.exists(done_file_unc):
                os.remove(done_file_unc)

            create_cmd = (
                f'schtasks /create '
                f'/S {self.target_ip} '
                f'/U {admin_user} '
                f'/P {admin_password} '
                f'/TN "{task_name}" '
                f'/TR "{remote_bat_path}" '
                f'/SC ONCE '
                f'/ST 23:59 '
                f'/RU SYSTEM '
                f'/RL HIGHEST '
                f'/F'
            )

            run_cmd = (
                f'schtasks /run '
                f'/S {self.target_ip} '
                f'/U {admin_user} '
                f'/P {admin_password} '
                f'/TN "{task_name}"'
            )

            delete_cmd = (
                f'schtasks /delete '
                f'/S {self.target_ip} '
                f'/U {admin_user} '
                f'/P {admin_password} '
                f'/TN "{task_name}" '
                f'/F'
            )
            result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                print(" > Failed to create scheduled task")
                print(result.stdout)
                print(result.stderr)
                return False
            result = subprocess.run(run_cmd, shell=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                print(" > Failed to run scheduled task")
                print(result.stdout)
                print(result.stderr)
                return False

            print(" > Scheduled Task started. Waiting for WinRM...")

            start_time = time.time()
            timeout = 180

            while time.time() - start_time < timeout:
                if os.path.exists(done_file_unc):
                    print(" > Bootstrap BAT finished")

                if self.wait_for_winrm_port(timeout=10):
                    print(" > WinRM is ready")
                    subprocess.run(
                        delete_cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    return True

                time.sleep(5)

            log_file_unc = rf"{remote_temp_unc}\enable_winrm_log.txt"

            print(" > Timeout: WinRM did not open")
            if os.path.exists(log_file_unc):
                print(" > Bootstrap log:")
                with open(log_file_unc, "r", encoding="utf-8", errors="ignore") as f:
                    print(f.read())

            return False

        except Exception as e:
            print(f" > Bootstrap failed: {e}")
            return False

        finally:
            subprocess.run(
                rf'net use \\{self.target_ip}\C$ /delete /y',
                shell=True,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

    def set_auto_login_user(self, username="Instrument", password=None, domain="."):
        if password is None:
            password = self.password

        if not self.session:
            self.connect()

        ps = f"""
        $reg = "HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon"
        Set-ItemProperty -Path $reg -Name "AutoAdminLogon" -Value "1"
        Set-ItemProperty -Path $reg -Name "DefaultUserName" -Value "{username}"
        Set-ItemProperty -Path $reg -Name "DefaultPassword" -Value "{password}"
        Set-ItemProperty -Path $reg -Name "DefaultDomainName" -Value "{domain}"
        $auto = (Get-ItemProperty -Path $reg).AutoAdminLogon
        $user = (Get-ItemProperty -Path $reg).DefaultUserName
        if ($auto -eq "1" -and $user -eq "{username}") {{
            Write-Output "SUCCESS"
        }} else {{
            Write-Output "FAILED"
        }}
        """

        result = self.session.run_ps(ps)
        return result.std_out.decode(errors="ignore").strip()

    def launch_app(self, exe_path):
        if not self.session:
            if not self.connect():
                return False

        if not exe_path or exe_path == "NOT_FOUND":
            print("Invalid application path")
            return False

        work_dir = str(Path(exe_path).parent)
        process_name = Path(exe_path).stem

        get_user = self.session.run_ps(
            "(Get-CimInstance Win32_ComputerSystem).UserName"
        )
        current_user = get_user.std_out.decode(
            errors="ignore"
        ).strip()

        if not current_user:
            print("No active user session found")
            return False

        task_name = f"LaunchApp_{int(time.time())}"

        inner_ps = f"""
        Start-Process `
            -FilePath "{exe_path}" `
            -WorkingDirectory "{work_dir}" `
            -WindowStyle Normal
        """

        encoded_payload = base64.b64encode(
            inner_ps.encode("utf-16-le")
        ).decode("utf-8")

        cmd = (
            f'$action = New-ScheduledTaskAction '
            f'-Execute "powershell.exe" '
            f'-Argument "-NoProfile -ExecutionPolicy Bypass '
            f'-EncodedCommand {encoded_payload}"; '

            f'Register-ScheduledTask '
            f'-TaskName "{task_name}" '
            f'-Action $action '
            f'-User "{current_user}" '
            f'-RunLevel Highest '
            f'-Force | Out-Null; '

            f'Start-ScheduledTask -TaskName "{task_name}"'
        )

        print(f" > Launching application for: {current_user}")
        print(f" > Application path: {exe_path}")
        print(f" > Expected process: {process_name}.exe")

        try:
            result = self.session.run_ps(cmd)

            error = result.std_err.decode(
                errors="ignore"
            ).strip()

            if error:
                print(f"Launch command warning: {error}")

            # זמן המתנה לעליית התהליך
            timeout = 60
            elapsed = 0

            while elapsed < timeout:
                check = self.session.run_ps(
                    f"""
                    $p = Get-Process `
                        -Name "{process_name}" `
                        -ErrorAction SilentlyContinue

                    if ($p) {{
                        $p |
                        Select-Object ProcessName, Id, Path
                    }}
                    """
                )

                output = check.std_out.decode(
                    errors="ignore"
                ).strip()

                if output:
                    print("Launch App started successfully")
                    print(output)

                    self.session.run_ps(
                        f"Unregister-ScheduledTask "
                        f"-TaskName '{task_name}' "
                        f"-Confirm:$false "
                        f"-ErrorAction SilentlyContinue"
                    )

                    return True

                time.sleep(2)
                elapsed += 2

            print(
                f"Application process {process_name}.exe "
                f"was not detected after {timeout} seconds"
            )

            return False

        except Exception as e:
            print(f"Launch App failed: {e}")
            self.session = None
            return False

        finally:
            if self.session:
                self.session.run_ps(
                    f"Unregister-ScheduledTask "
                    f"-TaskName '{task_name}' "
                    f"-Confirm:$false "
                    f"-ErrorAction SilentlyContinue"
                )

    def is_xsa_running(self):
        if not self.session:
            if not self.connect():
                return False


        ps = r"""
        $p = Get-Process -ErrorAction SilentlyContinue |
             Where-Object {
                $_.ProcessName -eq "LaunchXSA" -or
                $_.ProcessName -eq "Agilent.SA.xSA" -or
                $_.ProcessName -eq "Keysight.SA.xSA" -or
                $_.ProcessName -like "*xSA*"
             }
        if ($p) {
            $p | Select-Object ProcessName,Id,Path
        }
        """
        result = self.session.run_ps(ps)
        output = result.std_out.decode(errors="ignore").strip()
        if output:
            print("XSA is running")
            return True

        print("XSA is not running")
        return False

    def find_launch_network_path(self):
        if not self.session:
            if not self.connect():
                return "NOT_FOUND"
        exe_names = ["E5061.exe", "E5062.exe", "E5071.exe", "E5072.exe", "E5080.exe",  "835x.exe", "ENA.exe", "NetworkAnalyzer.exe", "Network Analyzer.exe", "PNA.exe",]
        known_paths = [
            r"C:\Program Files (x86)\Agilent\E5061B\E5061.exe",
            r"C:\Program Files (x86)\Keysight\E5061B\E5061.exe",
            r"C:\Program Files\Agilent\E5061B\E5061.exe",
            r"C:\Program Files\Keysight\E5061B\E5061.exe",

            r"C:\Program Files (x86)\Agilent\E5061\E5061.exe",
            r"C:\Program Files (x86)\Keysight\E5061\E5061.exe",
            r"C:\Program Files\Agilent\E5061\E5061.exe",
            r"C:\Program Files\Keysight\E5061\E5061.exe",

            r"C:\Program Files\Keysight\Network Analyzer\835x.exe",
            r"C:\Program Files\Agilent\Network Analyzer\835x.exe",
            r"C:\Program Files (x86)\Keysight\Network Analyzer\835x.exe",
            r"C:\Program Files (x86)\Agilent\Network Analyzer\835x.exe",
        ]

        for path in known_paths:
            ps = f"""
            if (Test-Path -LiteralPath '{path}') {{
                Write-Output '{path}'
            }}
            """

            try:
                result = self.session.run_ps(ps)
                output = result.std_out.decode(errors="ignore").strip()

                if output:
                    print(f"Network Analyzer path found: {output}")
                    return output

            except Exception as e:
                print(f"Known-path check failed: {e}")
                self.session = None
                return "NOT_FOUND"

        search_roots = [
            r"C:\Program Files (x86)\Agilent",
            r"C:\Program Files (x86)\Keysight",
            r"C:\Program Files\Keysight\Network Analyzer",
            r"C:\Program Files\Agilent\Network Analyzer",
            r"C:\Program Files\Agilent",
            r"C:\Program Files\Keysight",
            r"D:\Program Files (x86)\Agilent",
            r"D:\Program Files (x86)\Keysight",
            r"D:\Program Files\Agilent",
            r"D:\Program Files\Keysight",
            r"D:\Agilent",
            r"D:\Keysight",
        ]

        for root in search_roots:
            for exe_name in exe_names:
                ps = f"""
                if (Test-Path -LiteralPath '{root}') {{
                    Get-ChildItem `
                        -LiteralPath '{root}' `
                        -Filter '{exe_name}' `
                        -File `
                        -Recurse `
                        -ErrorAction SilentlyContinue |
                    Where-Object {{
                        $_.FullName -notmatch
                        'Windows\\\\Installer|IO Libraries|Connection Expert|Updater|Uninstall'
                    }} |
                    Select-Object -First 1 -ExpandProperty FullName
                }}
                """

                try:
                    result = self.session.run_ps(ps)
                    output = result.std_out.decode(errors="ignore").strip()

                    if output:
                        print(f"Network Analyzer path found: {output}")
                        return output

                except Exception as e:
                    print(
                        f"Search failed: root={root}, "
                        f"exe={exe_name}, error={e}"
                    )
                    self.session = None
                    return "NOT_FOUND"

        ps_running = r"""
        Get-CimInstance Win32_Process |
        Where-Object {
            $_.ExecutablePath -and
            $_.Name -match '^(E5061|E5062|E5071|E5072|E5080|835x|ENA|PNA|NetworkAnalyzer)\.exe$'
        } |
        Select-Object -First 1 -ExpandProperty ExecutablePath
        """

        try:
            result = self.session.run_ps(ps_running)
            output = result.std_out.decode(errors="ignore").strip()

            if output:
                print(f"Running Network Analyzer path: {output}")
                return output

        except Exception as e:
            print(f"Running-process search failed: {e}")
            self.session = None

        print("Network Analyzer application was not found")
        return "NOT_FOUND"

    def debug_network_path(self):
        if not self.session:
            if not self.connect():
                return

        ps = r"""
        $folder = 'C:\Program Files\Keysight\Network Analyzer'
        $file = Join-Path $folder 'E835x.exe'

        Write-Output "=== DEBUG ==="
        Write-Output "Computer: $env:COMPUTERNAME"
        Write-Output "User: $env:USERNAME"

        Write-Output "=== FOLDER ==="
        Write-Output "Folder exists: $(Test-Path -LiteralPath $folder)"

        Write-Output "=== FILE ==="
        Write-Output "File exists: $(Test-Path -LiteralPath $file -PathType Leaf)"

        Write-Output "=== DIRECTORY CONTENT ==="
        if (Test-Path -LiteralPath $folder) {
            Get-ChildItem -LiteralPath $folder -Force |
            Select-Object Name, FullName |
            Format-Table -AutoSize |
            Out-String -Width 300
        }

        Write-Output "=== MATCHING FILES ==="
        Get-ChildItem 'C:\Program Files\Keysight' `
            -Filter '*835*' `
            -Recurse `
            -File `
            -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty FullName
        """

        result = self.session.run_ps(ps)

        print("STDOUT:")
        print(result.std_out.decode("utf-8", errors="replace"))

        print("STDERR:")
        print(result.std_err.decode("utf-8", errors="replace"))

    def find_launch_xsa_path(self):
        if not self.session:
            self.connect()

        ps = r"""
        $paths = @(
             # N90xxB - Signal Analyzer XSA
            "C:\Program Files\Keysight\SignalAnalysis\Infrastructure\LaunchXSA.exe",
            "C:\Program Files\Agilent\SignalAnalysis\Infrastructure\LaunchXSA.exe",
            "C:\Program Files\Agilent\SignalAnalysis\Infrastructure\LaunchXSA.exe",
            "C:\Program Files (x86)\Keysight\SignalAnalysis\Infrastructure\LaunchXSA.exe",
            "C:\Program Files (x86)\Agilent\SignalAnalysis\Infrastructure\LaunchXSA.exe",
            "C:\Program Files (x86)\Agilent\SignalAnalysis\Infrastructure\LaunchXSA.exe"
        )
        foreach ($p in $paths) {
            if (Test-Path $p) {
                Write-Output $p
                exit
            }
        }
        Write-Output "NOT_FOUND"
        """

        result = self.session.run_ps(ps)
        return result.std_out.decode(errors="ignore").strip()

    def list_recent_processes(self):
        if not self.session:
            self.connect()

        ps = r"""
        Get-Process |
        Sort-Object StartTime -Descending -ErrorAction SilentlyContinue |
        Select-Object -First 20 ProcessName,Id,Path
        """

        result = self.session.run_ps(ps)
        print(result.std_out.decode(errors="ignore"))

    def press_no_app_popup(self, wait_seconds=10):
        if not self.session:
            self.connect()

        current_user = self.get_current_user()
        if not current_user:
            return "Error: No active user session found."

        time.sleep(wait_seconds)
        self.press_key_remote("TAB", 1)
        time.sleep(1)
        self.press_key_remote("ENTER", 1)

        return "NO key sequence sent"

    def wait_for_winrm_port(self, timeout=300, worker=None, logger=None):
        results_list = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                with socket.create_connection((self.target_ip, 5985), timeout=5):
                    report_step("WinRM port 5985 is open", "PASS", 0, results_list, " ", None, worker, logger)
                    print(" > WinRM port 5985 is open")
                    return True
            except:
                report_step("Waiting for WinRM port 5985...", "INFO", 0, results_list, " ", None, worker, logger)
                print(" > Waiting for WinRM port 5985...")
                time.sleep(10)

        return False

    def disable_windows_update_notifications(self, worker=None, logger=None):

        results_list = []

        if not self.session:
            if not self.connect():
                return False

        ps = r"""
        $reg1 = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate"
        $reg2 = "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"
        New-Item -Path $reg1 -Force | Out-Null
        New-Item -Path $reg2 -Force | Out-Null
        # Hide update notifications
        New-ItemProperty -Path $reg1 -Name "SetUpdateNotificationLevel" -Value 1 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $reg1 -Name "UpdateNotificationLevel" -Value 2 -PropertyType DWord -Force | Out-Null
        # Disable restart/update toast notifications
        New-ItemProperty -Path $reg2 -Name "RestartNotificationsAllowed2" -Value 0 -PropertyType DWord -Force | Out-Null
        New-ItemProperty -Path $reg2 -Name "TrayIconVisibility" -Value 0 -PropertyType DWord -Force | Out-Null
        gpupdate /force | Out-Null
        Write-Output "SUCCESS"
        """

        result = self.session.run_ps(ps)
        output = result.std_out.decode(errors="ignore").strip()

        #print(output)
        report_step("Disable windows Updated notifications", "PASS", 85, results_list, "Disable windows Updated notifications", None, worker, logger)
        return "SUCCESS" in output

    def stop_agilent_update_popup(self, worker=None, logger=None):
        results_list = []
        if not self.session:
            if not self.connect():
                return False

        ps = r'''
        Stop-Process -Name "AgilentLicenseNotifier" -Force -ErrorAction SilentlyContinue
        Write-Output "SUCCESS"
        '''

        result = self.session.run_ps(ps)
        output = result.std_out.decode(errors="ignore").strip()
        #print(output)
        report_step("Disable Agilent Updated notifications", "PASS", 85, results_list, "Disable windows Updated notifications", None, worker, logger)
        return "SUCCESS" in output

    def uninstall_all_calibration_advisors(self, dry_run=True):
        """
        Search and uninstall possible Keysight/Agilent Calibration Advisor apps.
        dry_run=True  -> only show what would be removed
        dry_run=False -> uninstall
        """

        if not self.session:
            if not self.connect():
                return False

        dry = "$true" if dry_run else "$false"

        ps = rf'''
        $dryRun = {dry}
        $keywords = @(
            "Calibration Advisor",
            "PathWave Calibration",
            "Keysight PathWave Calibration",
            "Keysight Calibration",
            "Agilent Calibration"
        )
        $apps = Get-ItemProperty `
            HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*, `
            HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* `
            -ErrorAction SilentlyContinue |
        Where-Object {{
            $name = $_.DisplayName
            if (-not $name) {{ return $false }}

            foreach ($k in $keywords) {{
                if ($name -like "*$k*") {{ return $true }}
            }}

            return $false
        }}

        if (-not $apps) {{
            Write-Output "NOT_FOUND"
            exit
        }}

        foreach ($app in $apps) {{
            Write-Output "FOUND: $($app.DisplayName) | Version: $($app.DisplayVersion)"

            if ($dryRun) {{
                Write-Output "DRY_RUN: Will not uninstall"
                continue
            }}

            $uninstall = $app.UninstallString

            if ($uninstall -match "MsiExec.exe") {{
                $guid = [regex]::Match($uninstall, "\{{[A-Fa-f0-9\-]+\}}").Value

                if ($guid) {{
                    Write-Output "UNINSTALLING MSI: $guid"
                    Start-Process "msiexec.exe" -ArgumentList "/x $guid /qn /norestart" -Wait
                    Write-Output "UNINSTALLED: $($app.DisplayName)"
                }}
                else {{
                    Write-Output "ERROR: MSI GUID not found for $($app.DisplayName)"
                }}
            }}
            elseif ($uninstall) {{
                Write-Output "NON_MSI_FOUND: $($app.DisplayName)"
                Write-Output "UninstallString: $uninstall"
            }}
            else {{
                Write-Output "ERROR: No uninstall string for $($app.DisplayName)"
            }}
        }}
        '''

        result = self.session.run_ps(ps)
        output = result.std_out.decode(errors="ignore").strip()
        error = result.std_err.decode(errors="ignore").strip()
        #print(output)
        if error:
            print(error)

        return "UNINSTALLED" in output or "FOUND" in output

    def get_running_network_analyzer_path(self):
        if not self.session:
            if not self.connect():
                return False

        ps = r"""
        Get-CimInstance Win32_Process |
        Where-Object {
            $_.ExecutablePath -and
            (
                $_.Name -match 'ena|network|e506|e507|e508|pna' -or
                $_.ExecutablePath -match 'ena|network|e506|e507|e508|pna'
            )
        } |
        Where-Object {
            $_.ExecutablePath -notmatch '^C:\\Windows\\Installer\\'
        } |
        Select-Object -First 1 -ExpandProperty ExecutablePath
        """

        try:
            result = self.session.run_ps(ps)

            path = result.std_out.decode(
                errors="ignore"
            ).strip()

            if path:
                print(f"Running Network Analyzer path: {path}")
                return path

        except Exception as e:
            print(f"Failed to get running process path: {e}")
            self.session = None

        return "NOT_FOUND"

    def get_latest_file_date(self, folder_path, extension):
        try:
            if not self.session:
                self.connect()

            extension = extension.lstrip(".")

            ps_command = f"""
            $folder = '{folder_path}'

            $file = Get-ChildItem -Path $folder -File -Filter '*.{extension}' |
                    Sort-Object LastWriteTime -Descending |
                    Select-Object -First 1

            if ($file) {{
                "$($file.Name)|$($file.LastWriteTime.ToString('dd/MM/yyyy HH:mm'))"
            }}
            """

            result = self.session.run_ps(ps_command)

            output = result.std_out.decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if not output:
                return [None, None]

            file_name, file_date = output.split("|", 1)

            return [file_name, file_date]

        except Exception as e:
            print(f"get_latest_file_date Error: {e}")
            return [None, None]

    def open_firmware_revision(self, timeout=15):
        if not self.session:
            self.connect()

        result = self.session.run_cmd("quser")
        output = result.std_out.decode(errors="ignore").strip()

        username = None

        for line in output.splitlines():
            if "Active" in line:
                parts = line.replace(">", "").split()

                if parts:
                    username = parts[0]
                    break

        if not username:
            return False, "No active interactive user found."

        host_result = self.session.run_cmd("hostname")
        hostname = host_result.std_out.decode(errors="ignore").strip()

        current_user = f"{hostname}\\{username}"

        print(f" > Interactive user: {current_user}")
        print(" > Opening Firmware Revision...")

        task_name = f"E5061_Firmware_{int(time.time())}"
        remote_script = r"C:\Windows\Temp\E5061_Open_Firmware.ps1"
        remote_b64 = r"C:\Windows\Temp\E5061_Open_Firmware.b64"
        remote_log = r"C:\Windows\Temp\E5061_Open_Firmware.txt"

        inner_ps = r'''
        $log = "C:\Windows\Temp\E5061_Open_Firmware.txt" 
        "=== OPEN FIRMWARE REVISION ===" |
            Out-File $log -Force 
        try
        {
            $p =
                Get-Process E5061 -ErrorAction Stop |
                Select-Object -First 1
    
            $targetPid = $p.Id
            "E5061 PID=$targetPid" |
                Out-File $log -Append
            $code = '
        [DllImport("user32.dll")]
        public static extern bool EnumWindows(
            EnumWindowsProc callback,
            IntPtr lParam);   
        public delegate bool EnumWindowsProc(
            IntPtr hWnd,
            IntPtr lParam);   
        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(
            IntPtr hWnd,
            out uint processId);   
        [DllImport("user32.dll")]
        public static extern int GetClassName(
            IntPtr hWnd,
            System.Text.StringBuilder lpClassName,
            int nMaxCount); 
        [DllImport("user32.dll")]
        public static extern IntPtr SendMessage(
            IntPtr hWnd,
            uint Msg,
            IntPtr wParam,
            IntPtr lParam);
        '  
            Add-Type `
                -MemberDefinition $code `
                -Name Win32 `
                -Namespace E5061Firmware
            $script:targetHwnd = [IntPtr]::Zero   
            $callback = {  
                param(
                    $hwnd,
                    $lparam
                )   
                [uint32]$pidValue = 0  
                [void][E5061Firmware.Win32]::GetWindowThreadProcessId(
                    $hwnd,
                    [ref]$pidValue
                )  
                if ($pidValue -eq $targetPid)
                {
                    $class =
                        New-Object System.Text.StringBuilder 256   
                    [void][E5061Firmware.Win32]::GetClassName(
                        $hwnd,
                        $class,
                        256
                    )
                    if ($class.ToString() -eq "AgilentENAMainWindow")
                    {
                        $script:targetHwnd = $hwnd
                        return $false
                    }
                }
    
                return $true
            }  
            $delegate =
                [E5061Firmware.Win32+EnumWindowsProc]$callback
      
            [void][E5061Firmware.Win32]::EnumWindows(
                $delegate,
                [IntPtr]::Zero
            )
            if ($script:targetHwnd -eq [IntPtr]::Zero)
            {
                "ERROR: AgilentENAMainWindow not found" |
                    Out-File $log -Append  
                exit 12
            }     
            $hwnd = $script:targetHwnd   
            "E5061 HWND=$hwnd" |
                Out-File $log -Append
            [void][E5061Firmware.Win32]::SendMessage(
                $hwnd,
                0x0111,
                [IntPtr]1026,
                [IntPtr]::Zero
            ) 
            "SYSTEM opened" |
                Out-File $log -Append 
            Start-Sleep -Milliseconds 800
            $wshell =
                New-Object -ComObject WScript.Shell   
            $activated =
                $wshell.AppActivate(
                    "E5061B Network Analyzer"
                )
    
            if (-not $activated)
            {
                "ERROR: Could not activate E5061" |
                    Out-File $log -Append
                exit 13
            }
            "E5061 activated" |
                Out-File $log -Append    
            Start-Sleep -Milliseconds 800
            for ($i = 1; $i -le 8; $i++)
            {
                $wshell.SendKeys("{DOWN}")
                Start-Sleep -Milliseconds 200
            }
    
            Start-Sleep -Milliseconds 500 
            $wshell.SendKeys("{ENTER}") 
            "Firmware Revision opened" |
                Out-File $log -Append  
            Start-Sleep -Seconds 2 
            exit 0
        }
        catch
        {
            "ERROR: $($_.Exception.Message)" |
                Out-File $log -Append 
            exit 20
        }
        '''

        encoded_script = base64.b64encode(inner_ps.encode("utf-8")).decode("ascii")
        self.session.run_ps(f"Remove-Item '{remote_b64}' " f"-Force -ErrorAction SilentlyContinue")
        self.session.run_ps(f"Remove-Item '{remote_script}' " f"-Force -ErrorAction SilentlyContinue")
        self.session.run_ps(f"Remove-Item '{remote_log}' " f"-Force -ErrorAction SilentlyContinue")
        chunk_size = 500

        for i in range(0, len(encoded_script), chunk_size):
            chunk = encoded_script[i:i + chunk_size]
            result = self.session.run_ps(f"[IO.File]::AppendAllText("  f"'{remote_b64}'," f"'{chunk}')")

            if result.status_code != 0:
                error = result.std_err.decode(errors="ignore").strip()
                return False, (f"Failed transferring script: {error}")

        convert_cmd = (
            f"$b=[IO.File]::ReadAllText('{remote_b64}');"
            f"$d=[Convert]::FromBase64String($b);"
            f"[IO.File]::WriteAllBytes('{remote_script}',$d)"
        )

        result = self.session.run_ps(convert_cmd)
        if result.status_code != 0:
            error = result.std_err.decode(errors="ignore").strip()
            return False, (f"Failed creating PowerShell script: {error}")
        self.session.run_ps(f"Remove-Item '{remote_b64}' " f"-Force -ErrorAction SilentlyContinue")

        reg_cmd = f'''
        $user = "{current_user}"
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File {remote_script}"
        $principal = New-ScheduledTaskPrincipal `
            -UserId $user `
            -LogonType Interactive `
            -RunLevel Highest
        $task = New-ScheduledTask `
            -Action $action `
            -Principal $principal
        Register-ScheduledTask `
            -TaskName "{task_name}" `
            -InputObject $task `
            -Force | Out-Null
        Start-ScheduledTask `
            -TaskName "{task_name}"
        '''
        try:
            result = self.session.run_ps(reg_cmd)
            if result.status_code != 0:
                error = result.std_err.decode(errors="ignore").strip()
                return False, (f"Failed starting Firmware task: {error}")

            start_time = time.time()
            state = None
            last_result = None
            while time.time() - start_time < timeout:
                time.sleep(0.5)
                check_cmd = f"""
                $task = Get-ScheduledTask `
                    -TaskName '{task_name}' `
                    -ErrorAction SilentlyContinue
                if ($task)
                {{
                    $info = Get-ScheduledTaskInfo `
                        -TaskName '{task_name}'
            
                    Write-Output "STATE=$($task.State)"
                    Write-Output "RESULT=$($info.LastTaskResult)"
                }}
                """
                check = self.session.run_ps(check_cmd)
                check_output = check.std_out.decode(errors="ignore").strip()
                for line in check_output.splitlines():
                    if line.startswith("STATE="):
                        state = line.split("=", 1)[1].strip()
                    elif line.startswith("RESULT="):

                        try:
                            last_result = int(line.split("=", 1)[1].strip())
                        except ValueError:
                            pass

                if state == "Ready":
                    break

            log_result = self.session.run_ps(f"Get-Content '{remote_log}' " f"-ErrorAction SilentlyContinue")
            log_output = log_result.std_out.decode(errors="ignore").strip()

            if log_output:
                print(" > E5061 Firmware:")
                print(log_output)
            if state != "Ready":
                return False, "Firmware task timeout."
            if last_result == 0:
                return True, "Firmware Revision opened."
            if last_result == 12:
                return False, "E5061 main window not found."
            if last_result == 13:
                return False, "Could not activate E5061 window."
            if last_result == 20:
                return False, "Failed opening Firmware Revision."
            return False, (f"Firmware task failed. " f"LastTaskResult={last_result}")

        finally:
            self.session.run_ps(
                f"Unregister-ScheduledTask "
                f"-TaskName '{task_name}' "
                f"-Confirm:$false "
                f"-ErrorAction SilentlyContinue"
            )

            self.session.run_ps(
                f"Remove-Item '{remote_script}' "
                f"-Force -ErrorAction SilentlyContinue"
            )

    def close_firmware_revision(self, timeout=10):
        if not self.session:
            self.connect()
        result = self.session.run_cmd("quser")
        output = result.std_out.decode(errors="ignore").strip()
        username = None

        for line in output.splitlines():
            if "Active" in line:
                parts = line.replace(">", "").split()
                if parts:
                    username = parts[0]
                    break
        if not username:
            return False, "No active interactive user found."

        host_result = self.session.run_cmd("hostname")
        hostname = host_result.std_out.decode(errors="ignore").strip()
        current_user = f"{hostname}\\{username}"
        print(f" > Interactive user: {current_user}")
        print(" > Closing E5061B Firmware Revision...")
        task_name = f"E5061_CloseFirmware_{int(time.time())}"
        remote_script = r"C:\Windows\Temp\E5061_Close_Firmware.ps1"
        remote_b64 = r"C:\Windows\Temp\E5061_Close_Firmware.b64"
        remote_log = r"C:\Windows\Temp\E5061_Close_Firmware.txt"

        inner_ps = r'''
        $log = "C:\Windows\Temp\E5061_Close_Firmware.txt"  
        "=== CLOSE E5061 FIRMWARE ===" |
            Out-File $log -Force
        try
        {
            $p =
                Get-Process E5061 -ErrorAction Stop |
                Select-Object -First 1
            $targetPid = $p.Id
            "E5061 PID=$targetPid" |
                Out-File $log -Append
            $code = '
        [DllImport("user32.dll")]
        public static extern bool EnumWindows(
            EnumWindowsProc callback,
            IntPtr lParam); 
        [DllImport("user32.dll")]
        public static extern bool EnumChildWindows(
            IntPtr hWndParent,
            EnumWindowsProc callback,
            IntPtr lParam);  
        public delegate bool EnumWindowsProc(
            IntPtr hWnd,
            IntPtr lParam);
        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(
            IntPtr hWnd,
            out uint processId);
        [DllImport("user32.dll")]
        public static extern int GetWindowText(
            IntPtr hWnd,
            System.Text.StringBuilder lpString,
            int nMaxCount); 
        [DllImport("user32.dll")]
        public static extern int GetClassName(
            IntPtr hWnd,
            System.Text.StringBuilder lpClassName,
            int nMaxCount);  
        [DllImport("user32.dll")]
        public static extern int GetDlgCtrlID(
            IntPtr hWnd); 
        [DllImport("user32.dll")]
        public static extern IntPtr SendMessage(
            IntPtr hWnd,
            uint Msg,
            IntPtr wParam,
            IntPtr lParam);
        ' 
            Add-Type `
                -MemberDefinition $code `
                -Name Win32 `
                -Namespace E5061Close
    
            $script:aboutHwnd = [IntPtr]::Zero
            $callback = {
                param(
                    $hwnd,
                    $lparam
                )
                [uint32]$pidValue = 0
                [void][E5061Close.Win32]::GetWindowThreadProcessId(
                    $hwnd,
                    [ref]$pidValue
                )
                if ($pidValue -eq $targetPid)
                {
                    $title =
                        New-Object System.Text.StringBuilder 256
                    $class =
                        New-Object System.Text.StringBuilder 256
                    [void][E5061Close.Win32]::GetWindowText(
                        $hwnd,
                        $title,
                        256
                    )
                    [void][E5061Close.Win32]::GetClassName(
                        $hwnd,
                        $class,
                        256
                    )
                    if (
                        $title.ToString() -eq "About E5061B" -and
                        $class.ToString() -eq "#32770"
                    )
                    {
                        $script:aboutHwnd = $hwnd
    
                        return $false
                    }
                }
                return $true
            }
            $delegate =
                [E5061Close.Win32+EnumWindowsProc]$callback
            [void][E5061Close.Win32]::EnumWindows(
                $delegate,
                [IntPtr]::Zero
            )
            if ($script:aboutHwnd -eq [IntPtr]::Zero)
            {
                "ERROR: About E5061B not found" |
                    Out-File $log -Append
                exit 12
            }
            "About HWND=$($script:aboutHwnd)" |
                Out-File $log -Append
            $script:closeHwnd = [IntPtr]::Zero
            $childCallback = { 
                param(
                    $hwnd,
                    $lparam
                )
                $class =
                    New-Object System.Text.StringBuilder 256
                $title =
                    New-Object System.Text.StringBuilder 256 
                [void][E5061Close.Win32]::GetClassName(
                    $hwnd,
                    $class,
                    256
                )
                [void][E5061Close.Win32]::GetWindowText(
                    $hwnd,
                    $title,
                    256
                )
                $id =
                    [E5061Close.Win32]::GetDlgCtrlID(
                        $hwnd
                    )
                if (
                    $class.ToString() -eq "Button" -and
                    $title.ToString() -eq "Close" -and
                    $id -eq 1151
                )
                {
                    $script:closeHwnd = $hwnd
    
                    return $false
                }
                return $true
            }
            $childDelegate =
                [E5061Close.Win32+EnumWindowsProc]$childCallback
            [void][E5061Close.Win32]::EnumChildWindows(
                $script:aboutHwnd,
                $childDelegate,
                [IntPtr]::Zero
            )
            if ($script:closeHwnd -eq [IntPtr]::Zero)
            {
                "ERROR: Close button not found" |
                    Out-File $log -Append
    
                exit 13
            }
            "Close HWND=$($script:closeHwnd)" |
                Out-File $log -Append
            [void][E5061Close.Win32]::SendMessage(
                $script:closeHwnd,
                0x00F5,
                [IntPtr]::Zero,
                [IntPtr]::Zero
            )
            "BM_CLICK sent" |
                Out-File $log -Append
            Start-Sleep -Milliseconds 1000
            $script:stillOpen = $false
            $verifyCallback = {  
                param(
                    $hwnd,
                    $lparam
                )
                [uint32]$pidValue = 0
                [void][E5061Close.Win32]::GetWindowThreadProcessId(
                    $hwnd,
                    [ref]$pidValue
                )
                if ($pidValue -eq $targetPid)
                {
                    $title =
                        New-Object System.Text.StringBuilder 256
                    [void][E5061Close.Win32]::GetWindowText(
                        $hwnd,
                        $title,
                        256
                    )
                    if ($title.ToString() -eq "About E5061B")
                    {
                        $script:stillOpen = $true
                        return $false
                    }
                }
                return $true
            }
            $verifyDelegate =
                [E5061Close.Win32+EnumWindowsProc]$verifyCallback
            [void][E5061Close.Win32]::EnumWindows(
                $verifyDelegate,
                [IntPtr]::Zero
            )
            if ($script:stillOpen)
            {
                "ERROR: About window still open" |
                    Out-File $log -Append
                exit 14
            }
            "SUCCESS: Firmware Revision closed" |
                Out-File $log -Append
            exit 0
        }
        catch
        {
            "ERROR: $($_.Exception.Message)" |
                Out-File $log -Append 
            exit 20
        }
        '''
        encoded_script = base64.b64encode(inner_ps.encode("utf-8")).decode("ascii")
        for remote_file in (remote_script, remote_b64, remote_log):
            self.session.run_ps(
                f"Remove-Item '{remote_file}' "
                f"-Force -ErrorAction SilentlyContinue"
            )
        chunk_size = 500
        for i in range(0, len(encoded_script), chunk_size):
            chunk = encoded_script[i:i + chunk_size]
            result = self.session.run_ps(
                f"[IO.File]::AppendAllText("
                f"'{remote_b64}',"
                f"'{chunk}')"
            )

            if result.status_code != 0:
                error = result.std_err.decode(errors="ignore").strip()
                return False, (f"Script transfer failed: {error}")
        result = self.session.run_ps(
            f"$b=[IO.File]::ReadAllText('{remote_b64}');"
            f"$d=[Convert]::FromBase64String($b);"
            f"[IO.File]::WriteAllBytes("
            f"'{remote_script}',$d)"
        )

        if result.status_code != 0:
            return False, "Could not create close script."

        reg_cmd = f'''
        $user = "{current_user}"
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File {remote_script}"
        $principal = New-ScheduledTaskPrincipal `
            -UserId $user `
            -LogonType Interactive `
            -RunLevel Highest
        $task = New-ScheduledTask `
            -Action $action `
            -Principal $principal
        Register-ScheduledTask `
            -TaskName "{task_name}" `
            -InputObject $task `
            -Force | Out-Null
        Start-ScheduledTask `
            -TaskName "{task_name}"
        '''
        try:
            result = self.session.run_ps(reg_cmd)
            if result.status_code != 0:
                error = result.std_err.decode(errors="ignore").strip()
                return False, (f"Failed starting close task: {error}")
            start_time = time.time()
            state = None
            last_result = None
            while time.time() - start_time < timeout:
                time.sleep(0.5)
                check = self.session.run_ps(
                    f"""
                    $task = Get-ScheduledTask `
                        -TaskName '{task_name}' `
                        -ErrorAction SilentlyContinue
                    if ($task)
                    {{
                        $info = Get-ScheduledTaskInfo `
                            -TaskName '{task_name}'
                        Write-Output "STATE=$($task.State)"
                        Write-Output "RESULT=$($info.LastTaskResult)"
                    }}
                    """
                )
                check_output = check.std_out.decode(errors="ignore").strip()
                for line in check_output.splitlines():
                    if line.startswith("STATE="):
                        state = line.split("=", 1)[1].strip()
                    elif line.startswith("RESULT="):
                        try:
                            last_result = int(line.split("=", 1)[1].strip())
                        except ValueError:
                            pass
                if state == "Ready":
                    break

            log_result = self.session.run_ps(
                f"Get-Content '{remote_log}' "
                f"-ErrorAction SilentlyContinue"
            )
            log_output = log_result.std_out.decode(errors="ignore").strip()
            print()
            print(" > E5061 Close Firmware:")
            print("----------------------------------------")
            print(log_output)
            print("----------------------------------------")
            print(f" > LastTaskResult: {last_result}")
            if state != "Ready":
                return False, "Close Firmware task timeout."
            if last_result == 0:
                return True, "Firmware Revision closed."
            if last_result == 12:
                return False, "About E5061B window not found."
            if last_result == 13:
                return False, "Close button not found."
            if last_result == 14:
                return False, "Close button clicked but window is still open."
            return False, (
                f"Close Firmware failed. "
                f"LastTaskResult={last_result}"
            )
        finally:
            self.session.run_ps(
                f"Unregister-ScheduledTask "
                f"-TaskName '{task_name}' "
                f"-Confirm:$false "
                f"-ErrorAction SilentlyContinue"
            )
            self.session.run_ps(
                f"Remove-Item '{remote_script}' "
                f"-Force -ErrorAction SilentlyContinue"
            )

    def open_windows_system(self, timeout=10):
        if not self.session:
            self.connect()

        result = self.session.run_cmd("quser")
        output = result.std_out.decode(errors="ignore").strip()
        username = None
        for line in output.splitlines():
            if "Active" in line:
                parts = line.replace(">", "").split()
                if parts:
                    username = parts[0]
                    break
        if not username:
            return False, "No active interactive user found."

        host_result = self.session.run_cmd("hostname")
        hostname = host_result.std_out.decode(errors="ignore").strip()
        current_user = f"{hostname}\\{username}"
        print(f" > Interactive user: {current_user}")
        print(" > Opening Windows System...")
        task_name = f"E5061_WindowsSystem_{int(time.time())}"
        remote_script = r"C:\Windows\Temp\E5061_Open_System.ps1"
        remote_b64 = r"C:\Windows\Temp\E5061_Open_System.b64"
        remote_log = r"C:\Windows\Temp\E5061_Open_System.txt"

        inner_ps = r'''
        $log = "C:\Windows\Temp\E5061_Open_System.txt"  
        "=== OPEN WINDOWS SYSTEM ===" |
            Out-File $log -Force 
        try
        {
            Start-Process "control.exe" `
                -ArgumentList "/name Microsoft.System"
            "System command sent" |
                Out-File $log -Append
            # Give Control Panel time to open
            Start-Sleep -Seconds 2
            $code = '
        [DllImport("user32.dll")]
        public static extern bool EnumWindows(
            EnumWindowsProc callback,
            IntPtr lParam);
        public delegate bool EnumWindowsProc(
            IntPtr hWnd,
            IntPtr lParam);
        [DllImport("user32.dll")]
        public static extern int GetWindowText(
            IntPtr hWnd,
            System.Text.StringBuilder lpString,
            int nMaxCount);
        [DllImport("user32.dll")]
        public static extern int GetClassName(
            IntPtr hWnd,
            System.Text.StringBuilder lpClassName,
            int nMaxCount);
        [DllImport("user32.dll")]
        public static extern bool IsWindowVisible(
            IntPtr hWnd); 
        [DllImport("user32.dll")]
        public static extern bool ShowWindow(
            IntPtr hWnd,
            int nCmdShow); 
        [DllImport("user32.dll")]
        public static extern bool SetForegroundWindow(
            IntPtr hWnd);
        '
            Add-Type `
                -MemberDefinition $code `
                -Name Win32 `
                -Namespace E5061System
            $script:systemHwnd = [IntPtr]::Zero
            $callback = {  
                param(
                    $hwnd,
                    $lparam
                )
                if (
                    -not [E5061System.Win32]::IsWindowVisible(
                        $hwnd
                    )
                )
                {
                    return $true
                }
                $title =
                    New-Object System.Text.StringBuilder 512
    
                $class =
                    New-Object System.Text.StringBuilder 256
                [void][E5061System.Win32]::GetWindowText(
                    $hwnd,
                    $title,
                    512
                )
                [void][E5061System.Win32]::GetClassName(
                    $hwnd,
                    $class,
                    256
                )  
                $windowTitle = $title.ToString()
                $className = $class.ToString()  
                if ($windowTitle)
                {
                    "HWND=$hwnd CLASS=$className TITLE=[$windowTitle]" |
                        Out-File $log -Append
                }  
                # Windows 7 / Embedded System window
                if (
                    $windowTitle -eq "System"
                )
                {
                    $script:systemHwnd = $hwnd  
                    return $false
                }
                return $true
            }
            $delegate =
                [E5061System.Win32+EnumWindowsProc]$callback
            for ($try = 1; $try -le 10; $try++)
            {
                $script:systemHwnd = [IntPtr]::Zero
                [void][E5061System.Win32]::EnumWindows(
                    $delegate,
                    [IntPtr]::Zero
                ) 
                if (
                    $script:systemHwnd -ne [IntPtr]::Zero
                )
                {
                    break
                }
                Start-Sleep -Milliseconds 500
            }
            if (
                $script:systemHwnd -eq [IntPtr]::Zero
            )
            {
                "ERROR: System window not found" |
                    Out-File $log -Append
                exit 12
            }
            "System HWND=$($script:systemHwnd)" |
                Out-File $log -Append
            [void][E5061System.Win32]::ShowWindow(
                $script:systemHwnd,
                3
            )
            "System MAXIMIZED" |
                Out-File $log -Append
            Start-Sleep -Milliseconds 500
            [void][E5061System.Win32]::SetForegroundWindow(
                $script:systemHwnd
            )
            Start-Sleep -Seconds 1
            "SUCCESS: Windows System opened and maximized" |
                Out-File $log -Append
            exit 0
        }
        catch
        {
            "ERROR: $($_.Exception.Message)" |
                Out-File $log -Append
            exit 20
        }
        '''
        encoded_script = base64.b64encode(inner_ps.encode("utf-8")).decode("ascii")
        for remote_file in (remote_script, remote_b64, remote_log):
            self.session.run_ps(
                f"Remove-Item '{remote_file}' "
                f"-Force -ErrorAction SilentlyContinue"
            )

        chunk_size = 500
        for i in range(0, len(encoded_script), chunk_size):
            chunk = encoded_script[i:i + chunk_size]
            result = self.session.run_ps(
                f"[IO.File]::AppendAllText("
                f"'{remote_b64}',"
                f"'{chunk}')"
            )
            if result.status_code != 0:
                error = result.std_err.decode(errors="ignore").strip()
                return False, (f"Script transfer failed: {error}")

        convert_cmd = (
            f"$b=[IO.File]::ReadAllText('{remote_b64}');"
            f"$d=[Convert]::FromBase64String($b);"
            f"[IO.File]::WriteAllBytes('{remote_script}',$d)"
        )
        result = self.session.run_ps(convert_cmd)
        if result.status_code != 0:
            error = result.std_err.decode(errors="ignore").strip()
            return False, (f"Failed creating System script: {error}")
        self.session.run_ps(
            f"Remove-Item '{remote_b64}' "
            f"-Force -ErrorAction SilentlyContinue"
        )
        reg_cmd = f'''
        $user = "{current_user}"
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File {remote_script}"  
        $principal = New-ScheduledTaskPrincipal `
            -UserId $user `
            -LogonType Interactive `
            -RunLevel Highest
        $task = New-ScheduledTask `
            -Action $action `
            -Principal $principal
        Register-ScheduledTask `
            -TaskName "{task_name}" `
            -InputObject $task `
            -Force | Out-Null
        Start-ScheduledTask `
            -TaskName "{task_name}"
        '''
        try:
            result = self.session.run_ps(reg_cmd)
            if result.status_code != 0:
                error = result.std_err.decode(errors="ignore").strip()
                return False, (f"Failed starting System task: {error}")
            start_time = time.time()
            state = None
            last_result = None
            while time.time() - start_time < timeout:
                time.sleep(0.5)
                check = self.session.run_ps(
                    f"""
                    $task = Get-ScheduledTask `
                        -TaskName '{task_name}' `
                        -ErrorAction SilentlyContinue         
                    if ($task)
                    {{
                        $info = Get-ScheduledTaskInfo `
                            -TaskName '{task_name}'            
                        Write-Output "STATE=$($task.State)"
                        Write-Output "RESULT=$($info.LastTaskResult)"
                    }}
                    """
                )
                check_output = check.std_out.decode(errors="ignore").strip()
                for line in check_output.splitlines():
                    if line.startswith("STATE="):
                        state = line.split("=", 1)[1].strip()
                    elif line.startswith("RESULT="):
                        try:
                            last_result = int(line.split("=", 1)[1].strip())
                        except ValueError:
                            pass
                if state == "Ready":
                    break
            log_result = self.session.run_ps(
                f"Get-Content '{remote_log}' "
                f"-ErrorAction SilentlyContinue"
            )
            log_output = log_result.std_out.decode(errors="ignore").strip()
            print()
            print(" > Windows System Log:")
            print("----------------------------------------")
            print(log_output)
            print("----------------------------------------")
            print(f" > LastTaskResult: {last_result}")

            if state != "Ready":
                return False, "Windows System task timeout."
            if last_result == 0:
                return True, ("Windows System opened and maximized.")
            if last_result == 12:
                return False, ("Windows System opened but window was not found.")
            if last_result == 20:
                return False, ("PowerShell error while opening Windows System.")
            return False, (
                f"Windows System task failed. "
                f"LastTaskResult={last_result}"
            )

        finally:
            self.session.run_ps(
                f"Unregister-ScheduledTask "
                f"-TaskName '{task_name}' "
                f"-Confirm:$false "
                f"-ErrorAction SilentlyContinue"
            )
            self.session.run_ps(
                f"Remove-Item '{remote_script}' "
                f"-Force -ErrorAction SilentlyContinue"
            )

    def open_system_information(self):
        if not self.session:
            self.connect()

        result = self.session.run_cmd("quser")
        output = result.std_out.decode(errors="ignore").strip()
        username = None
        for line in output.splitlines():
            if "Active" in line:
                parts = line.replace(">", "").split()
                if parts:
                    username = parts[0]
                    break
        if not username:
            return False, "No active interactive user found."
        host_result = self.session.run_cmd("hostname")
        hostname = host_result.std_out.decode(errors="ignore").strip()
        current_user = f"{hostname}\\{username}"
        print(f" > Interactive user: {current_user}")
        print(" > Opening System Information...")
        task_name = f"E5061_MSInfo_{int(time.time())}"
        inner_ps = (
            "Start-Process "
            "'C:\\Windows\\System32\\msinfo32.exe' "
            "-WindowStyle Maximized"
        )
        encoded_payload = base64.b64encode(inner_ps.encode("utf-16-le")).decode("utf-8")
        reg_cmd = f'''
        $user = "{current_user}"
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_payload}"
        $principal = New-ScheduledTaskPrincipal `
            -UserId $user `
            -LogonType Interactive `
            -RunLevel Highest
        $task = New-ScheduledTask `
            -Action $action `
            -Principal $principal
        Register-ScheduledTask `
            -TaskName "{task_name}" `
            -InputObject $task `
            -Force | Out-Null
        Start-ScheduledTask `
            -TaskName "{task_name}"
        '''
        result = self.session.run_ps(reg_cmd)
        if result.status_code != 0:
            error = result.std_err.decode(errors="ignore").strip()
            print(f" > Error: {error}")
            return False, error

        time.sleep(4)

        self.session.run_ps(
            f"Unregister-ScheduledTask "
            f"-TaskName '{task_name}' "
            f"-Confirm:$false "
            f"-ErrorAction SilentlyContinue"
        )

        return True, "System Information opened."

    def maximize_system_information(self, timeout=10):
        if not self.session:
            self.connect()

        result = self.session.run_cmd("quser")
        output = result.std_out.decode(errors="ignore").strip()
        username = None
        for line in output.splitlines():
            if "Active" in line:
                parts = line.replace(">", "").split()
                if parts:
                    username = parts[0]
                    break
        if not username:
            return False, "No active interactive user found."

        host_result = self.session.run_cmd("hostname")
        hostname = host_result.std_out.decode(errors="ignore").strip()
        current_user = f"{hostname}\\{username}"
        print(f" > Interactive user: {current_user}")
        print(" > Resizing System Information to full screen...")
        task_name = f"E5061_ResizeMSInfo_{int(time.time())}"
        remote_script = r"C:\Windows\Temp\E5061_Resize_MSInfo.ps1"
        remote_b64 = r"C:\Windows\Temp\E5061_Resize_MSInfo.b64"
        remote_log = r"C:\Windows\Temp\E5061_Resize_MSInfo.txt"

        inner_ps = r'''
        $log = "C:\Windows\Temp\E5061_Resize_MSInfo.txt"
        "=== RESIZE SYSTEM INFORMATION ===" |
            Out-File $log -Force
        try
        {
            $p =
                Get-Process msinfo32 `
                -ErrorAction Stop |
                Select-Object -First 1 
            $targetPid = $p.Id    
            "PID=$targetPid" |
                Out-File $log -Append
            $code = '
        [DllImport("user32.dll")]
        public static extern bool EnumWindows(
            EnumWindowsProc callback,
            IntPtr lParam);  
        public delegate bool EnumWindowsProc(
            IntPtr hWnd,
            IntPtr lParam);  
        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(
            IntPtr hWnd,
            out uint processId);   
        [DllImport("user32.dll")]
        public static extern int GetWindowText(
            IntPtr hWnd,
            System.Text.StringBuilder text,
            int count); 
        [DllImport("user32.dll")]
        public static extern int GetClassName(
            IntPtr hWnd,
            System.Text.StringBuilder text,
            int count);  
        [DllImport("user32.dll")]
        public static extern bool IsWindowVisible(
            IntPtr hWnd); 
        [DllImport("user32.dll")]
        public static extern bool SetWindowPos(
            IntPtr hWnd,
            IntPtr hWndInsertAfter,
            int X,
            int Y,
            int cx,
            int cy,
            uint uFlags);
        [DllImport("user32.dll")]
        public static extern bool GetWindowRect(
            IntPtr hWnd,
            out RECT rect);  
        public struct RECT
        {
            public int Left;
            public int Top;
            public int Right;
            public int Bottom;
        }
        ' 
            Add-Type `
                -MemberDefinition $code `
                -Name Win32 `
                -Namespace MSInfoResize
    
            $script:targetHwnd = [IntPtr]::Zero 
            $callback = {  
                param($hwnd, $lparam)   
                [uint32]$pidValue = 0 
                [void][MSInfoResize.Win32]::GetWindowThreadProcessId(
                    $hwnd,
                    [ref]$pidValue
                ) 
                if ($pidValue -ne $targetPid)
                {
                    return $true
                } 
                if (
                    -not [MSInfoResize.Win32]::IsWindowVisible(
                        $hwnd
                    )
                )
                {
                    return $true
                }
                $title =
                    New-Object System.Text.StringBuilder 512 
                $class =
                    New-Object System.Text.StringBuilder 256
                [void][MSInfoResize.Win32]::GetWindowText(
                    $hwnd,
                    $title,
                    512
                )  
                [void][MSInfoResize.Win32]::GetClassName(
                    $hwnd,
                    $class,
                    256
                ) 
                if (
                    $title.ToString() -eq "System Information" -and
                    $class.ToString() -eq "#32770"
                )
                {
                    $script:targetHwnd = $hwnd 
                    return $false
                }
                return $true
            }
    
            $delegate =
                [MSInfoResize.Win32+EnumWindowsProc]$callback
            [void][MSInfoResize.Win32]::EnumWindows(
                $delegate,
                [IntPtr]::Zero
            )

            if ($script:targetHwnd -eq [IntPtr]::Zero)
            {
                "ERROR: System Information window not found" |
                    Out-File $log -Append  
                exit 12
            }
     
            "HWND=$($script:targetHwnd)" |
                Out-File $log -Append

            Add-Type -AssemblyName System.Windows.Forms
    
            $screen =
                [System.Windows.Forms.Screen]::FromHandle(
                    $script:targetHwnd
                )
    
            $area = $screen.WorkingArea  
            "Screen X=$($area.X)" |
                Out-File $log -Append  
            "Screen Y=$($area.Y)" |
                Out-File $log -Append  
            "Screen Width=$($area.Width)" |
                Out-File $log -Append
            "Screen Height=$($area.Height)" |
                Out-File $log -Append
            $result =
                [MSInfoResize.Win32]::SetWindowPos(
                    $script:targetHwnd,
                    [IntPtr]::Zero,
                    $area.X,
                    $area.Y,
                    $area.Width,
                    $area.Height,
                    0x0040
                )  
            "SetWindowPos=$result" |
                Out-File $log -Append

            Start-Sleep -Seconds 1
    
            $rect =
                New-Object MSInfoResize.Win32+RECT 
            [void][MSInfoResize.Win32]::GetWindowRect(
                $script:targetHwnd,
                [ref]$rect
            )  
            $width =
                $rect.Right - $rect.Left  
            $height =
                $rect.Bottom - $rect.Top 
            "New Position=$($rect.Left),$($rect.Top)" |
                Out-File $log -Append  
            "New Size=${width}x${height}" |
                Out-File $log -Append  
            if (-not $result)
            {
                "ERROR: SetWindowPos failed" |
                    Out-File $log -Append   
                exit 13
            }  
            "SUCCESS: System Information resized" |
                Out-File $log -Append   
            exit 0
        }
        catch
        {
            "ERROR: $($_.Exception.Message)" |
                Out-File $log -Append   
            exit 20
        }
        '''

        encoded_script = base64.b64encode(inner_ps.encode("utf-8")).decode("ascii")
        for remote_file in (remote_script, remote_b64, remote_log):
            self.session.run_ps(
                f"Remove-Item '{remote_file}' "
                f"-Force -ErrorAction SilentlyContinue"
            )

        chunk_size = 500
        for i in range(0, len(encoded_script), chunk_size):
            chunk = encoded_script[i:i + chunk_size]
            result = self.session.run_ps(
                f"[IO.File]::AppendAllText("
                f"'{remote_b64}',"
                f"'{chunk}')"
            )
            if result.status_code != 0:
                error = result.std_err.decode(errors="ignore").strip()

                return False, (f"Script transfer failed: {error}")

        result = self.session.run_ps(
            f"$b=[IO.File]::ReadAllText('{remote_b64}');"
            f"$d=[Convert]::FromBase64String($b);"
            f"[IO.File]::WriteAllBytes("
            f"'{remote_script}',$d)"
        )
        if result.status_code != 0:
            return False, "Could not create resize script."

        reg_cmd = f'''
        $user = "{current_user}"
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File {remote_script}"
        $principal = New-ScheduledTaskPrincipal `
            -UserId $user `
            -LogonType Interactive `
            -RunLevel Highest
        $task = New-ScheduledTask `
            -Action $action `
            -Principal $principal
        Register-ScheduledTask `
            -TaskName "{task_name}" `
            -InputObject $task `
            -Force | Out-Null
        Start-ScheduledTask `
            -TaskName "{task_name}"
        '''
        try:
            result = self.session.run_ps(reg_cmd)
            if result.status_code != 0:
                error = result.std_err.decode(errors="ignore").strip()
                return False, (f"Failed starting resize task: {error}")

            start_time = time.time()
            state = None
            last_result = None
            while time.time() - start_time < timeout:
                time.sleep(0.5)
                check = self.session.run_ps(
                    f"""
                    $task = Get-ScheduledTask `
                        -TaskName '{task_name}' `
                        -ErrorAction SilentlyContinue              
                    if ($task)
                    {{
                        $info = Get-ScheduledTaskInfo `
                            -TaskName '{task_name}'             
                        Write-Output "STATE=$($task.State)"
                        Write-Output "RESULT=$($info.LastTaskResult)"
                    }}
                    """
                )

                check_output = check.std_out.decode(errors="ignore").strip()
                for line in check_output.splitlines():
                    if line.startswith("STATE="):
                        state = line.split("=", 1)[1].strip()
                    elif line.startswith("RESULT="):
                        try:
                            last_result = int(line.split("=", 1)[1].strip())
                        except ValueError:
                            pass
                if state == "Ready":
                    break

            log_result = self.session.run_ps(
                f"Get-Content '{remote_log}' "
                f"-ErrorAction SilentlyContinue"
            )
            log_output = log_result.std_out.decode(errors="ignore").strip()
            print()
            print(" > System Information Resize:")
            print("----------------------------------------")
            print(log_output)
            print("----------------------------------------")
            print(f" > LastTaskResult: {last_result}")

            if state != "Ready":
                return False, "Resize task timeout."
            if last_result == 0:
                return True, "System Information resized to full screen."
            if last_result == 12:
                return False, "System Information window not found."
            if last_result == 13:
                return False, "SetWindowPos failed."
            return False, (f"Resize failed. LastTaskResult={last_result}")
        finally:
            self.session.run_ps(
                f"Unregister-ScheduledTask "
                f"-TaskName '{task_name}' "
                f"-Confirm:$false "
                f"-ErrorAction SilentlyContinue"
            )
            self.session.run_ps(
                f"Remove-Item '{remote_script}' "
                f"-Force -ErrorAction SilentlyContinue"
            )

    def prepare_system_information(self):
        if not self.session:
            self.connect()

        result = self.session.run_cmd("quser")
        output = result.std_out.decode(errors="ignore").strip()
        username = None
        for line in output.splitlines():
            if "Active" in line:
                parts = line.replace(">", "").split()
                if parts:
                    username = parts[0]
                    break
        if not username:
            return False, "No active interactive user found."

        host_result = self.session.run_cmd("hostname")
        hostname = host_result.std_out.decode(errors="ignore").strip()
        current_user = f"{hostname}\\{username}"
        task_name = f"E5061_PrepareMSInfo_{int(time.time())}"

        inner_ps = (
            '$w = New-Object -ComObject WScript.Shell; '
            '$ok = $w.AppActivate("System Information"); '
            'if ($ok) { '
            'Start-Sleep -Milliseconds 500; '
            '$w.SendKeys("{TAB}"); '
            'Start-Sleep -Milliseconds 500; '
            'exit 0; '
            '} else { '
            'exit 12; '
            '}'
        )

        encoded_payload = base64.b64encode(inner_ps.encode("utf-16-le")).decode("utf-8")

        reg_cmd = f'''
        $user = "{current_user}"
        $action = New-ScheduledTaskAction `
            -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded_payload}"  
        $principal = New-ScheduledTaskPrincipal `
            -UserId $user `
            -LogonType Interactive `
            -RunLevel Highest
        $task = New-ScheduledTask `
            -Action $action `
            -Principal $principal
        Register-ScheduledTask `
            -TaskName "{task_name}" `
            -InputObject $task `
            -Force | Out-Null
        Start-ScheduledTask `
            -TaskName "{task_name}"
        '''

        result = self.session.run_ps(reg_cmd)

        if result.status_code != 0:
            error = result.std_err.decode(errors="ignore").strip()
            return False, error

        time.sleep(2)

        self.session.run_ps(
            f"Unregister-ScheduledTask "
            f"-TaskName '{task_name}' "
            f"-Confirm:$false "
            f"-ErrorAction SilentlyContinue"
        )

        return True, "TAB sent to System Information."

    def get_installed_keysight_licenses(self):

        if not self.session:
            if not self.connect():
                return []

        ps = r"""
        $ErrorActionPreference = 'Stop'
        $ProgressPreference = 'SilentlyContinue'
    
        $config = 'C:\ProgramData\Keysight\Licensing\Configuration\Variables\CCL_LICENSES_DIRS.config'
        $xmlPath = 'C:\Program Files (x86)\Agilent\ACCL\Licensing\bin\LicenseMetadata_VNA.xml'
    
        $features = @{}
        if (-not (Test-Path -LiteralPath $config)) {
            throw "License directory configuration not found"
        } 
        $dirs = @(
            Get-Content -LiteralPath $config |
                Where-Object {
                    $_.Trim() -and -not $_.Trim().StartsWith('#')
                }
        ) 
        foreach ($dir in $dirs) {
            $dir = $dir.Trim()
            if (-not (Test-Path -LiteralPath $dir)) {
                continue
            }
            Get-ChildItem -LiteralPath $dir -Filter '*.lic' -File `
                -Recurse -Force -ErrorAction SilentlyContinue |
                ForEach-Object {
                    $file = $_
                    Get-Content -LiteralPath $file.FullName -ErrorAction Stop |
                        ForEach-Object {
    
                            if ($_ -match '^\s*(FEATURE|INCREMENT)\s+(\S+)') {
    
                                $feature = $matches[2]
    
                                if (-not $features.ContainsKey($feature)) {
                                    $features[$feature] = ''
                                }
                            }
                        }
                }
        }  
        if (Test-Path -LiteralPath $xmlPath) {
    
            [xml]$xml = Get-Content -LiteralPath $xmlPath
    
            $nodes = $xml.SelectNodes('//*')
            foreach ($node in $nodes) {
                if ($node.LocalName -notin @('SWLicenseInfo', 'HWLicenseInfo')) {
                    continue
                }
                $nameNode = $node.SelectSingleNode(
                    './*[local-name()="SW_ID-FeatureName" or local-name()="HW_ID-FeatureName"]'
                )
                $descNode = $node.SelectSingleNode(
                    './*[local-name()="SW_Description" or local-name()="HW_Description"]'
                )
    
                if ($null -eq $nameNode) {
                    continue
                }
                $feature = $nameNode.InnerText.Trim()
    
                if (
                    $features.ContainsKey($feature) -and
                    $null -ne $descNode
                ) {
                    $features[$feature] = $descNode.InnerText.Trim()
                }
            }
        }
            $rows = @(
            foreach ($feature in ($features.Keys | Sort-Object)) {
    
                [PSCustomObject]@{
                    Feature = $feature
                    Description = $features[$feature]
                }
            }
        )
        ConvertTo-Json -InputObject $rows -Depth 3 -Compress
        """

        try:
            result = self.session.run_ps(ps)
            output = result.std_out.decode("utf-8", errors="replace").strip()
            errors = result.std_err.decode("utf-8", errors="replace").strip()

            if result.status_code != 0:
                print("ERROR:", errors)
                return []
            if not output:
                return []
            licenses = json.loads(output)

            if isinstance(licenses, dict):
                licenses = [licenses]

            for lic in licenses:
                print(
                    f"{lic['Feature']:<20} | "
                    f"{lic['Description']}"
                )

            return [
                [lic["Feature"], lic["Description"]]
                for lic in licenses
            ]

        except Exception as e:
            print(f"License extraction error: {e}")
            return []

    def e508x_license_full_query(self, licenses):
        results_list = []

        try:
            print("\n===== LICENSE FULL QUERY =====")
            print("Received licenses:", licenses)

            headers = [
                "Feature",
                "Description"
            ]

            license_table = create_data_table(
                title="Keysight License Manager",
                headers=[
                    f"{headers[0]:^22}",
                    f"{headers[1]:^80}"
                ]
            )

            for feature, description in licenses:
                license_table["rows"].append([
                    feature,
                    description
                ])

            print("Table type:", license_table.get("type"))
            print("Table title:", license_table.get("title"))
            print("Table rows:", len(license_table["rows"]))

            results_list.append(license_table)

            return results_list

        except Exception as error:
            print(
                f"License information error: "
                f"{type(error).__name__}: {error}"
            )

            if self.logger:
                self.logger.exception("Failed reading license information")

            return results_list

    def open_e508x_firmware_revision(self, timeout=30):
        if not self.session:
            self.connect()

        result = self.session.run_cmd("quser")
        output = result.std_out.decode(errors="replace")
        username = None
        for line in output.splitlines():
            if "Active" in line:
                parts = line.replace(">", "").split()
                if parts:
                    username = parts[0]
                    break

        if not username:
            return False, "No active interactive user found."

        host_result = self.session.run_cmd("hostname")
        hostname = host_result.std_out.decode(errors="replace").strip()
        current_user = f"{hostname}\\{username}"
        print(f" > Interactive user: {current_user}")
        unique_id = uuid.uuid4().hex[:8]
        task_name = f"E508x_About_{unique_id}"
        script_path = rf"C:\Windows\Temp\E508x_About_{unique_id}.ps1"
        b64_path = rf"C:\Windows\Temp\E508x_About_{unique_id}.b64"
        log_path = rf"C:\Windows\Temp\E508x_About_{unique_id}.txt"
        error_path = rf"C:\Windows\Temp\E508x_About_Error_{unique_id}.txt"

        inner_ps = rf"""
        $ErrorActionPreference = 'Stop'  
        $log = '{log_path}'  
        try {{ 
            "SCRIPT_STARTED" | Set-Content -LiteralPath $log
            # Find E5080B application
            $p = Get-Process -Name '835x' -ErrorAction Stop |
                 Where-Object {{ $_.MainWindowHandle -ne 0 }} |
                 Select-Object -First 1
            if (-not $p) {{
                throw "E5080B application window not found"
            }}  
            $p.Refresh()   
            $hwnd = $p.MainWindowHandle 
            Add-Content -LiteralPath $log -Value "PID=$($p.Id)"
            Add-Content -LiteralPath $log -Value "TITLE=$($p.MainWindowTitle)"
            Add-Content -LiteralPath $log -Value "HWND=$hwnd"
            Add-Content -LiteralPath $log -Value "SESSION=$($p.SessionId)"
    
            if ($hwnd -eq 0) {{
                throw "Main window handle is zero"
            }}   
            # Activate ENA application
            $wshell = New-Object -ComObject WScript.Shell 
            $activated = $wshell.AppActivate($p.Id)
            if (-not $activated) {{
                throw "Could not activate ENA window"
            }}
    
            Add-Content -LiteralPath $log -Value "WINDOW_ACTIVATED"  
            Start-Sleep -Milliseconds 700
    
            # Close an existing menu, if any
            $wshell.SendKeys("{{ESC}}")
            Start-Sleep -Milliseconds 300
    
            # Open Help menu (Alt+H)       
            $wshell.SendKeys("%h")
            Start-Sleep -Milliseconds 700           
            Add-Content -LiteralPath $log -Value "HELP_MENU_OPENED"
            
            # Select About NA (last item in Help menu)
            $wshell.SendKeys("{{DOWN 5}}")
            Start-Sleep -Milliseconds 500          
            Add-Content -LiteralPath $log -Value "ABOUT_SELECTED"
            
            # Open About NA
            $wshell.SendKeys("{{ENTER}}")
            Start-Sleep -Milliseconds 1200
    
            Add-Content -LiteralPath $log -Value "RESULT=ABOUT_COMMAND_SENT" 
            Add-Content -LiteralPath $log -Value "RESULT=ABOUT_COMMAND_SENT"
            exit 0
        }}
        catch {{
            $errorMessage = $_ | Out-String
            try {{
                [System.IO.File]::AppendAllText(
                    $log,
                    "`r`nERROR=" + $errorMessage
                )
            }}
            catch {{}} 
            exit 20
        }}
        """
        encoded = base64.b64encode(inner_ps.encode("utf-8")).decode("ascii")
        task_registered = False
        try:
            for path in (b64_path, script_path, log_path, error_path):
                self.session.run_ps(
                    f"Remove-Item -LiteralPath '{path}' "
                    f"-Force -ErrorAction SilentlyContinue"
                )

            chunk_size = 500
            for i in range(0, len(encoded), chunk_size):
                chunk = encoded[i:i + chunk_size]
                result = self.session.run_ps(f"[IO.File]::AppendAllText('{b64_path}', '{chunk}')")
                if result.status_code != 0:
                    error = result.std_err.decode(errors="replace")
                    return False, f"Script transfer failed: {error}"

            convert_cmd = (
                f"$b=[IO.File]::ReadAllText('{b64_path}');"
                f"$d=[Convert]::FromBase64String($b);"
                f"[IO.File]::WriteAllBytes('{script_path}',$d)"
            )

            result = self.session.run_ps(convert_cmd)
            if result.status_code != 0:
                error = result.std_err.decode(errors="replace")
                return False, f"Script creation failed: {error}"

            check_script = f"""
            $errors = $null
            $tokens = $null
            [System.Management.Automation.Language.Parser]::ParseFile(
                '{script_path}',
                [ref]$tokens,
                [ref]$errors
            ) | Out-Null  
            if ($errors.Count -gt 0) {{
                $errors | ForEach-Object {{
                    Write-Output "SYNTAX_ERROR: $($_.Message)"
                    Write-Output "LINE: $($_.Extent.StartLineNumber)"
                }}
            }}
            else {{
                Write-Output "SYNTAX_OK"
            }}
            """
            check_result = self.session.run_ps(check_script)
            syntax_output = check_result.std_out.decode("utf-8", errors="replace").strip()
            print("\n===== POWERSHELL SYNTAX CHECK =====")
            print(syntax_output)
            if (check_result.status_code != 0 or "SYNTAX_OK" not in syntax_output):
                return False, (f"PowerShell syntax check failed:\n{syntax_output}")

            reg_cmd = f"""
            $ErrorActionPreference = 'Stop'     
            $user = '{current_user}'     
            $action = New-ScheduledTaskAction `
                -Execute 'powershell.exe' `
                -Argument '-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "{script_path}" 2> "{error_path}"'       
            $principal = New-ScheduledTaskPrincipal `
                -UserId $user `
                -LogonType Interactive `
                -RunLevel Highest       
            $task = New-ScheduledTask `
                -Action $action `
                -Principal $principal     
            Register-ScheduledTask `
                -TaskName '{task_name}' `
                -InputObject $task `
                -Force | Out-Null   
            Start-ScheduledTask -TaskName '{task_name}'
            """

            result = self.session.run_ps(reg_cmd)
            if result.status_code != 0:
                error = result.std_err.decode(errors="replace")
                return False, f"Scheduled Task failed: {error}"
            task_registered = True

            start_time = time.time()
            state = None
            last_result = None
            log_output = ""
            while time.time() - start_time < timeout:
                time.sleep(0.5)
                check_cmd = f"""
                $task = Get-ScheduledTask `
                    -TaskName '{task_name}' `
                    -ErrorAction SilentlyContinue          
                if ($task) {{
                    $info = Get-ScheduledTaskInfo -TaskName '{task_name}'           
                    Write-Output "STATE=$($task.State)"
                    Write-Output "RESULT=$($info.LastTaskResult)"
                }}
                """
                check = self.session.run_ps(check_cmd)
                check_output = check.std_out.decode("utf-8", errors="replace").strip()
                for line in check_output.splitlines():
                    if line.startswith("STATE="):
                        state = line.split("=", 1)[1].strip()
                    elif line.startswith("RESULT="):
                        try:
                            last_result = int(line.split("=", 1)[1].strip())
                        except ValueError:
                            pass

                log_result = self.session.run_ps(
                    f"Get-Content -LiteralPath '{log_path}' "
                    f"-ErrorAction SilentlyContinue"
                )

                log_output = log_result.std_out.decode("utf-8", errors="replace").strip()
                if state == "Ready" and last_result is not None:
                    break
            print("\n===== E5080B ABOUT WINDOW =====")
            print(f"STATE={state}")
            print(f"LAST_RESULT={last_result}")

            if log_output:
                print("\n===== SCRIPT LOG =====")
                print(log_output)

            error_result = self.session.run_ps(
                f"Get-Content -LiteralPath '{error_path}' "
                f"-ErrorAction SilentlyContinue"
            )

            error_output = error_result.std_out.decode("utf-8", errors="replace").strip()
            if error_output:
                print("\n===== POWERSHELL ERROR LOG =====")
                print(error_output)

            if state != "Ready":
                return False, (
                    f"Task timeout. "
                    f"State={state}, LastTaskResult={last_result}"
                )

            if last_result == 0 and "RESULT=ABOUT_COMMAND_SENT" in log_output:
                return True, "Help -> About NA command sent successfully."

            return False, (
                f"About window task failed.\n"
                f"LastTaskResult={last_result}\n"
                f"LOG={log_output}\n"
                f"ERROR={error_output}"
            )

        finally:

            if task_registered:
                self.session.run_ps(
                    f"Unregister-ScheduledTask "
                    f"-TaskName '{task_name}' "
                    f"-Confirm:$false "
                    f"-ErrorAction SilentlyContinue"
                )

            self.session.run_ps(
                f"Remove-Item -LiteralPath '{script_path}','{b64_path}' "
                f"-Force -ErrorAction SilentlyContinue"
            )

    def open_e508x_about_window(self, action="open", scroll_steps=2, timeout=30):

        if not self.session:
            self.connect()

        if action not in ("open", "prepare_scroll", "scroll", "close"):
            return False, f"Invalid action: {action}"

        if action == "scroll":
            if not isinstance(scroll_steps, int) or not 1 <= scroll_steps <= 20:
                return False, "scroll_steps must be between 1 and 20"

        result = self.session.run_cmd("quser")
        output = result.std_out.decode(errors="replace")
        username = None
        for line in output.splitlines():
            if "Active" in line:
                parts = line.replace(">", "").split()
                if parts:
                    username = parts[0]
                    break

        if not username:
            return False, "No active interactive user found"

        result = self.session.run_cmd("hostname")
        hostname = result.std_out.decode(errors="replace").strip()
        current_user = f"{hostname}\\{username}"
        print(f" > Interactive user: {current_user}")
        print(f" > Action: {action}")
        uid = uuid.uuid4().hex[:10]
        task_name = f"E508xAbout_{uid}"
        script_path = rf"C:\Windows\Temp\E508xAbout_{uid}.ps1"
        b64_path = rf"C:\Windows\Temp\E508xAbout_{uid}.b64"
        log_path = rf"C:\Windows\Temp\E508xAbout_{uid}.log"

        cs_code = r"""
            using System;
            using System.Text;
            using System.Collections.Generic;
            using System.Runtime.InteropServices;
            public class E508xWindowApi
            {
                public delegate bool EnumWindowsProc(
                    IntPtr hWnd,
                    IntPtr lParam
                );
                [DllImport("user32.dll")]
                public static extern IntPtr GetForegroundWindow();      
                [DllImport("user32.dll")]
                public static extern bool SetForegroundWindow(IntPtr hWnd);        
                [DllImport("user32.dll")]
                public static extern bool IsWindow(IntPtr hWnd);      
                [DllImport("user32.dll")]
                public static extern bool IsWindowVisible(IntPtr hWnd);      
                [DllImport("user32.dll", CharSet = CharSet.Unicode)]
                public static extern int GetWindowText(
                    IntPtr hWnd,
                    StringBuilder text,
                    int count
                );       
                [DllImport("user32.dll")]
                public static extern uint GetWindowThreadProcessId(
                    IntPtr hWnd,
                    out uint processId
                );       
                [DllImport("user32.dll")]
                public static extern bool EnumWindows(
                    EnumWindowsProc callback,
                    IntPtr lParam
                );     
                public static string Title(IntPtr hWnd)
                {
                    StringBuilder sb = new StringBuilder(512);
                    GetWindowText(hWnd, sb, sb.Capacity);
                    return sb.ToString();
                }     
                public static List<IntPtr> WindowsForPid(uint targetPid)
                {
                    List<IntPtr> result = new List<IntPtr>();   
                    EnumWindows(delegate(IntPtr hWnd, IntPtr unused)
                    {
                        uint pid;
                        GetWindowThreadProcessId(hWnd, out pid);
        
                        if (pid == targetPid && IsWindowVisible(hWnd))
                            result.Add(hWnd);   
                        return true;
                    }, IntPtr.Zero);    
                    return result;
                }
            }
            """

        cs_b64 = base64.b64encode(cs_code.encode("utf-8")).decode("ascii")

        helpers_ps = """
            $cs = [Text.Encoding]::UTF8.GetString(
                [Convert]::FromBase64String('__CS_BASE64__')
            )
            Add-Type -TypeDefinition $cs -ErrorAction Stop
            function Write-Log {
                param([string]$Message)
                Add-Content -LiteralPath $log -Value $Message
            }
            function Get-ForegroundInfo {
                $h = [E508xWindowApi]::GetForegroundWindow()
                $title = [E508xWindowApi]::Title($h)
                return "HWND=$h TITLE=$title"
            }
            function Get-VnaWindows {
                $handles = [E508xWindowApi]::WindowsForPid(
                    [uint32]$p.Id
                )
                $items = @()
                foreach ($h in $handles) {
                    $items += [PSCustomObject]@{
                        Handle = $h
                        Title = [E508xWindowApi]::Title($h)
                    }
                }
                return $items
            }
            function Activate-Window {
                param(
                    [IntPtr]$Handle,
                    [string]$ExpectedTitle = ""
                )
                if (-not [E508xWindowApi]::IsWindow($Handle)) {
                    return $false
                }
                [void][E508xWindowApi]::SetForegroundWindow($Handle)
                Start-Sleep -Milliseconds 350
                $foreground = [E508xWindowApi]::GetForegroundWindow()
                if ($foreground -eq $Handle) {
                    return $true
                }
                if ($ExpectedTitle -ne "") {
                    [void]$wshell.AppActivate($ExpectedTitle)
                    Start-Sleep -Milliseconds 350
                    $foreground = [E508xWindowApi]::GetForegroundWindow()
                    if ($foreground -eq $Handle) {
                        return $true
                    }
                }
                return $false
            }
            """.replace("__CS_BASE64__", cs_b64)

        if action == "open":
            action_ps = r"""
                Write-Log "OPEN_START"
                if (-not $wshell.AppActivate($p.Id)) {
                    throw "Could not activate ENA application"
                }
                Start-Sleep -Milliseconds 700
                $wshell.SendKeys("{ESC}")
                Start-Sleep -Milliseconds 300
                $wshell.SendKeys("%h")
                Start-Sleep -Milliseconds 600
                $wshell.SendKeys("{DOWN 5}")
                Start-Sleep -Milliseconds 400
                $wshell.SendKeys("{ENTER}")
                Start-Sleep -Milliseconds 1100
                Write-Log "ABOUT_OPEN_COMMAND_SENT"
                $aboutTitle = "About Network Analyzer"
                if (-not $wshell.AppActivate($aboutTitle)) {
                    throw "Could not activate About Network Analyzer"
                }
                Start-Sleep -Milliseconds 500
                Write-Log "ABOUT_ACTIVATED"
                $before = @(Get-VnaWindows)
                foreach ($w in $before) {
                    Write-Log "BEFORE_MORE HWND=$($w.Handle) TITLE=$($w.Title)"
                }
                $wshell.SendKeys("{ENTER}")
                Start-Sleep -Milliseconds 1200
                Write-Log "MORE_ENTER_SENT"
                Write-Log ("FOREGROUND_AFTER_MORE=" + (Get-ForegroundInfo))
                $after = @(Get-VnaWindows)
                foreach ($w in $after) {
                    Write-Log "AFTER_MORE HWND=$($w.Handle) TITLE=$($w.Title)"
                }
                Write-Log "RESULT=MORE_READY"
                """
        elif action == "prepare_scroll":
            action_ps = r"""
                Write-Log "PREPARE_SCROLL_START"
                Write-Log ("FOREGROUND_BEFORE=" + (Get-ForegroundInfo))
                $aboutTitle = "About Network Analyzer"
                $windows = @(Get-VnaWindows)
                foreach ($w in $windows) {
                    Write-Log "VNA_WINDOW HWND=$($w.Handle) TITLE=$($w.Title)"
                }
                $aboutWindow = $windows |
                    Where-Object { $_.Title -eq $aboutTitle } |
                    Select-Object -First 1
                if (-not $aboutWindow) {
                    throw "About Network Analyzer window not found"
                }
                $foreground = [E508xWindowApi]::GetForegroundWindow()
                $moreWindow = $windows |
                    Where-Object {
                        $_.Handle -eq $foreground -and
                        $_.Handle -ne $aboutWindow.Handle -and
                        $_.Handle -ne $p.MainWindowHandle
                    } |
                    Select-Object -First 1
                if (-not $moreWindow) {
                    $moreWindow = $windows |
                        Where-Object {
                            $_.Handle -ne $aboutWindow.Handle -and
                            $_.Handle -ne $p.MainWindowHandle -and
                            $_.Title -ne ""
                        } |
                        Select-Object -First 1
                }
                if (-not $moreWindow) {
                    Write-Log "MORE_WINDOW_NOT_IDENTIFIED"
                    throw "More window could not be identified safely"
                }
                Write-Log "MORE_CANDIDATE_HWND=$($moreWindow.Handle)"
                Write-Log "MORE_CANDIDATE_TITLE=$($moreWindow.Title)"
                $focused = Activate-Window -Handle $moreWindow.Handle `
                                           -ExpectedTitle $moreWindow.Title
            
                Write-Log "MORE_FOCUS_RESULT=$focused"
                Write-Log ("FOREGROUND_AFTER_MORE_FOCUS=" + (Get-ForegroundInfo))
                if (-not $focused) {
                    throw "Could not focus More window"
                }
                $wshell.SendKeys("{ESC}")
                Start-Sleep -Milliseconds 900
                Write-Log "MORE_ESC_SENT"
                Write-Log ("FOREGROUND_AFTER_ESC=" + (Get-ForegroundInfo))
                $stillOpen = [E508xWindowApi]::IsWindow(
                    $moreWindow.Handle
                )
                Write-Log "MORE_EXISTS_AFTER_ESC=$stillOpen"
                # Try ENTER if ESC did not close More
                if ($stillOpen) {
                    Write-Log "TRYING_ENTER_TO_CLOSE_MORE"
                    $focused = Activate-Window -Handle $moreWindow.Handle `
                                               -ExpectedTitle $moreWindow.Title
                    if (-not $focused) {
                        throw "More still exists and cannot be focused"
                    }
                    $wshell.SendKeys("{ENTER}")
                    Start-Sleep -Milliseconds 900
                    Write-Log "MORE_ENTER_SENT"
                    $stillOpen = [E508xWindowApi]::IsWindow(
                        $moreWindow.Handle
                    )
                    Write-Log "MORE_EXISTS_AFTER_ENTER=$stillOpen"
                }
                if ($stillOpen) {
                    throw "More window is still open after ESC and ENTER"
                }
                Write-Log "MORE_CLOSED"
                if (-not $wshell.AppActivate($aboutTitle)) {
                    throw "Could not restore About window focus"
                }
                Start-Sleep -Milliseconds 600
                Write-Log "ABOUT_FOCUS_RESTORED"
                Write-Log ("FOREGROUND_AFTER_ABOUT=" + (Get-ForegroundInfo))
                $wshell.SendKeys("{LEFT 3}")
                Start-Sleep -Milliseconds 500
                Write-Log "LEFT_3_SENT"
                $wshell.SendKeys("{DOWN 6}")
                Start-Sleep -Milliseconds 700
                
                Write-Log "DOWN_6_SENT"
                Write-Log "RESULT=SCROLL_READY"
                """
        elif action == "close":
            action_ps = r"""
                Write-Log "CLOSE_ABOUT_START"
                $aboutTitle = "About Network Analyzer"
                if (-not $wshell.AppActivate($aboutTitle)) {
                    throw "Could not activate About Network Analyzer"
                }
                Start-Sleep -Milliseconds 500
                $wshell.SendKeys("{ESC}")
                Start-Sleep -Milliseconds 700
                Write-Log "ABOUT_ESC_SENT"  
                $remaining = @(Get-VnaWindows | Where-Object {
                    $_.Title -eq $aboutTitle
                })    
                if ($remaining.Count -gt 0) {
                    throw "About window is still open after ESC"
                }    
                Write-Log "ABOUT_CLOSED"
                Write-Log "RESULT=ABOUT_CLOSED"
                """
        else:

            action_ps = """
                Write-Log "SCROLL_START"
                $aboutTitle = "About Network Analyzer"
                if (-not $wshell.AppActivate($aboutTitle)) {
                    throw "Could not activate About window"
                }
                Start-Sleep -Milliseconds 350
                $wshell.SendKeys("{DOWN __STEPS__}")
                Start-Sleep -Milliseconds 500
                Write-Log "DOWN_SENT=__STEPS__"
                Write-Log "RESULT=SCROLL_SENT"
                """.replace("__STEPS__", str(scroll_steps))

        inner_ps = (
                "$ErrorActionPreference = 'Stop'\n"
                f"$log = '{log_path}'\n"
                f"$actionName = '{action}'\n"
                + r"""
                try {
                    "SCRIPT_STARTED" | Set-Content -LiteralPath $log
                    Add-Content -LiteralPath $log -Value "ACTION=$actionName"
                    $p = Get-Process -Name '835x' -ErrorAction Stop |
                         Where-Object { $_.MainWindowHandle -ne 0 } |
                         Select-Object -First 1
                    if (-not $p) {
                        throw "E5080B application window not found"
                    }
                    $p.Refresh()
                    Add-Content -LiteralPath $log -Value "PID=$($p.Id)"
                    Add-Content -LiteralPath $log -Value "TITLE=$($p.MainWindowTitle)"
                    Add-Content -LiteralPath $log -Value "SESSION=$($p.SessionId)"
                    $wshell = New-Object -ComObject WScript.Shell
                """
                + helpers_ps
                + "\n"
                + action_ps
                + r"""
        exit 0
    }
    catch {
        $errorMessage = $_ | Out-String
        try {
            [System.IO.File]::AppendAllText(
                $log,
                "`r`nERROR=" + $errorMessage
            )
        }
        catch {}
        exit 20
    }
    """
        )

        encoded = base64.b64encode(inner_ps.encode("utf-8")).decode("ascii")
        task_registered = False
        try:
            for path in (b64_path, script_path, log_path):
                self.session.run_ps(
                    f"Remove-Item -LiteralPath '{path}' "
                    f"-Force -ErrorAction SilentlyContinue"
                )
            for i in range(0, len(encoded), 500):
                chunk = encoded[i:i + 500]
                result = self.session.run_ps(f"[IO.File]::AppendAllText('{b64_path}', '{chunk}')")
                if result.status_code != 0:
                    return False, (
                            "Script transfer failed: "
                            + result.std_err.decode(errors="replace")
                    )
            convert_cmd = (
                f"$b=[IO.File]::ReadAllText('{b64_path}');"
                f"$d=[Convert]::FromBase64String($b);"
                f"[IO.File]::WriteAllBytes('{script_path}',$d)"
            )
            result = self.session.run_ps(convert_cmd)
            if result.status_code != 0:
                return False, (
                        "Script creation failed: "
                        + result.std_err.decode(errors="replace")
                )

            check_script = f"""
                $errors = $null
                $tokens = $null
                [System.Management.Automation.Language.Parser]::ParseFile(
                    '{script_path}',
                    [ref]$tokens,
                    [ref]$errors
                ) | Out-Null
                if ($errors.Count -gt 0) {{
                    $errors | ForEach-Object {{
                        Write-Output "SYNTAX_ERROR: $($_.Message)"
                        Write-Output "LINE: $($_.Extent.StartLineNumber)"
                    }}
                }}
                else {{
                    Write-Output "SYNTAX_OK"
                }}
                """

            check_result = self.session.run_ps(check_script)
            syntax_output = check_result.std_out.decode("utf-8", errors="replace").strip()
            print("\n===== POWERSHELL SYNTAX CHECK =====")
            print(syntax_output)
            if (check_result.status_code != 0 or "SYNTAX_OK" not in syntax_output):
                return False, (f"PowerShell syntax error:\n{syntax_output}")

            reg_cmd = f"""
                $ErrorActionPreference = 'Stop'
                $user = '{current_user}'
                $action = New-ScheduledTaskAction `
                    -Execute 'powershell.exe' `
                    -Argument '-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "{script_path}"'
                $principal = New-ScheduledTaskPrincipal `
                    -UserId $user `
                    -LogonType Interactive `
                    -RunLevel Highest
                $task = New-ScheduledTask `
                    -Action $action `
                    -Principal $principal
                Register-ScheduledTask `
                    -TaskName '{task_name}' `
                    -InputObject $task `
                    -Force | Out-Null
                Start-ScheduledTask -TaskName '{task_name}'
                """

            result = self.session.run_ps(reg_cmd)
            if result.status_code != 0:
                return False, ("Scheduled Task failed: " + result.std_err.decode(errors="replace"))
            task_registered = True
            start_time = time.time()
            state = None
            last_result = None
            log_output = ""

            expected_result = {
                "open": "RESULT=MORE_READY",
                "prepare_scroll": "RESULT=SCROLL_READY",
                "scroll": "RESULT=SCROLL_SENT",
                "close": "RESULT=ABOUT_CLOSED"
            }[action]

            while time.time() - start_time < timeout:
                time.sleep(0.5)
                check_cmd = f"""
                    $task = Get-ScheduledTask `
                        -TaskName '{task_name}' `
                        -ErrorAction SilentlyContinue
                    if ($task) {{
                        $info = Get-ScheduledTaskInfo -TaskName '{task_name}'
                        Write-Output "STATE=$($task.State)"
                        Write-Output "RESULT=$($info.LastTaskResult)"
                    }}
                    """

                check = self.session.run_ps(check_cmd)
                check_output = check.std_out.decode("utf-8", errors="replace").strip()
                for line in check_output.splitlines():
                    if line.startswith("STATE="):
                        state = line.split("=", 1)[1].strip()
                    elif line.startswith("RESULT="):
                        try:
                            last_result = int(
                                line.split("=", 1)[1].strip()
                            )
                        except ValueError:
                            pass

                log_result = self.session.run_ps(
                    f"Get-Content -LiteralPath '{log_path}' "
                    f"-ErrorAction SilentlyContinue"
                )

                log_output = log_result.std_out.decode("utf-8", errors="replace").strip()
                if expected_result in log_output:
                    break
                if "ERROR=" in log_output:
                    break
                if (
                        state == "Ready"
                        and last_result is not None
                        and last_result != 0
                ):
                    break
            print("\n===== E5080B ABOUT WINDOW =====")
            print(f"ACTION={action}")
            print(f"STATE={state}")
            print(f"LAST_RESULT={last_result}")
            print(log_output)
            if (expected_result in log_output and "ERROR=" not in log_output):
                return True, f"{action} completed."

            return False, (
                f"Action failed or timed out.\n"
                f"ACTION={action}\n"
                f"STATE={state}\n"
                f"LAST_RESULT={last_result}\n"
                f"LOG={log_output}"
            )
        finally:
            if task_registered:
                self.session.run_ps(
                    f"Unregister-ScheduledTask "
                    f"-TaskName '{task_name}' "
                    f"-Confirm:$false "
                    f"-ErrorAction SilentlyContinue"
                )
            self.session.run_ps(
                f"Remove-Item -LiteralPath '{script_path}','{b64_path}' "
                f"-Force -ErrorAction SilentlyContinue"
            )

    def capture_e508x_firmware_info(self, serial_number, results_list, worker, logger):

        page_count = 1
        capture_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        screenshot_name = f"System_Info_{capture_id}"

        # 1. Open About + More
        success, message = self.open_e508x_about_window(action="open")
        if not success:
            raise RuntimeError(message)

        # 2. Screenshot About + More
        image = self.screenshot_network(folder="Firmware", serial_number=serial_number, picture_name=f"Firmware More_{screenshot_name}", shot=page_count, full_screen=True)
        if not image:
            raise RuntimeError("Failed to capture More screenshot")

        print(" > More screenshot completed.")
        report_step(name=f"Firmware Information ScreenShot #N{page_count}", status="INFO", progress=26, results_list=results_list, value=f"Firmware Information ScreenShot #N{page_count}", image_path=image, worker=worker, logger=logger)
        page_count = page_count + 1

        # 3. Close More, restore About focus and press LEFT 3
        success, message = self.open_e508x_about_window(action="prepare_scroll")
        print(success, message)
        if not success:
            raise RuntimeError(message)

        # 4. SCREENSHOT - ABOUT ONLY
        image = self.screenshot_network(folder="Firmware", serial_number=serial_number, picture_name=f"Firmware About_{screenshot_name}",  shot=page_count, window_title="About Network Analyzer", full_screen=False)
        if not image:
            raise RuntimeError("About screenshot failed")
        print(" > About screenshot completed.")
        report_step(name=f"Firmware Information ScreenShot #N{page_count}", status="INFO", progress=28, results_list=results_list, value=f"Firmware Information ScreenShot #N{page_count}", image_path=image, worker=worker, logger=logger)

        # 5. CLOSE ABOUT WINDOW
        success, message = self.open_e508x_about_window(action="close")
        print(success, message)
        if not success:
            raise RuntimeError(message)

def device_remote_to_administrator(target_ip, worker=None, logger=None):
    results_list = []
    admin_user = "Administrator"
    admin_password = ""
    instrument_user = "Instrument"
    exe_destination_file = r'C$\Windows\Temp'
    bat_file_name = "InterlligentTester.bat"
    exe_file_name = "nircmd.exe"
    source = load_configFile("bat_mircmd_path")

    try:
        updater = WINconn(target_ip, admin_user, admin_password)
        admin_passwords = get_passwords("Administrator", load_configFile("password_path"))
        inst_passwords = get_passwords("Instrument", load_configFile("password_path"))
        real_admin_password = updater.check_password( username="Administrator", passwords=admin_passwords)
        real_inst_password = updater.check_password(username="Instrument", passwords=inst_passwords)
        admin_password = real_admin_password
        instrument_password = real_inst_password
        updater.username = "Administrator"
        updater.password = real_admin_password
        updater.session = None

        updater.copy_file_to_remote(target_ip, admin_user, admin_password, source, exe_file_name, None, exe_destination_file)
        report_step("Copy the mircmd file to the device", "PASS", 1, results_list, " ", None, worker, logger)
        updater.setup_local_machine(worker, logger)

        if not updater.wait_for_winrm_port(timeout=90, worker=worker, logger=logger):
            report_step("WinRM is not ready - trying bootstrap via schtasks", "INFO", 1, results_list, " ", None, worker, logger)
            if not updater.bootstrap_winrm_via_schtasks(admin_user, admin_password):
                print(" > Failed to bootstrap WinRM")
                report_step("Failed to bootstrap WinRM", "FAIL", 1, results_list, " ", None, worker, logger)
                return False
            updater.setup_local_machine(worker, logger)

        report_step("Connect to remote device", "PASS", 1, results_list, " ", None, worker, logger)

        if not updater.connect():
            report_step("Failed to connect to remote device using WinRM", "FAIL", 1, results_list, " ", None, worker,
                        logger)
            return False

        current_user = updater.get_current_user()
        print(f" > Current active user: {current_user}")
        report_step(f"Current active user: {current_user}", "INFO", 2, results_list, " ", None, worker, logger)

        if current_user is None:
            report_step("Cannot detect current active user", "FAIL", 2, results_list, " ", None, worker, logger)
            return False

        if current_user != "Administrator":
                report_step("Switch user to Administrator", "INFO", 2, results_list, " ", None, worker, logger)
                if not updater.switch_remote_to_administrator(worker, logger, admin_user, admin_password, domain="."):
                    report_step("Failed to switch remote PC to Administrator", "FAIL", 2, results_list, " ", None, worker, logger)
                    return False

                report_step("User is Administrator", "PASS", 3, results_list, " ", None, worker, logger)

        else:
             report_step("User is already Administrator", "PASS", 3, results_list, " ", None, worker, logger)

        updater.copy_file_to_remote(target_ip, admin_user, admin_password, source, bat_file_name)
        report_step("Copy the BAT file to the device", "PASS", 4, results_list, " ", None, worker, logger)
        report_step("Running the BAT file on the device 90 sec..Please wait doing somethings in the background", "INFO", 4, results_list, " ", None, worker, logger)
        updater.run_bat_file()
        report_step("Remote Device to by control by local computer", "PASS", 4, results_list, " ", None, worker, logger)
        updater.set_auto_login_user(instrument_user, instrument_password, domain=".")
        report_step("Auto set user to Instrument", "INFO", 5, results_list, " ", None, worker, logger)
        model = updater.get_model()
        report_step(f"Model Device is: {model}", "INFO", 5, results_list, " ", None, worker, logger)

        if f"{model[:3]}xxB" == "N90xxB":
            app_path = updater.find_launch_xsa_path()
            print(app_path)
            report_step(f"Launch XSA Path: {app_path}", "INFO", 6, results_list, " ", None, worker, logger)
            if updater.launch_app(app_path):
                report_step("Launch XSA Program", "PASS", 8, results_list, " ", None, worker, logger)
                updater.press_no_app_popup(20)
            else:
                report_step("Failed to launch XSA Program", "FAIL", 8, results_list, " ", None, worker, logger)
                return f"{model[:4]}x"

        if f"{model[:3]}xxB" == "E50xxB":
            app_path = updater.find_launch_network_path()
            print(app_path)
            report_step(f"Launch Network Path: {app_path}", "INFO", 6, results_list, " ", None, worker, logger)
            if updater.launch_app(app_path):
                report_step("Launch Network Program", "PASS", 8, results_list, " ", None, worker, logger)
                updater.press_no_app_popup(20)
            else:
                report_step("Failed to launch Network Program", "FAIL", 8, results_list, " ", None, worker, logger)
                return f"{model[:3]}xxB"

        return f"{model[:4]}x"

    except Exception as e:
        print(f"Error connecting to WIN user: {e}")
        report_step(f"Error connecting to WIN user: {e}", "FAIL", 8, results_list, " ", None, worker, logger)

if __name__ == "__main__":

    target_ip = "192.168.1.200"
    serial_number = "MY59202793"
    user = "Administrator"
    password = "Keysight4u!"

    updater = WINconn(target_ip, user, password)
    updater.capture_e508x_firmware_info(serial_number)

    #pdater.uninstall_all_calibration_advisors(False)
    #updater.close_firmware_revision()
    #updater.open_windows_system()
    #Firmware_image = updater.screenshot_network("Firmware", "MY49810546", "screenshot_name", "1")
    #updater.open_system_information()
    #time.sleep(2)
    #updater.prepare_system_information()
    #time.sleep(1)
    #updater.maximize_system_information()
    #time.sleep(5)
    #updater.capture_all_system_information(serial_number, results_list, worker, logger)
    #result, message = updater.open_firmware_revision()
    #print(result, message)
    #Firmware_image = updater.screenshot_firmware("Firmware", "MY49810546", "screenshot_name", "1")



    """updater.setup_local_machine()
    updater.disable_windows_update_notifications()"""

    """current_user = updater.get_current_user()
    print(f" > Current active user: {current_user}")

    if current_user is None:
        print(" > Cannot connect to remote device. Stop.")
        sys.exit(1)

    if current_user != "Administrator":
        if updater.switch_remote_to_administrator(admin_user="Administrator", admin_password=password, domain="."):
            updater.run_bat_file()
            updater.set_auto_login_user(username="Instrument", password="measure4u", domain=".")
        else:
            print("Failed to switch remote PC to Administrator")
            sys.exit(1)
    else:
        updater.set_auto_login_user(username="Instrument", password="measure4u", domain=".")
        updater.run_bat_file()
    print(updater.find_launch_xsa_path())
    if updater.launch_xsa():
        updater.press_no_xsa_popup(20)
    updater.is_xsa_running()"""

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




