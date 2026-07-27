from Communication.WINconnection import WINconn
from TestingEquipment.SignalAnaLyzer.SignalAnalyzer import *
from Communication.WEBconnection import *
from pathlib import Path
import time
import os

## ---------------------  Strings ------------------------------##
IVI_RESET = "*RST"
IVI_IDENT = "*IDN?"
## ---------------------  Displays  ----------------------------##
IVI_DISPLAY_GET_TRACE = ":TRAC? TRACE1"
## ---------------------  Settings  ----------------------------##
IVI_SETTING_SET_SPAN = ":SENSE:FREQ:SPAN"

#url = "https://www.keysight.com/us/en/lib/software-detail/instrument-firmware-software/n9000b-cxa-signal-analyzer-instrument-software-2674911.html"
#guide = Path.cwd().parent.parent

# Created by Benny Aberman - 054-3220104
# N90xxB device class
    # Getting the license data for the device function
    # Capture all Error, Hardware, LXI, Hw_statistics for the device function
    # Open the system information screen on the device function
    # Main N90xxB function

class N90XXB(SignalSignalAnalyzer):

    # Getting the license data for the device function
    def deep_license_scan(self):
        print("\n--- Deep License Scan ---")

        commands = {
            "Standard Options (*OPT)": "*OPT?",
            "Feature Capabilities": ":INST:CAT?",
            "List Licenses":":SYSTem:LKEY:LIST?",
            "Software Version Date":":SYSTem:SOFTware:VERSion:DATE?",
        }

        for desc, cmd in commands.items():
            try:
                result = self.query(cmd)
                if result and len(result.strip()) > 2:
                    print(f"{desc}: {result.strip()}")
                else:
                    print(f"{desc}: [Empty or Not Supported]")
            except:
                print(f"{desc}: [Command Failed]")

    # Capture all Error, Hardware, LXI, HW_statistics for the device function
    def capture_other_screen(self, results_list, worker, logger):
        try:
            commands = {
                "Errors":"ERR",
                "Hardware": "HARD",
                "LXI": "LXI",
                "Hw_statistics": "HWST",
            }
            serialNumber = self.get_idn()[2]

            for desc, cmd in commands.items():

                print(f"Capture {desc} Screenshot -> by :SYST:SHOW {cmd}")
                try:
                    self.write(f":SYST:SHOW {cmd}")
                except Exception as e:
                    print(f"Error Screen Shot: {e}")

                # Wait for the operation to complete
                self.query("*OPC?")

                # 1. Save the screen image to the instrument's internal storage first
                # Use .png for modern MXA/X-Series; .bmp is also supported
                #print("Saving screen image on instrument...")
                self.write(':MMEMory:STORe:SCReen "D:\\temp_scr.png"')

                # Wait for the operation to complete
                self.query("*OPC?")

                # 2. Transfer the file data from the instrument to the PC
                #print("Transferring file to PC...")
                image_data = self.instr.query_binary_values(':MMEMory:DATA? "D:\\temp_scr.png"',
                                                     datatype='B',
                                                     container=bytes)

                # 3. Save to local file
                guide = load_configFile("screenShot_path")
                os.makedirs(f"{guide}\\{serialNumber}", exist_ok=True)
                local_image = f"{guide}\\{serialNumber}\\{serialNumber}_{desc}.png"
                with open(local_image, "wb") as f:
                    f.write(image_data)
                time.sleep(0.5)
                report_step(name=f"Capture {desc} Screen",status="INFO", progress=25, results_list=results_list, value=f"Captured {desc} Screenshot", image_path=local_image, worker=worker, logger=logger)
                # Optional: Clean up the temporary file on the instrument
                self.write(':MMEMory:DELete "D:\\temp_scr.png"')

        except Exception as e:
            print(f"Error: {e}")

    # Open the system information screen on the device function
    def open_system_screen(self):
        try:
            commands = {
                "SYSTem": "SYST",
            }
            serialNumber = self.get_idn()[2]
            os.makedirs(f"../../ScreenShot/{serialNumber}", exist_ok=True)

            for desc, cmd in commands.items():
                try:
                    self.write(f":SYST:SHOW {cmd}")
                except Exception as e:
                    print(f"Error Screen Shot: {e}")
                    continue

                self.query("*OPC?")


        except Exception as e:
            print(f"Error: {e}")

