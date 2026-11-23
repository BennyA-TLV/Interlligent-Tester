pyinstaller --windowed --onedir --name IntelligentTester ^
--add-data "Icon;Icon" ^
--add-data "Files;Files" ^
--add-data "Communication;Communication" ^
--add-data "TestingEquipment;TestingEquipment" ^
--hidden-import Communication.AnalyzerConnection ^
--hidden-import Communication.Connection ^
--hidden-import Communication.WINconnection ^
--hidden-import Communication.WEBconnection ^
--hidden-import TestingEquipment.SignalAnaLyzer.SignalAnaLyzer ^
--hidden-import TestingEquipment.SignalAnaLyzer.N90xxB ^
--hidden-import TestingEquipment.SignalAnaLyzer.Spectrum ^
--hidden-import TestingEquipment.SignalAnaLyzer.Firmware ^
--hidden-import pyvisa_py ^
main.py