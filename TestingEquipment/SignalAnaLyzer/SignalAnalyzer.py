from Communication.AnalyzerConnction import AnalyzerConn
from Communication.Connection import *
import time



## ---------------------  Strings ------------------------------##
IVI_RESET = "*RST"
IVI_IDENT = "*IDN?"
## ---------------------  Displays  ----------------------------##
IVI_DISPLAY_GET_TRACE = ":TRAC? TRACE1"
## ---------------------  Settings  ----------------------------##
IVI_SETTING_SET_SPAN = ":SENSE:FREQ:SPAN"

#Created by Benny Aberman - 054-3220104
#Signal Analyzer devices class
    # The get keysight device manufacturer, model, serial number, firmware version function
    # Setting the frequency width (SPAN) function
    # Getting the trace data function
    # Alignment now all function
    # Alignment RF only function

class SignalAnalyzer(AnalyzerConn):

    # The get keysight device manufacturer, model, serial number, firmware version function
    def get_idn(self):
        #print(f"Manufacturer:  {idn[0]}")
        #print(f"Model:         {idn[1]}")
        #print(f"Serial Number: {idn[2]}")
        #print(f"Firmware Ver:  {idn[3]}")
        return self.query(IVI_IDENT).split(',')


    # Setting the frequency width (SPAN) function
    def set_span(self, span_hz):
        self.write(IVI_SETTING_SET_SPAN + f" {span_hz}")
        display_ferq = int(span_hz/1000)
        print(f"Span set to {display_ferq}KHz.")

    # Getting the trace data function
    def get_trace_data(self):
        raw_data = self.query(IVI_DISPLAY_GET_TRACE)
        return [float(val) for val in raw_data.split(',')]

    def device_errors(self):
        try:
            return self.query(":SYST:ERR?")
        except:
            pass

    # Alignment now all function
    def alignment_Now_All(self, results_list, worker, logger):
        print("Starting Alignment Now All... Please wait.")
        report_step("Alignment ALL", "RUNNING", 26, results_list, "Alignment ALL", None, worker, logger)
        cal_status = self.query("CAL?")

        try:
            opc = self.query("*OPC?")
            time.sleep(10)
            if opc.strip() == "1":
                #print(cal_status)
                print("Alignment Now All Completed Successfully!")
                report_step("Alignment ALL", "PASS", 30, results_list, "Alignment ALL", None, worker, logger)
            else:
                print("Alignment Now All with Errors")
                report_step("Alignment ALL", "FAIL", 30, results_list, "Alignment ALL", None, worker, logger)
                err = self.device_errors()
                print(f"\nSystem Status: {err}")
            print("Waiting 10 second to screenshot the Error information ")
            time.sleep(10)
        except Exception as e:
            print(f"Error: {e}")

    # Alignment RF only function
    def alignment_RF(self):
        print("Starting Alignment RF... Please wait.")
        cal_status = self.query(":CALibration:RF?")

        try:
            opc = self.query("*OPC?")
            if opc.strip() == "1":
                print(cal_status)
                print("Alignment RF Completed Successfully!")
            else:
                print("Alignment RF with Errors")
                err = self.device_errors()
                print(f"\nSystem Status: {err}")
        except Exception as e:
            print(f"Error: {e}")