# Main N90xxB function
def N90XXB_System_Test(target_ip,worker=None, logger=None, run_win_update=True, run_firmware_update=True):
    results_list = []
    download_results = []
    device = None
    device_Model = "None"
    serial_number = "None"
    admin_user = "Administrator"
    admin_password = "Keysight4u!"
    exe_destination_file = r'C$\Windows\Temp'
    bat_file_name = "InterlligentTester.bat"
    exe_file_name = "nircmd.exe"
    source = load_configFile("bat_mircmd_path")
    firmware_info_table = create_text_table("firmware Information")
    requested_os = "Windows 10"
    download_path = load_configFile("download_path")
    if download_path is None:
        download_path = Path.home() / "Downloads"
    download_defult = Path.home() / "Downloads"

    download = True
    time.sleep(5)
    try:
        device = N90XXB(target_ip, logger)
        if device.connect():
            report_step("N90XXB Device is replaying", "PASS", 8, results_list, " ", None, worker, logger)
            device.disconnect()
        else:
            report_step("N90XXB Device isn't replaying", "FAIL", 8, results_list, " ", None, worker, logger)
            device.disconnect()
        if check_progress(worker): return serial_number, device_Model, results_list
        report_step("Connection to N90XXB Windows Device", "RUNNING", 10, results_list, " ", None, worker, logger)
        windows_control = WINconn(target_ip, admin_user, admin_password)
        admin_passwords = get_passwords("Administrator", load_configFile("password_path"))
        real_admin_password = windows_control.check_password(username="Administrator", passwords=admin_passwords)
        admin_password = real_admin_password
        windows_control.username = "Administrator"
        windows_control.password = real_admin_password
        windows_control.session = None
        if windows_control.connect():
            report_step("Connection to N90XXB Windows Device", "PASS", 10, results_list, " ", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
            #windows_control.copy_file_to_remote(target_ip, admin_user, admin_password, source, bat_file_name)
            #report_step("Copy the BAT file to the device", "PASS", 6, results_list, " ", None, worker, logger)
            #if check_progress(worker): return serial_number, device_Model, results_list
            #windows_control.copy_file_to_remote(target_ip, admin_user, admin_password, source, exe_file_name, None, exe_destination_file)
            #report_step("Copy the mircmd file to the device", "PASS", 8, results_list, " ", None, worker, logger)
            #if check_progress(worker): return serial_number, device_Model, results_list
            #windows_control.setup_local_machine(worker, logger)
            #report_step("Local computer command to control device", "PASS", 10, results_list, " ", None, worker, logger)
            #if check_progress(worker): return serial_number, device_Model, results_list
            #windows_control.run_bat_file()
            #report_step("Remote Device to by control by local computer", "PASS", 12, results_list, " ", None,worker, logger)
            #if check_progress(worker): return serial_number, device_Model, results_list
            requested_os = windows_control.get_remote_os(target_ip, admin_user, admin_password)
            report_step("N90XXB Device OS", "INFO", 14, results_list, requested_os, None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
        else:
            report_step("Connection to N90XXB Windows Device", "FAIL", 4, results_list, " ", None, worker, logger)
            report_step("Copy the BAT file to the device", "FAIL", 6, results_list, " ", None, worker, logger)
            report_step("Copy the mircmd file to the device", "FAIL", 8, results_list, " ", None, worker, logger)
            report_step("local computer command to control device", "FAIL", 10, results_list, " ", None, worker, logger)
            report_step("Remote Device to by control by local computer", "FAIL", 12, results_list, " ", None, worker, logger)
            report_step("N90XXB Device OS", "FAIL", 14, results_list, " ", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list


    except Exception as e:
        print(f"Error: {e}")
        return serial_number, device_Model, results_list

    try:
        if  device.connect() and windows_control.connect():
            device_Model = device.get_idn()[1]
            serial_number = device.get_idn()[2]
            firmwareUnitVer = device.get_idn()[3]
            if check_progress(worker): return serial_number, device_Model, results_list
            report_step("N90XXB Connected", "PASS", 15, results_list, " ", None, worker, logger)
            results_list.extend(device.system_full_query())
            report_step("Get System information", "PASS", 20, results_list, " ", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
            print("\n")
            output, external_results = device.license_full_query(":SYSTem:LKEY:LIST?")
            print(output)
            results_list.extend(external_results)
            report_step("Keysight License Manager", "PASS", 25, results_list, " ", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
            device.alignment_Now_All(results_list, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
            device.capture_other_screen(results_list, worker, logger)
            report_step("Screen Shots all Data (Errors, Hardware, LXI, HW_Statistics)", "PASS", 35, results_list, "Done", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
            time.sleep(5)
            device.open_system_screen()
            report_step("Open System Information", "PASS", 36, results_list, " ", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
            device.disconnect()
            windows_control.capture_all_systems(serial_number, results_list, worker, logger)
            report_step("Screen Shots System Information", "PASS", 40, results_list, "Done", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
            time.sleep(2)
            print(windows_control.open_license_manager())
            time.sleep(30)
            report_step("Open License Window", "PASS", 41, results_list, " ", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
            time.sleep(5)
            windows_control.capture_all_licenses(serial_number, results_list, worker, logger)
            report_step("Screen Shots License Information", "PASS", 45, results_list, "Done", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
            url = get_urls(device_Model, load_configFile("url_path"))
            report_step(f"Url for device {url}", "INFO", 46, results_list, f"Get Url for device  - {url}", None, worker,logger)
            if url != "No url":
                add_text_row(firmware_info_table, f"Url for device  - {url}")
                if check_progress(worker): return serial_number, device_Model, results_list
                firmwareWebVer = get_keysight_software_details(url)
                report_step("Latest firmware for device", "INFO", 48, results_list, f"Latest firmware for device - {firmwareWebVer['revision']}", None, worker, logger)
                add_text_row(firmware_info_table, f"Latest firmware for device - {firmwareWebVer['revision']}")
                if check_progress(worker): return serial_number, device_Model, results_list
                latest = get_latest_version_for_os(requested_os, url)
                add_text_row(firmware_info_table, f"Device OS - {requested_os}")
                report_step("Latest firmware for device OS", "INFO", 50, results_list, f"Latest firmware for device OS - {latest}", None, worker, logger)
                add_text_row(firmware_info_table, f"Latest firmware for device OS - {latest}")
                if check_progress(worker): return serial_number, device_Model, results_list
                print(f"The latest version for {requested_os} is: {latest}")
                if run_firmware_update:
                    upgrade_path = get_upgrade_versions_for_os(firmwareUnitVer, requested_os, url)
                    report_step("The Steps to Upgrade firmware", "INFO", 51, results_list, f"Upgrade Path - {upgrade_path}",
                                None, worker, logger)
                    add_text_row(firmware_info_table, f"Upgrade Path - {upgrade_path}")
                    if check_progress(worker): return serial_number, device_Model, results_list
                    for version in upgrade_path:
                        result = download_keysight_version(version, url, get_n90_family(device_Model), download, download_path, download_defult)
                        download_results.append(result)
                        time.sleep(10)
                    was_download = all(item["Success"] for item in download_results)
                    link = [item["Path"] for item in download_results if item["Success"]]
                    if was_download:
                        report_step("link for Download the latest firmware OS", "INFO", 52, results_list, f"Download the latest firmware OS - {link}", None, worker, logger)
                        add_text_row(firmware_info_table, f"link for Download the latest firmware for OS - {link}")
                    else:
                        report_step("Latest firmware OS", "INFO", 52, results_list, f"latest firmware OS - {link}", None, worker, logger)
                        add_text_row(firmware_info_table, f"Latest firmware for OS - {link}")
                    if check_progress(worker): return serial_number, device_Model, results_list

                    if (firmwareWebVer.get('revision') != firmwareUnitVer) and (
                            requested_os.lower() in firmwareWebVer.get('os').lower()):
                        print(f"Your operation system is {requested_os}")
                        print(f"The Unit firmware is {firmwareUnitVer} and New firmware is {firmwareWebVer.get('revision')}")
                        print("*" * 90)
                        print("!" * 30 + "   Need to Update Firmware   " + "!" * 30)
                        print("*" * 90)
                        report_step("Need to Update Firmware", "INFO", 55, results_list, f"Need to Update Firmware!! - Device {firmwareUnitVer}", None, worker, logger)
                        add_text_row(firmware_info_table, f"Need to Update Firmware!! - {firmwareUnitVer}")

                    elif (requested_os.lower() not in firmwareWebVer.get('os').lower()) and (latest != firmwareUnitVer):
                        print(f"Your operation system is {requested_os}")
                        print(f"The Unit firmware is {firmwareUnitVer} and New firmware is {latest} for {requested_os}")
                        print("*" * 90)
                        print("!" * 30 + "   Need to Update Firmware   " + "!" * 30)
                        print("*" * 90)
                        report_step("Need to Update Firmware", "INFO", 55, results_list, f"Need to Update Firmware!! - {firmwareUnitVer}", None, worker, logger)
                        add_text_row(firmware_info_table, f"Need to Update Firmware!! - {firmwareUnitVer}")
                    else:
                        print("*" * 90)
                        print("-" * 30 + "  No Need to Update Firmware  " + "-" * 30)
                        print("*" * 90)
                        report_step("No Need to Update Firmware", "INFO", 55, results_list, f"No Need to Update Firmware - {firmwareUnitVer}.", None, worker, logger)
                        add_text_row(firmware_info_table, f"No Need to Update Firmware - {firmwareUnitVer}.")
                    if check_progress(worker): return serial_number, device_Model, results_list

                    if download:
                        for index, version in enumerate(upgrade_path):
                            print(f"The firmware {version} file is in: {link[index]}\\{device_Model}")
                            firmware_file = find_file_by_name(download_path, get_n90_family(device_Model), was_download, latest)
                            report_step("Download Firmware " + firmware_file, "PASS", 70, results_list, "Download Firmware " + firmware_file, None, worker, logger)
                            add_text_row(firmware_info_table, "Download Firmware " + firmware_file)
                            if check_progress(worker): return serial_number, device_Model, results_list
                            print(f"The file in {download_path}\\{get_n90_family(device_Model)} is: {firmware_file}")
                            copy_file = windows_control.copy_file_to_remote(target_ip, admin_user, admin_password, download_path, firmware_file, get_n90_family(device_Model), exe_destination_file)
                            if copy_file:
                                report_step("Copy the download Firmware " + firmware_file + " to the device", "PASS", 75, results_list, "Copy the download Firmware " + firmware_file + " to the device", None, worker, logger)
                                add_text_row(firmware_info_table, "Copy the download Firmware " + firmware_file + " to the device")
                            else:
                                report_step("Firmware " + firmware_file + " is already in the device", "PASS", 75, results_list,"Firmware " + firmware_file + " is already in the device", None, worker, logger)
                                add_text_row(firmware_info_table, "Firmware " + firmware_file + " is already in the device")
                            if check_progress(worker): return serial_number, device_Model, results_list
                            print(f"The firmware {latest} file is in the device: {exe_destination_file}")
                    else:
                        print(f"The firmware {firmwareUnitVer} file is in: {link}")
                else:
                    if (firmwareWebVer.get('revision') != firmwareUnitVer) and (
                            requested_os.lower() in firmwareWebVer.get('os').lower()):
                        report_step("User cancel firmware update Need to Update Firmware manually", "INFO", 55,
                                    results_list,
                                    f"Need to Update Firmware manually!! - Device {firmwareUnitVer}", None, worker,
                                    logger)
                        add_text_row(firmware_info_table, f"Need to Update Firmware manually!! - {firmwareUnitVer}")

                    elif (requested_os.lower() not in firmwareWebVer.get('os').lower()) and (latest != firmwareUnitVer):
                        report_step("User cancel firmware update Need to Update Firmware manually", "INFO", 55,
                                    results_list,
                                    f"Need to Update Firmware manually!! - {firmwareUnitVer}", None, worker, logger)
                        add_text_row(firmware_info_table, f"Need to Update Firmware manually!! - {firmwareUnitVer}")
                    else:
                        report_step("User cancel firmware update No Need to Update Firmware", "INFO", 55, results_list,
                                    f"No Need to Update Firmware - {firmwareUnitVer}.", None, worker, logger)
                        add_text_row(firmware_info_table, f"No Need to Update Firmware - {firmwareUnitVer}.")
                    if check_progress(worker): return serial_number, device_Model, results_list

            else:
                report_step("No Url for this device can't check firmware", "FAIL", 75, results_list,"No Url for this device can't check firmware", None, worker, logger)
            results_list.append(firmware_info_table)
            if run_win_update:
                windows_control.minimize_window()
                windows_control.disable_windows_update_notifications(worker, logger)
                windows_control.stop_agilent_update_popup(worker, logger)
                info, update_result = windows_control.main_update_process(results_list, worker, logger)
                results_list.extend(update_result)
                report_step("Windows Update Complete", "PASS", 100, results_list, "Windows Update Complete", None, worker, logger)
                if check_progress(worker): return serial_number, device_Model, results_list
            else:
                report_step("User Cancel Windows Update", "INFO", 100, results_list, "Windows Update Cancel", None,worker, logger)
                if check_progress(worker): return serial_number, device_Model, results_list
        else:
            report_step("Test Completed", "FAIL", 100, results_list, "Test Completed", None, worker, logger)
            if check_progress(worker): return serial_number, device_Model, results_list
        return serial_number, device_Model, results_list

    except Exception as e:
        print(f"Error: {e}")
        return serial_number, device_Model, results_list


def is_n90xxb(model):
    return bool(re.fullmatch(r"N90\d\dB", model))

def get_n90_family(model):

    model = model.upper().strip()
    if re.match(r"^N90\d{2}B$", model):
        return "N90xxB"
    return None

def xsa_response(target_ip, worker=None, logger=None, timeout=600):

    xsa = N90XXB(target_ip, logger)
    return device_information(xsa, worker=worker, logger=logger, timeout=timeout)


if __name__ == "__main__":

    target_ip = "192.168.1.200"
    user = "Administrator"
    password = "Keysight4u!"
    exe_destination_file = r'C$\Windows\Temp'
    bat_file_name = "InterlligentTester.bat"
    exe_file_name = "nircmd.exe"
    source = load_configFile("bat_mircmd_path")
    download_path = load_configFile("download_path")
    if download_path is None:
        download_path = os.path.join(os.environ['USERPROFILE'], 'Downloads')

    download = True

    device = N90XXB(target_ip)
    windows_control = WINconn(target_ip, user, password)
    windows_control.copy_file_to_remote(target_ip, user, password, source, exe_file_name, exe_destination_file)
    windows_control.setup_local_machine()
    print(windows_control.run_bat_file())
    requested_os = windows_control.get_remote_os(target_ip, user, password)

    if device.connect():
        device_Model = device.get_idn()[1]
        serial_number = device.get_idn()[2]
        firmwareUnitVer = device.get_idn()[3]
        #device.get_idn()
        #device.set_span(1e6)  # 1 MHz
        #print("Span set to 1MHz.")
        #device.device_errors()
        #device.deep_license_scan()
        device.system_full_query()
        #print(device.query(":SYST:CONF?"))
        #print(device.query_name(":SYST:LKEY:COUT?", "N9060ES1E"))
        print("\n")
        print(device.license_full_query(":SYSTem:LKEY:LIST?"))

        device.alignment_Now_All()

        device.capture_other_screen()
        time.sleep(5)
        device.open_system_screen()
        device.disconnect()
        windows_control.capture_all_systems(serial_number)
        time.sleep(2)
        print(windows_control.open_license_manager())
        time.sleep(5)
        windows_control.capture_all_licenses(serial_number)

        url =get_urls(device_Model, load_configFile("url_path"))
        firmwareWebVer = get_keysight_software_details(url)
        #print(f"Latest Web Version: {firmwareWebVer.get('revision')}")
        #print(f"Operation systems: {firmwareWebVer.get('os')}")

        latest = get_latest_version_for_os(requested_os, url)
        print(f"The latest version for {requested_os} is: {latest}")
        link = download_keysight_version(latest, url, download)
        print(f"The firmware {latest} file is in: {link}")

        #all_versions = get_keysight_versions_with_os(url)
        #result = get_latest_for_os(all_versions, requested_os)
        #print(f"Latest Version for {requested_os}: {result['Version']}")
        #print(f"Download Link: {result['Download']}")

        if (firmwareWebVer.get('revision') != firmwareUnitVer) and (requested_os.lower() in firmwareWebVer.get('os').lower()):
            print(f"Your operation system is {requested_os}")
            print(f"The Unit firmware is {firmwareUnitVer} and New firmware is {firmwareWebVer.get('revision')}")
            if not download:
                print(f"The firmware {firmwareUnitVer} file is in: {link}")
            else:
                print(f"The firmware {latest} file is in: {download_path}")
            print("*" * 90)
            print("!" * 30 + "   Need to Update Firmware   " + "!" * 30)
            print("*" * 90)
        elif (requested_os.lower() not in firmwareWebVer.get('os').lower()) and (latest != firmwareUnitVer):
            print(f"Your operation system is {requested_os}")
            print(f"The Unit firmware is {firmwareUnitVer} and New firmware is {latest} for {requested_os}")
            if not download:
                print(f"The firmware {firmwareUnitVer} file is in: {link}")
            else:
                print(f"The firmware {latest} file is in: {download_path}")
            print("*" * 90)
            print("!" * 30 + "   Need to Update Firmware   " + "!" * 30)
            print("*" * 90)
        else:
            print("*" * 90)
            print("-" * 30 + "  No Need to Update Firmware  " + "-" * 30)
            print("*" * 90)

        if download:
            firmware_file = get_latest_file(download_path)
            print(f"The latest file in {download_path} is: {firmware_file}")
            windows_control.copy_file_to_remote(target_ip, user, password, download_path, firmware_file, exe_destination_file)

        windows_control.minimize_window()
        windows_control.main_update_process()

    os._exit(0)
