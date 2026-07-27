import pyvisa
from Communication.Connection import *

#Created by Benny Aberman - 054-3220104
#Analyzer devices class
    # The init function
    # The Connect function
    # The query + name function
    # The license full query function
    # The system full query function
    # The get option descriptions function
    # The disconnect function

class NetworkAnalyzerConn:

    # The init function that contains all the parameters of the class.
    # Option_descriptions.csv file that in files folder contain all the descriptions for the data we collect
    # From the device
    def __init__(self, ip_address, logger=None, timeout=30000):

        self.rm = pyvisa.ResourceManager('@py')
        self.address = f"TCPIP0::{ip_address}::5025::SOCKET"
        self.logger = logger
        self.timeout = timeout
        self.instr = None
        self.option_descriptions = get_license_descriptions(load_configFile("license_path"))

    # The Connect function
    def connect(self):
        try:
            self.instr = self.rm.open_resource(self.address)
            self.instr.timeout = self.timeout
            self.instr.read_termination = '\n'
            self.instr.write_termination = '\n'
            if hasattr(self, "logger") and self.logger: self.logger.info(f"Connected to {self.address}")
            return True
        except Exception as e:
            if hasattr(self, "logger") and self.logger: self.logger.exception(f"Connection error to {self.address}")
            return False

    # The write function - commands that not return any data
    def write(self, cmd):
        if self.instr:
            self.instr.write(cmd)

    # The query function - commands that return data
    def query(self, cmd):
        try:
            return self.instr.query(cmd) if self.instr else None
        except Exception as e:
            print(f"Error: {e}")

    # The query + name function  - commands that need adding same data to return specific data
    def query_name(self, cmd, name):
        try:
            safe_name = str(name).replace('"', '\\"')
            return self.query(f'{cmd} "{safe_name}"')
        except Exception as e:
            print(f"Error: {e}")

    # The license full query function - return all the data form the license manger
    def get_installed_options(self):
        """
        מחפש ב-Windows Registry רכיבי E5061/ENA ואופציות מותקנות.

        Returns:
            tuple:
                output_text: טקסט לתצוגה
                options: רשימה של מילונים
        """

        if not self.session:
            if not self.connect():
                return "", []

        ps = r"""
        $uninstallPaths = @(
            "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
            "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
        )

        $apps = Get-ItemProperty $uninstallPaths -ErrorAction SilentlyContinue |
            Where-Object {
                $_.DisplayName -and (
                    $_.DisplayName -match "E5061" -or
                    $_.DisplayName -match "ENA" -or
                    $_.DisplayName -match "Network Analyzer" -or
                    $_.Publisher -match "Keysight" -or
                    $_.Publisher -match "Agilent"
                )
            } |
            Select-Object DisplayName, DisplayVersion, Publisher, InstallLocation |
            Sort-Object DisplayName -Unique

        foreach ($app in $apps) {
            $name = [string]$app.DisplayName
            $version = [string]$app.DisplayVersion
            $publisher = [string]$app.Publisher
            $location = [string]$app.InstallLocation

            Write-Output "$name|$version|$publisher|$location"
        }
        """

        try:
            result = self.session.run_ps(ps)

            stdout = result.std_out.decode(
                "utf-8",
                errors="ignore"
            ).strip()

            stderr = result.std_err.decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if stderr:
                print(f"Registry query warning: {stderr}")

            if not stdout:
                print("No E50/ENA software information was found.")
                return "", []

            options = []
            output = []

            for line in stdout.splitlines():
                parts = line.split("|", 3)

                while len(parts) < 4:
                    parts.append("")

                name, version, publisher, location = [
                    value.strip() for value in parts
                ]

                item = {
                    "name": name,
                    "version": version or "Unknown",
                    "publisher": publisher or "Unknown",
                    "location": location or "Unknown"
                }

                options.append(item)

                output.append(
                    f"{item['name']} | "
                    f"{item['version']} | "
                    f"{item['publisher']} | "
                    f"{item['location']}"
                )

            return "\n".join(output), options

        except Exception as e:
            print(f"Error reading E50 installed options: {e}")
            return "", []

    def license_full_query(self):
        results_list = []

        try:
            output_text, installed_items = self.get_installed_options()

            table = create_data_table(
                title="Keysight Network Analyzer Installed Software",
                headers=[
                    "Component",
                    "Version",
                    "Publisher",
                    "Install Location"
                ]
            )

            for item in installed_items:
                add_data_row(
                    table,
                    [
                        item["name"],
                        item["version"],
                        item["publisher"],
                        item["location"]
                    ]
                )

            results_list.append(table)

            return output_text, results_list

        except Exception as e:
            print(f"Error: {e}")
            return "", results_list

    # The system full query function - return all the data form the system information
    def system_full_query(self):
        results_list = []

        headers = [
            "Option ID",
            "Name/Description",
            "Option Version"
        ]

        measurements_table = create_data_table( title="System Information", headers=[ f"{headers[0]:^13}", f"{headers[1]:^60}", f"{headers[2]:^18}" ])
        system_info_table = create_text_table("System Information")
        try:
            if not self.instr:
                raise RuntimeError("Instrument is not connected")

            self.read_e50_system_information( system_info_table, measurements_table)

            results_list.append(system_info_table)
            results_list.append(measurements_table)
            return results_list

        except Exception as error:
            print(f"System information error: " f"{type(error).__name__}: {error}")
            if self.logger:
                self.logger.exception("Failed reading system information")
            return results_list

    def read_e50_system_information(self, system_info_table, measurements_table):
        print("\n")
        print("*" * 20 + " System Information " + "*" * 20)

        idn = self.instr.query("*IDN?").strip()
        idn_parts = [part.strip() for part in idn.split(",")]

        manufacturer = (idn_parts[0] if len(idn_parts) > 0 else "Unknown")
        model = (idn_parts[1] if len(idn_parts) > 1 else "Unknown")
        serial_number = (idn_parts[2] if len(idn_parts) > 2 else "Unknown")
        firmware = (idn_parts[3] if len(idn_parts) > 3 else "Unknown")
        system_lines = [
            f"Manufacturer: {manufacturer}",
            f"Model: {model}",
            f"Serial Number: {serial_number}",
            f"Firmware: {firmware}",
            f"VISA Address: {self.address}"
        ]

        for line in system_lines:
            print(line)
            add_text_row(system_info_table, line)

        options_response = self.instr.query("*OPT?")

        if not options_response:
            add_text_row(system_info_table,"Options: No response")
            return

        options_response = options_response.strip()
        print(f"Options raw response: {options_response}")

        option_items = self.split_e50_options(options_response)

        if not option_items:
            add_text_row( system_info_table,f"Options: {options_response}")
            return

        self.print_option_header()

        for option_id, version in option_items:
            description = find_option_descriptions(self.option_descriptions, option_id)
            print(f"{option_id:<13} | " f"{description:<60} | " f"{version:<18}")

            add_data_row(measurements_table,[f"{option_id:<13}", f"{description:<60}", f"{version:<18}"])

        self.read_e50_additional_system_fields(system_info_table)

    def split_e50_options(self, response):

        parsed_options = []
        clean_response = (response.replace('"', "").replace(";", ",").strip())
        raw_items = [item.strip() for item in clean_response.split(",") if item.strip()]

        for item in raw_items:
            option_id = item
            version = "- - -"

            if ":" in item:
                option_id, version = item.split(":", 1)

            option_id = option_id.strip()
            version = version.strip()

            if option_id.upper().startswith("E5061B-"):
                option_id = option_id.split("-", 1)[1]

            parsed_options.append((option_id, version))

        return parsed_options

    def print_option_header(self):

        columns = ["Option ID", "Name/Description", "Option Version"]
        print("\n")
        print(f"{columns[0]:^13} | " f"{columns[1]:^60} | " f"{columns[2]:^18}")
        print("_" * 101)

    def read_e50_additional_system_fields(self, system_info_table):

        commands = {
            "System Error": ":SYSTem:ERRor?",
        }

        for title, command in commands.items():
            try:
                response = self.instr.query(command)
                if response is not None:
                    line = f"{title}: {response.strip()}"
                    print(line)
                    add_text_row(system_info_table, line)

            except Exception as error:
                print(
                    f"Skipping {command}: "
                    f"{type(error).__name__}: {error}"
                )


    # The disconnect function
    def disconnect(self):
        if self.instr is not None:
            try:
                self.instr.close()

                if self.logger:
                    self.logger.info(
                        f"Disconnected from {self.address}"
                    )

            except Exception as error:
                print(
                    f" > Disconnect warning: "
                    f"{type(error).__name__}: {error}"
                )
