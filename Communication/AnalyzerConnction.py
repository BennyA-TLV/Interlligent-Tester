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

class AnalyzerConn:

    # The init function that contains all the parameters of the class.
    # Option_descriptions.csv file that in files folder contain all the descriptions for the data we collect
    # From the device
    def __init__(self, ip_address, logger=None, timeout=30000):
        self.rm = pyvisa.ResourceManager('@py')
        self.address = f"TCPIP0::{ip_address}::INSTR"
        self.logger = logger
        self.timeout = timeout
        self.instr = None
        self.option_descriptions = get_option_descriptions(load_configFile("option_path"))

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
            return self.instr.query(cmd + " " +  f"\"{name}\"") if self.instr else None
        except Exception as e:
            print(f"Error: {e}")

    # The license full query function - return all the data form the license manger
    def license_full_query(self, command):
        results_list = []
        try:
            raw_data = self.instr.query_binary_values(command, datatype='B', header_fmt='ieee')
            full_string = "".join([chr(b) for b in raw_data]).replace('"', '')
            lines = [line.strip() for line in full_string.split('\n') if line.strip()]
            print("*" * 87 + " Keysight License Manager " + "*" * 87+ "\n")
            colns = ["Feature", "Description", "Version", "License number" ,"Expiration", "Type", "Count", "Location"]
            print(f"{colns[0]:^13} | {colns[1]:^80} | {colns[2]:^14} |  {colns[3]:^17} | {colns[4]:^12} | {colns[5]:^12} | {colns[6]:^12} | {colns[7]:^12}")
            print("-" * 200)
            measurements_table = create_data_table(title="Keysight License Manager",headers=[f"{colns[0]:^13}", f"{colns[1]:^80}", f"{colns[2]:^14}", f"{colns[3]:^17}", f"{colns[4]:^12}", f"{colns[5]:^12}", f"{colns[6]:^12}", f"{colns[7]:^12}"])
            output = []
            for line in lines:
                parts = line.split(',')
                if len(parts) >= 3:
                    opt, ver, sig = parts[0], parts[1], parts[2]
                    exp, type, count, location = "None", "Fixed", "Unlimited", "Local"
                    description = find_option_descriptions(self.option_descriptions, opt)
                    moreData = self.query_name(":SYST:LKEY?", opt).split(',')
                    if (len(moreData) > 1):
                        output.append(f"{opt:<13} | {description:<80} |{ver:<15} | {sig[:15]}... | {moreData[1]:<15}")
                        add_data_row(measurements_table,[f"{opt:<13}", f"{description:<80}", f"{ver:<15}", f"{sig[:15]}...", f"{moreData[1]:<15}"])
                    else:
                        output.append(f"{opt:<13} | {description:<80} |{ver:<15} | {sig[:15]}... | {exp:<12} | {type:<12} | {count:<12} | {location:<12}")
                        add_data_row(measurements_table, [f"{opt:<13}", f"{description:<80}", f"{ver:<15}", f"{sig[:15]}...", f"{exp:<12}", f"{type:<12}", f"{count:<12}", f"{location:<12}"])
            results_list.append(measurements_table)
            return "\n".join(output), results_list

        except Exception as e:
            print(f"Error: {e}")
            return "", results_list

    # The system full query function - return all the data form the system information
    def system_full_query(self):
        results_list = []
        one_line = 1
        try:
            raw_bytes = self.instr.query_binary_values(":SYSTem:CONFigure:SYSTem?", datatype='B', header_fmt='ieee')

            full_text = "".join([chr(b) for b in raw_bytes])
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            print("\n")
            print("*" * 20 + " System Information " + "*" * 20 + "\n")
            headers = ["Option ID","Name/Description","Option Version"]
            measurements_table = create_data_table(title="System Information", headers=[f"{headers[0]:^13}",f"{headers[1]:^60}", f"{headers[2]:^18}"])
            system_info_table = create_text_table("System Information")
            for line in lines:
                #if not line.startswith("N90"):
                if not (len(line) >= 2 and line[0].isalpha() and line[1].isdigit()):
                    print(line)
                    add_text_row(system_info_table, line)
                else:
                    parts = [p.strip().replace('"', '') for p in line.split(',')]
                    if len(parts) >= 1:
                        opt_id = parts[0]
                        version = parts[1] if len(parts) > 1 else " - - -"
                        if ":" in opt_id:
                            before, sep, after = opt_id.partition(':')
                            opt_id = before
                            version = after
                        description = find_option_descriptions(self.option_descriptions, opt_id)
                        if(one_line):
                            print("\n")
                            colns = ["Option ID","Name/Description","Option Version"]
                            print(f"{colns[0]:^13} | {colns[1]:^60} | {colns[2]:^18}")
                            print("_" * 101)
                            one_line = 0
                        print(f"{opt_id:<13} | {description:<60} | {version:<18}")
                        add_data_row(measurements_table, [f"{opt_id:<13}", f"{description:<60}", f"{version:<18}"])

            results_list.append(system_info_table)
            results_list.append(measurements_table)
            return results_list
        except Exception as e:
            print(f"Error: {e}")

    # The disconnect function
    def disconnect(self):
        if self.instr:
            self.instr.close()
            print("Disconnected.")


