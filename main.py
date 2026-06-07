from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QVBoxLayout, \
    QHBoxLayout, QProgressBar, QMessageBox, QTextEdit, QDialog, QGraphicsDropShadowEffect, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from TestingEquipment.SignalAnaLyzer.N90xxB import *
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from typing import Any
from pathlib import Path
import time
import logging
import threading
import os
import sys

class FirmwareQuestionDialog(QDialog):

    def __init__(self, message):
        super().__init__()

        self.remaining_seconds = 300

        self.setWindowTitle("Firmware Installation")
        self.setMinimumSize(520, 260)

        layout = QVBoxLayout(self)

        self.message_label = QLabel(message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))

        self.timer_label = QLabel("05:00")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("""
            QLabel {
                color: red;
                background-color: #fff0f0;
                border: 2px solid red;
                border-radius: 12px;
                padding: 15px;
            }
        """)

        buttons_layout = QHBoxLayout()

        yes_btn = QPushButton("YES")
        no_btn = QPushButton("NO")

        yes_btn.clicked.connect(self.accept)
        no_btn.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(yes_btn)
        buttons_layout.addWidget(no_btn)
        buttons_layout.addStretch()

        layout.addWidget(self.message_label)
        layout.addWidget(self.timer_label)
        layout.addLayout(buttons_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)

    def update_timer(self):

        self.remaining_seconds -= 1

        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60

        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

        if self.remaining_seconds <= 0:
            self.timer.stop()
            self.reject()


