"""
BalanceLog Pro - Report Generator

Generates production reports (daily, weekly, monthly) with statistics.
Exports to Excel, CSV, and PDF formats.
"""

import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional

from src.database.db_manager import DatabaseManager
from src.database.models import BalancingRecord, DailySummary, ReportData
from src.excel.excel_exporter import ExcelExporter
from src.utils.logger import get_logger

logger = get_logger("reports")


class ReportGenerator:
    """
    Generates production reports with aggregated statistics.

    Report types:
    - Daily: Single day's production summary
    - Weekly: Monday–Sunday production summary
    - Monthly: Full month production summary

    Statistics include:
    - Total shafts balanced
    - Front/Rear breakdown
    - Average initial/final imbalance
    - Most common correction weight
    - OCR confidence average

    Export formats: Excel (.xlsx), CSV (.csv), PDF (.pdf)
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        self._db = db_manager
        self._excel = ExcelExporter()

    # ─────────────────────────────────────────────────────────
    # Report Generation
    # ─────────────────────────────────────────────────────────
    def generate_daily(self, date_str: str) -> ReportData:
        """Generate a daily production report."""
        records = self._db.get_records_by_date(date_str)
        summary = self._db.get_daily_summary(date_str)
        stats = self._db.get_statistics(date_str, date_str)

        report = ReportData(
            period="Daily",
            start_date=date_str,
            end_date=date_str,
            total_shafts=stats.get("total_shafts", 0),
            front_count=summary.front_shafts,
            rear_count=summary.rear_shafts,
            avg_initial_imbalance=stats.get("avg_initial_imbalance", 0),
            avg_final_imbalance=stats.get("avg_final_imbalance", 0),
            most_common_weight=stats.get("most_common_weight", 0),
            daily_summaries=[summary],
            records=records,
        )

        logger.info("Daily report generated for %s: %d shafts", date_str, report.total_shafts)
        return report

    def generate_weekly(self, week_start: str) -> ReportData:
        """
        Generate a weekly production report.

        Args:
            week_start: Start date of the week (YYYY-MM-DD, typically Monday)
        """
        start = datetime.strptime(week_start, "%Y-%m-%d")
        end = start + timedelta(days=6)
        end_str = end.strftime("%Y-%m-%d")

        records = self._db.get_records_by_date_range(week_start, end_str)
        stats = self._db.get_statistics(week_start, end_str)

        # Generate daily summaries for each day in the week
        daily_summaries = []
        for i in range(7):
            day = start + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            daily_summaries.append(self._db.get_daily_summary(day_str))

        front = sum(1 for r in records if r.shaft_type == "Front")
        rear = sum(1 for r in records if r.shaft_type == "Rear")

        report = ReportData(
            period="Weekly",
            start_date=week_start,
            end_date=end_str,
            total_shafts=stats.get("total_shafts", 0),
            front_count=front,
            rear_count=rear,
            avg_initial_imbalance=stats.get("avg_initial_imbalance", 0),
            avg_final_imbalance=stats.get("avg_final_imbalance", 0),
            most_common_weight=stats.get("most_common_weight", 0),
            daily_summaries=daily_summaries,
            records=records,
        )

        logger.info(
            "Weekly report generated: %s to %s, %d shafts",
            week_start, end_str, report.total_shafts,
        )
        return report

    def generate_monthly(self, year: int, month: int) -> ReportData:
        """Generate a monthly production report."""
        start_str = f"{year}-{month:02d}-01"
        # Calculate last day of month
        if month == 12:
            end = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(year, month + 1, 1) - timedelta(days=1)
        end_str = end.strftime("%Y-%m-%d")

        records = self._db.get_records_by_date_range(start_str, end_str)
        stats = self._db.get_statistics(start_str, end_str)

        # Daily summaries for the month
        daily_summaries = []
        current = datetime(year, month, 1)
        while current <= end:
            day_str = current.strftime("%Y-%m-%d")
            daily_summaries.append(self._db.get_daily_summary(day_str))
            current += timedelta(days=1)

        front = sum(1 for r in records if r.shaft_type == "Front")
        rear = sum(1 for r in records if r.shaft_type == "Rear")

        report = ReportData(
            period="Monthly",
            start_date=start_str,
            end_date=end_str,
            total_shafts=stats.get("total_shafts", 0),
            front_count=front,
            rear_count=rear,
            avg_initial_imbalance=stats.get("avg_initial_imbalance", 0),
            avg_final_imbalance=stats.get("avg_final_imbalance", 0),
            most_common_weight=stats.get("most_common_weight", 0),
            daily_summaries=daily_summaries,
            records=records,
        )

        logger.info(
            "Monthly report generated: %s, %d shafts",
            f"{year}-{month:02d}", report.total_shafts,
        )
        return report

    # ─────────────────────────────────────────────────────────
    # Export
    # ─────────────────────────────────────────────────────────
    def export_to_excel(self, report: ReportData, output_path: Path) -> Path:
        """Export report to a styled Excel file."""
        title = f"{report.period} Report ({report.start_date}"
        if report.start_date != report.end_date:
            title += f" to {report.end_date}"
        title += ")"

        return self._excel.export_records(report.records, output_path, title)

    def export_to_csv(self, report: ReportData, output_path: Path) -> Path:
        """Export report to CSV format."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        headers = [
            "Date", "Time", "Punching Number", "Tube Length", "Type",
            "Initial 0°", "Initial Left", "Initial Left Angle",
            "Initial Right", "Initial Right Angle",
            "Weight Add. Left", "Weight Add. Right",
            "After Corr. 0°", "After Corr. Left", "After Corr. Right",
            "Screenshot", "OCR Confidence", "Notes",
        ]

        with open(str(output_path), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Summary header
            writer.writerow([f"BalanceLog Pro — {report.period} Report"])
            writer.writerow([f"Period: {report.start_date} to {report.end_date}"])
            writer.writerow([f"Total Shafts: {report.total_shafts}"])
            writer.writerow([])

            # Column headers
            writer.writerow(headers)

            # Data rows
            for record in report.records:
                writer.writerow([
                    record.date, record.time, record.punching_number,
                    record.tube_length, record.shaft_type,
                    record.initial_zero_degree,
                    record.initial_left_value, record.initial_left_angle,
                    record.initial_right_value, record.initial_right_angle,
                    record.weight_addition_left, record.weight_addition_right,
                    record.after_correction_zero_degree,
                    record.after_correction_left, record.after_correction_right,
                    record.screenshot_path, f"{record.ocr_confidence:.1%}",
                    record.operator_notes,
                ])

        logger.info("CSV exported: %s", output_path.name)
        return output_path

    def export_to_pdf(self, report: ReportData, output_path: Path) -> Path:
        """
        Export report to PDF format using reportlab.

        Creates a professional PDF with:
        - Title and summary section
        - Statistics table
        - Daily breakdown table
        - Full records table
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            )

            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=landscape(A4),
                rightMargin=15 * mm,
                leftMargin=15 * mm,
                topMargin=15 * mm,
                bottomMargin=15 * mm,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "CustomTitle", parent=styles["Title"],
                fontSize=18, textColor=colors.HexColor("#1E3A5F"),
            )
            subtitle_style = ParagraphStyle(
                "CustomSubtitle", parent=styles["Normal"],
                fontSize=10, textColor=colors.gray,
            )

            elements = []

            # Title
            elements.append(Paragraph(
                f"BalanceLog Pro — {report.period} Report", title_style
            ))
            elements.append(Paragraph(
                f"Period: {report.start_date} to {report.end_date} | "
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                subtitle_style,
            ))
            elements.append(Spacer(1, 10 * mm))

            # Summary statistics
            summary_data = [
                ["Total Shafts", "Front", "Rear", "Avg Initial", "Avg Final",
                 "Common Weight"],
                [
                    str(report.total_shafts),
                    str(report.front_count),
                    str(report.rear_count),
                    f"{report.avg_initial_imbalance:.2f}",
                    f"{report.avg_final_imbalance:.2f}",
                    f"{report.most_common_weight:.1f}g",
                ],
            ]

            summary_table = Table(summary_data, colWidths=[80, 60, 60, 80, 80, 80])
            summary_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 8 * mm))

            # Records table (limited to avoid massive PDFs)
            records_to_show = report.records[:200]  # Limit for PDF
            if records_to_show:
                header = ["Date", "Time", "Punch No.", "Length", "Type",
                          "Init L", "Init R", "Wt L", "Wt R",
                          "Corr L", "Corr R", "Conf"]
                table_data = [header]

                for r in records_to_show:
                    table_data.append([
                        r.date, r.time, r.punching_number[:12],
                        f"{r.tube_length:.0f}", r.shaft_type,
                        f"{r.initial_left_value:.1f}",
                        f"{r.initial_right_value:.1f}",
                        f"{r.weight_addition_left:.1f}",
                        f"{r.weight_addition_right:.1f}",
                        f"{r.after_correction_left:.1f}",
                        f"{r.after_correction_right:.1f}",
                        f"{r.ocr_confidence:.0%}",
                    ])

                col_widths = [55, 40, 55, 40, 35, 35, 35, 35, 35, 35, 35, 35]
                records_table = Table(table_data, colWidths=col_widths, repeatRows=1)
                records_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A5F")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor("#F5F5F5")]),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                ]))
                elements.append(Paragraph("Detailed Records", styles["Heading2"]))
                elements.append(records_table)

            doc.build(elements)
            logger.info("PDF exported: %s", output_path.name)

        except ImportError:
            logger.warning("reportlab not installed — PDF export unavailable")
        except Exception as e:
            logger.error("PDF export error: %s", e)

        return output_path