class LiveReportDialog(QDialog):

    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(650, 350)
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([
            "Step",
            "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.table)
        layout.addWidget(self.progress)

    def add_step(self, name, status):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setWordWrap(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setItem( row,0,QTableWidgetItem(name))
        self.table.setItem(row,1, QTableWidgetItem(status))
        self.table.resizeRowsToContents()
        self.table.scrollToBottom()

    def set_progress(self, value):
        self.progress.setValue(value)


class ReportDialog(QDialog):

    def __init__(self, title, content):

        super().__init__()
        self.setWindowTitle(title)
        self.setMinimumSize(500, 350)
        layout = QVBoxLayout(self)
        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setPlainText(content)

        self.text_area.setStyleSheet("""
            QTextEdit {background-color: #f8f9fa; border: 1px solid #cccccc; font-family: Consolas; font-size: 12px;
            }
        """)

        layout.addWidget(self.text_area)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

class TestWorker(QThread):

    row_started = pyqtSignal(int)
    progress_update = pyqtSignal(int, int)
    row_finished = pyqtSignal(int, str, str)
    table_update = pyqtSignal(int, str, str, str)
    row_interrupted = pyqtSignal(int)
    firmware_dialog_request = pyqtSignal(str, object)
    all_finished = pyqtSignal()

    def __init__(self):

        super().__init__()

        self.tasks = []
        self.current_row_index = -1
        self.is_killed = False
        self.test_failed = False

    def add_task(self, task):

        for existing_task in self.tasks:
            if existing_task["index"] == task["index"]:
                return False
        self.tasks.append(task)
        return True

    def run(self):

        while not self.is_killed:
            if not self.tasks:
                self.msleep(200)
                continue
            task = self.tasks.pop(0)

            row_index = task["index"]
            self.current_row_index = row_index
            ip = task["ip"]
            unit = task["unit"]
            serialNumber = "Unknown_SN"
            deviceModel = unit
            self.row_started.emit(row_index)
            recipients = load_email_recipients(Path(load_configFile("email_path"), "Email.csv"), "start")
            send_test_started_email(recipients, unit, row_index + 1, ip)
            self.test_failed = False
            device_logger, log_file = create_test_logger(row_index)
            device_logger.info(f"Test started | Slot={row_index + 1} | IP={ip}")
            try:
                if unit == "N90xxB":
                    serialNumber, deviceModel, result = N90XXB_System_Test(ip, worker=self, logger=device_logger)

                    if self.test_failed:
                        final_status = "FAILED"
                    else:
                        final_status = "PASSED"
                else:
                    raise Exception(f"Unsupported unit type: {unit}")
                self.progress_update.emit(row_index, 100)
                recipients = load_email_recipients(Path(load_configFile("email_path"), "Email.csv"), notify_type="end")
                guide = load_configFile("pdf_reports_path")
                os.makedirs(f"{guide}\\{serialNumber}", exist_ok=True)
                if serialNumber != "":
                    pdf_file = f"{guide}\\{serialNumber}\\{serialNumber}.pdf"
                else:
                    pdf_file = f"{guide}\\None\\None.pdf"
                device_logger.info(f"Serial Number detected: {serialNumber}")
                device_logger.info(f"Unit: {unit}")
                device_logger.info(f"Test finished | Result={final_status}")
                send_test_ended_email(recipients, serialNumber, unit, row_index + 1, ip, final_status, pdf_file)

                self.create_pdf_report(filename=pdf_file, slot=row_index + 1, ip=ip, unit=deviceModel, serial_number= serialNumber, final_status=final_status, results=result)
                self.row_finished.emit(row_index, final_status, pdf_file)


            except Exception as e:
                error_results = [{ "name": "Unhandled Exception", "status": "FAIL", "value": str(e), "time": time.strftime("%H:%M:%S"), "image_path": None}]
                guide = load_configFile("pdf_reports_path")
                os.makedirs(f"{guide}\\{serialNumber}", exist_ok=True)
                pdf_file = f"{guide}\\{serialNumber}\\{serialNumber}.pdf"
                logging.exception(f"Unhandled exception in Slot {row_index + 1} - {e}")

                self.create_pdf_report(filename=pdf_file, slot=row_index + 1, ip=ip, unit=deviceModel, serial_number= serialNumber, final_status="FAILED", results=error_results)
                self.row_finished.emit(row_index, "FAILED", pdf_file)
        self.all_finished.emit()

    def stop(self):
        self.is_killed = True

    def format_results(self, results):

        lines = []

        lines.append("+----+-----------------------------+--------+----------------------+----------+")
        lines.append("| #  | Step                        | Status | Value                | Time     |")
        lines.append("+----+-----------------------------+--------+----------------------+----------+")

        for i, item in enumerate(results, start=1):

            name = item.get("name", "")
            status = item.get("status", "")
            value = item.get("value", "")
            t = item.get("time", "")

            lines.append(
                f"| {i:<2} | {name:<27} | {status:<6} | {value:<20} | {t:<8} |"
            )

            image = item.get("image", "")

            if image:
                lines.append(
                    f"|    | Image: {image:<61} |"
                )

        lines.append("+----+-----------------------------+--------+----------------------+----------+")

        return "\n".join(lines)


    def create_pdf_report(self, filename, slot, ip, unit, serial_number, final_status, results, left_icon="Icon/icon.png", right_icon="Icon/TLV-mmW_logo.png"):

        left_icon = resource_path(left_icon)
        right_icon = resource_path(right_icon)
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        story = []

        logo_table = Table([[Image(left_icon, width=2.0 * inch, height=0.45 * inch), Image(right_icon, width=0.9 * inch, height=0.9 * inch)]],colWidths=[5.8 * inch, 1.0 * inch])
        logo_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (0, 0), "LEFT"),
            ("ALIGN", (1, 0), (1, 0), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        story.append(logo_table)
        story.append(Spacer(1, 16))
        title_style = styles["Title"]
        title_style.fontSize = 24
        title_style.leading = 28
        story.append(Paragraph("<para align='center'><b>TEST REPORT</b></para>",title_style))
        story.append(Spacer(1, 24))

        summary_data = [
            ["Slot", slot],
            ["IP Address", ip],
            ["Unit", unit],
            ["Serial Number", serial_number],
            ["Final Status", final_status],
            ["Finished Time", time.strftime("%H:%M:%S")]
        ]

        summary_table = Table(summary_data,colWidths=[1.7 * inch, 4.8 * inch])
        status_color = colors.green if final_status == "PASSED" else colors.red
        summary_table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (1, 4), (1, 4), status_color),
            ("FONTNAME", (1, 4), (1, 4), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 7),
        ]))

        story.append(summary_table)
        story.append(Spacer(1, 20))

        test_steps = [
            item for item in results
            if isinstance(item, dict)
               and item.get("type", "step") == "step"
        ]

        if test_steps:
            story.append(Paragraph("<b>Test Steps</b>", styles["Heading2"]))
            story.append(Spacer(1, 8))
            cell_style = ParagraphStyle(name="CellStyle",fontSize=8,leading=10)
            table_data: list[list[Any]] = [["#", "Step", "Status", "Value", "Time"]]

            for i, step in enumerate(test_steps, start=1):
                status = str(step.get("status", "")).upper()
                if "PASS" in status:
                    status_text = f"<font color='green'><b>{status}</b></font>"
                elif "FAIL" in status:
                    status_text = f"<font color='red'><b>{status}</b></font>"
                elif "RUNNING" in status:
                    status_text = f"<font color='blue'><b>{status}</b></font>"
                else:
                    status_text = status
                table_data.append([str(i), Paragraph(str(step.get("name", "")), cell_style), Paragraph(status_text, cell_style), Paragraph(str(step.get("value", "")), cell_style), Paragraph(str(step.get("time", "")), cell_style)])
            results_table = Table(table_data,colWidths=[ 0.35 * inch, 2.1 * inch, 0.75 * inch, 2.3 * inch, 0.75 * inch], repeatRows=1)
            results_style = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d9eaf7")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (2, -1), "CENTER"),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEADING", (0, 0), (-1, -1), 10),
            ]

            for row_index, step in enumerate(test_steps, start=1):
                status = step.get("status", "").upper()
                if "PASS" in status:
                    results_style.append(("TEXTCOLOR", (2, row_index), (2, row_index), colors.green))
                    results_style.append(("FONTNAME", (2, row_index), (2, row_index), "Helvetica-Bold"))
                elif "FAIL" in status:
                    results_style.append(("TEXTCOLOR", (2, row_index), (2, row_index), colors.red))
                    results_style.append(("FONTNAME", (2, row_index), (2, row_index), "Helvetica-Bold"))
                elif "INFO" in status:
                    results_style.append(("TEXTCOLOR", (2, row_index), (2, row_index), colors.blue))
                    results_style.append(("FONTNAME", (2, row_index), (2, row_index), "Helvetica-Bold"))

            results_table.setStyle(TableStyle(results_style))
            story.append(results_table)
            story.append(Spacer(1, 20))

        for item in results:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "data_table":

                title = item.get("title", "Data Table")
                headers = item.get("headers", [])
                rows = item.get("rows", [])

                if not headers or not rows:
                    continue

                story.append(Spacer(1, 12))
                story.append(Paragraph(f"<b>{title}</b>", styles["Heading2"]))
                story.append(Spacer(1, 8))
                if title == "Keysight License Manager":
                    data_cell_style = ParagraphStyle(name="DataCellStyle", fontSize=7, leading=8, wordWrap="CJK")
                else:
                    data_cell_style = ParagraphStyle(name="DataCellStyle", fontSize=8, leading=9, wordWrap="CJK")
                table_data: list[list[Any]] = [[Paragraph(str(h), data_cell_style) for h in headers]]

                for row in rows:
                    table_data.append([Paragraph(str(cell), data_cell_style)for cell in row])

                page_width = A4[0] - doc.leftMargin - doc.rightMargin
                num_cols = len(headers)
                if title == "Keysight License Manager":
                    col_widths = [
                        0.8 * inch,
                        2.3 * inch,
                        0.7 * inch,
                        1.4 * inch,
                        0.6 * inch,
                        0.5 * inch,
                        0.6 * inch,
                        0.7 * inch,
                    ]

                else:
                    col_widths = [page_width / num_cols] * num_cols
                data_table = Table(table_data, colWidths=col_widths, repeatRows=1, splitByRow=True)

                data_table_style = [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("PADDING", (0, 0), (-1, -1), 4),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("LEADING", (0, 0), (-1, -1), 8),
                ]

                for row_idx, row in enumerate(rows, start=1):
                    for col_idx, cell in enumerate(row):
                        text = str(cell).upper()
                        if "PASS" in text:
                            data_table_style.append(("TEXTCOLOR", (col_idx, row_idx), (col_idx, row_idx), colors.green))
                            data_table_style.append(("FONTNAME", (col_idx, row_idx), (col_idx, row_idx), "Helvetica-Bold"))
                        elif "FAIL" in text:
                            data_table_style.append(("TEXTCOLOR", (col_idx, row_idx), (col_idx, row_idx), colors.red))
                            data_table_style.append(("FONTNAME", (col_idx, row_idx), (col_idx, row_idx), "Helvetica-Bold"))

                data_table.setStyle(TableStyle(data_table_style))

                story.append(data_table)
                story.append(Spacer(1, 20))

            if item.get("type") == "text_table":

                title = item.get("title", "Information")
                rows = item.get("rows", [])
                if not rows: continue

                story.append(Spacer(1, 12))
                story.append(Paragraph(f"<b>{title}</b>", styles["Heading2"]))
                story.append(Spacer(1, 8))
                table_data = []
                text_cell_style = ParagraphStyle(name="TextCellStyle", fontName="Courier", fontSize=8, leading=9, wordWrap='CJK')

                for row in rows:
                    table_data.append([Paragraph( str(row), text_cell_style)])

                text_table = Table(table_data, colWidths=[6.0 * inch])

                text_table.setStyle(TableStyle([
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                    ("PADDING", (0, 0), (-1, -1), 6),
                    ("FONTNAME", (0, 0), (-1, -1), "Courier"),
                ]))

                story.append(text_table)
                story.append(Spacer(1, 20))


        image_counter = 1

        for step in results:
            if not isinstance(step, dict):
                continue
            image_path = step.get("image_path")
            if image_path:
                story.append(Paragraph(f"<b>Image {image_counter}: {step.get('name', '')}</b>", styles["Heading3"]))
                story.append(Spacer(1, 6))
                story.append(Image(image_path,  width=6.3 * inch, height=3.6 * inch))
                story.append(Spacer(1, 16))
                image_counter += 1
        doc.build(story)

    def ask_firmware_install(self, message):

        request = {
            "answer": False,
            "event": threading.Event()
        }
        self.firmware_dialog_request.emit(message, request)

        request["event"].wait()
        return request["answer"]

class MainWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("Intelligent Tester")
        self.setWindowIcon(QIcon("Icon/icon.png"))
        self.setMinimumSize(1000, 600)
        self.rows = []
        self.user_stopped = False
        self.is_closing = False
        self.live_reports = {}

        self.init_ui()

        self.worker = TestWorker()

        self.worker.row_started.connect(self.lock_row)
        self.worker.progress_update.connect(self.update_row_progress)
        self.worker.row_finished.connect(self.store_report)
        self.worker.row_interrupted.connect(self.unlock_row)
        self.worker.all_finished.connect(self.finalize)
        self.worker.table_update.connect(self.update_live_report)
        self.worker.progress_update.connect(self.update_live_progress)

        self.worker.start()

    def init_ui(self):

        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(
            30,
            20,
            30,
            30
        )

        self.main_layout.setSpacing(15)
        header_layout = QHBoxLayout()
        self.main_label = QLabel()
        left_pix = QPixmap(resource_path("Icon/icon.png"))
        if not left_pix.isNull():
            self.main_label.setPixmap(
                left_pix.scaled(350, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            )

        self.company_label = QLabel()
        right_pix = QPixmap(resource_path("Icon/TLV-mmW_logo.png"))

        if not right_pix.isNull():
            self.company_label.setPixmap(
                right_pix.scaled( 100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            )

        header_layout.addWidget(self.main_label)
        header_layout.addStretch()
        header_layout.addWidget(self.company_label)

        self.main_layout.addLayout(header_layout)
        self.main_layout.addSpacing(30)

        for i in range(5):
            row_layout = QHBoxLayout()
            row_layout.addStretch()

            cb = QCheckBox()
            cb.setFixedWidth(30)
            green_icon = resource_path("Icon/green_ok.png").replace("\\", "/")
            cb.setStyleSheet(f"""
                QCheckBox::indicator {{width: 22px; height: 22px; border: 2px solid gray; border-radius: 5px; }}
                QCheckBox::indicator:checked {{image: url({green_icon});background-color: white; }}
            """)

            ip_input = QLineEdit()
            ip_input.setPlaceholderText( f"10.1.44.{200 + i}" )
            ip_input.setFixedWidth(180)
            ip_input.setEnabled(False)
            ip_input.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            ip_input.setFont(
                QFont("Arial", 13, QFont.Weight.Bold)
            )

            ip_input.setStyleSheet("""
                QLineEdit {border: 2px solid #cccccc;border-radius: 8px; padding: 5px; background-color: #f9f9f9; }
            """)

            combo = QComboBox()
            combo.addItems(["N90xxB"])
            combo.setFixedWidth(140)
            combo.setFont(QFont("Arial", 11, QFont.Weight.Bold))

            status_label = QLabel("PENDING")
            status_label.setFixedWidth(100)
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            status_label.setStyleSheet("""
                QLabel {background-color: orange; color: white; padding: 5px; border-radius: 8px; font-weight: bold; }
            """)

            progress_bar = QProgressBar()
            progress_bar.setFixedWidth(150)
            progress_bar.setValue(0)
            progress_bar.setStyleSheet("""
            QProgressBar {border-radius: 5px; text-align: center; background-color: #eeeeee;}
                QProgressBar::chunk { background-color: #28a745; }
            """)

            report_btn = QPushButton("📄 Report")
            report_btn.setFixedWidth(120)
            report_btn.setVisible(False)
            report_btn.setStyleSheet("""
                QPushButton {
                background-color: #17a2b8; color: white; 
                border-radius: 8px; font-weight: bold; padding: 5px;
                }

                QPushButton:hover {
                    background-color: #138496;
                }
            """)

            cb.stateChanged.connect(lambda state, idx=i: self.handle_checkbox_change(idx, state))
            row_layout.addWidget(cb)
            row_layout.addWidget(QLabel("IP:", font=QFont("Arial", 12, QFont.Weight.Bold)))
            row_layout.addWidget(ip_input)
            row_layout.addSpacing(10)
            row_layout.addWidget(QLabel("UNIT:", font=QFont("Arial", 12, QFont.Weight.Bold)))
            row_layout.addWidget(combo)
            row_layout.addSpacing(15)
            row_layout.addWidget(status_label)
            row_layout.addSpacing(10)
            row_layout.addWidget(progress_bar)
            row_layout.addSpacing(10)
            row_layout.addWidget(report_btn)
            row_layout.addStretch()
            self.main_layout.addLayout(row_layout)
            self.rows.append({
                "checkbox": cb,
                "ip_input": ip_input,
                "combo": combo,
                "status": status_label,
                "progress": progress_bar,
                "report_btn": report_btn,
                "report_text": "",
                "pdf_file": "",
                "is_finished": False,
                "is_queued": False,
                "is_running": False
            })

        self.main_layout.addStretch()
        buttons_layout = QHBoxLayout()
        self.start_btn = QPushButton("▶ START")
        self.start_btn.setFixedSize(220, 50)
        self.start_btn.setFont(
            QFont("Arial", 12, QFont.Weight.Bold))

        self.start_btn.setStyleSheet("""
            QPushButton {background-color: #db9e34; color: white; border-radius: 12px; border: 2px solid #b92929; }
            QPushButton:hover { background-color: #b96529;}
            QPushButton:disabled {background-color: #cccccc; border: 1px solid #999999; }
        """)

        self.stop_btn = QPushButton("■ STOP")
        self.stop_btn.setFixedSize(220, 50)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        self.stop_btn.setStyleSheet("""
            QPushButton {background-color: red; color: white; border-radius: 12px; border: 2px solid #b92929;}
            QPushButton:hover {background-color: #cc0000;}
            QPushButton:disabled {background-color: #ff9999; color: #eeeeee; border: 1px solid #ffcccc;}
        """)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(3, 3)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.start_btn.setGraphicsEffect(shadow)
        self.start_btn.clicked.connect(self.start_tests)
        self.stop_btn.clicked.connect(self.stop_tests)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.start_btn)
        buttons_layout.addWidget(self.stop_btn)
        buttons_layout.addStretch()
        self.main_layout.addLayout(buttons_layout)

    def handle_checkbox_change(self, index, state):

        row = self.rows[index]
        if state == 2:
            row["ip_input"].setEnabled(True)
            if self.is_test_running():
                self.add_single_row_to_queue(index)
        else:
            row["ip_input"].setEnabled(False)
            row["progress"].setValue(0)
            row["report_btn"].setVisible(False)
            row["is_finished"] = False
            row["is_queued"] = False
            row["is_running"] = False
            row["status"].setText("PENDING")
            row["status"].setStyleSheet("""
                QLabel {background-color: orange; color: white; padding: 5px; border-radius: 8px; font-weight: bold;}
            """)
            self.update_buttons_state()

    def add_single_row_to_queue(self, index):

        row = self.rows[index]
        if row["is_finished"]: return False
        if row["is_queued"]: return False
        if row["is_running"]: return False
        if not row["checkbox"].isChecked(): return False
        ip = row["ip_input"].text().strip()
        if not ip:
            ip = row["ip_input"].placeholderText()
        row["progress"].setValue(0)

        task_added = self.worker.add_task({"index": index, "ip": ip, "unit": row["combo"].currentText()})

        if task_added:
            row["is_queued"] = True
            row["checkbox"].setEnabled(False)
            row["ip_input"].setEnabled(False)
            row["combo"].setEnabled(False)
            row["status"].setText("QUEUED")
            row["status"].setStyleSheet("""
                QLabel {background-color: #ffc107; color: white; padding: 5px; border-radius: 8px; font-weight: bold;}
            """)

            self.user_stopped = False
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            return True
        return False

    def start_tests(self):

        logging.info("START button pressed")
        added_any = False
        for i, row in enumerate(self.rows):
            if (
                    row["checkbox"].isChecked()
                    and not row["is_finished"]
                    and not row["is_queued"]
                    and not row["is_running"]
            ):

                if not row["checkbox"].isEnabled():
                    continue

                task_added = self.add_single_row_to_queue(i)

                if task_added:
                    added_any = True

        if not added_any:
            QMessageBox.information(
                self,
                "Info",
                "No new tests selected."
            )

            return

        self.user_stopped = False
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def update_row_progress(self, index, value):

        self.rows[index]["progress"].setValue(value)

    def lock_row(self, index):

        row = self.rows[index]
        row["is_queued"] = False
        row["is_running"] = True
        row["checkbox"].setEnabled(False)
        row["ip_input"].setEnabled(False)
        row["combo"].setEnabled(False)
        row["status"].setText("RUNNING")
        row["status"].setStyleSheet("""
            QLabel {background-color: #007bff; color: white; padding: 5px; border-radius: 8px; font-weight: bold; }
        """)

        self.update_buttons_state()
        self.open_live_report(index)

    def unlock_row(self, index):

        row = self.rows[index]
        row["is_queued"] = False
        row["is_running"] = False
        row["checkbox"].setEnabled(True)
        row["ip_input"].setEnabled(True)
        row["combo"].setEnabled(True)
        if row["is_finished"]:
            return
        row["status"].setText("STOPPED")
        row["status"].setStyleSheet("""
            QLabel {background-color: red; color: white; padding: 5px; border-radius: 8px; font-weight: bold;}
        """)

        self.update_buttons_state()

    def store_report(self, index, final_status, pdf_file):

        row = self.rows[index]
        row["is_finished"] = True
        row["is_queued"] = False
        row["is_running"] = False
        row["report_btn"].setVisible(True)
        row["progress"].setValue(100)
        if final_status == "FAILED":
            row["status"].setText("FAILED")
            row["status"].setStyleSheet("""QLabel {background-color: red; color: white; padding: 5px; border-radius: 8px; font-weight: bold;} """)
        else:
            row["status"].setText("PASSED")
            row["status"].setStyleSheet("""QLabel {background-color: green; color: white; padding: 5px; border-radius: 8px; font-weight: bold;}""")
        row["checkbox"].setEnabled(True)
        row["ip_input"].setEnabled(True)
        row["combo"].setEnabled(True)
        row["pdf_file"] = pdf_file
        try:
            row["report_btn"].clicked.disconnect()
        except:
            pass

        row["report_btn"].clicked.connect(lambda _, idx=index: self.open_pdf_report(idx))

        self.update_buttons_state()
        if not self.is_test_running() and not self.is_closing: QTimer.singleShot(3000, self.show_finished_message)

    def open_pdf_report(self, index):

        pdf_file = self.rows[index]["pdf_file"]

        if not pdf_file or not os.path.exists(pdf_file):
            QMessageBox.warning(self,"Report Missing","PDF report file was not found.")
            return

        os.startfile(pdf_file)

    def is_test_running(self):

        for row in self.rows:
            if row["is_queued"] or row["is_running"]:
                return True
        return False

    def update_buttons_state(self):

        has_active_tests = self.is_test_running()
        self.stop_btn.setEnabled(has_active_tests)
        if has_active_tests:
            self.start_btn.setEnabled(False)
        else:
            self.start_btn.setEnabled(True)

    def show_report(self, index):
        dialog = ReportDialog(
            f"Report Slot {index + 1}",
            self.rows[index]["report_text"]
        )
        dialog.exec()

    def stop_tests(self):

        logging.warning("STOP button pressed by user")
        self.user_stopped = True
        self.worker.stop()
        self.worker.wait(3000)
        for row in self.rows:
            row["is_queued"] = False
            row["is_running"] = False
            row["checkbox"].setEnabled(True)
            row["ip_input"].setEnabled(True)
            row["combo"].setEnabled(True)

            if not row["is_finished"]:
                row["status"].setText("PENDING")

                row["status"].setStyleSheet("""
                    QLabel {background-color: orange; color: white; padding: 5px; border-radius: 8px; font-weight: bold;}
                """)

        self.worker = TestWorker()
        self.worker.row_started.connect(self.lock_row)
        self.worker.progress_update.connect(self.update_row_progress)
        self.worker.row_finished.connect(self.store_report)
        self.worker.row_interrupted.connect(self.unlock_row)
        self.worker.all_finished.connect(self.finalize)
        self.worker.table_update.connect(self.update_live_report)
        self.worker.progress_update.connect(self.update_live_progress)
        self.worker.start()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        QMessageBox.warning(self,"Tests Stopped","Tests stopped by user." )

    def finalize(self):
        pass

    def closeEvent(self, event):

        logging.info("Application closing")
        self.is_closing = True
        self.user_stopped = True

        if hasattr(self, "worker"):
            self.worker.stop()
            self.worker.wait(3000)
        event.accept()

    def open_live_report(self, index):

        dialog = LiveReportDialog( f"Live Report - Slot {index + 1}")
        self.live_reports[index] = dialog
        dialog.show()

    def update_live_report(self, index, name, status):
        if index in self.live_reports:
            self.live_reports[index].add_step(name, status)

    def update_live_progress(self, index, value):

        if index in self.live_reports:
            self.live_reports[index].set_progress(value)

    def show_finished_message(self):

        if not self.is_test_running() and not self.is_closing:
            for dialog in self.live_reports.values():
                dialog.close()
            self.live_reports.clear()
            QMessageBox.information(self,"Finished","All tests completed.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())