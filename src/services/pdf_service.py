"""
PDF Generation Service for AI-generated content
"""
import logging
from io import BytesIO
from fpdf import FPDF
from datetime import datetime

logger = logging.getLogger(__name__)


class UTF8PDF(FPDF):
    """PDF class with UTF-8 support for Russian and Kazakh"""

    def __init__(self):
        super().__init__()
        self.add_font('DejaVu', '', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', uni=True)
        self.add_font('DejaVu', 'B', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', uni=True)
        self.set_font('DejaVu', '', 12)


class PDFService:
    """Service for generating PDF documents"""

    @staticmethod
    def generate_lesson_plan(content: str, title: str = "План урока") -> BytesIO:
        """
        Generate PDF for lesson plan

        Args:
            content: AI-generated lesson plan text
            title: Document title

        Returns:
            BytesIO object with PDF content
        """
        try:
            pdf = UTF8PDF()
            pdf.add_page()

            # Add title
            pdf.set_font('DejaVu', 'B', 16)
            pdf.cell(0, 10, title, ln=True, align='C')
            pdf.ln(5)

            # Add generation date
            pdf.set_font('DejaVu', '', 10)
            pdf.cell(0, 10, f"Создано: {datetime.now().strftime('%d.%m.%Y %H:%M')}", ln=True)
            pdf.ln(5)

            # Add content
            pdf.set_font('DejaVu', '', 12)
            # Split content by lines and add each line
            for line in content.split('\n'):
                # Handle markdown headers
                if line.startswith('# '):
                    pdf.set_font('DejaVu', 'B', 14)
                    pdf.multi_cell(0, 8, line[2:])
                    pdf.set_font('DejaVu', '', 12)
                elif line.startswith('## '):
                    pdf.set_font('DejaVu', 'B', 13)
                    pdf.multi_cell(0, 7, line[3:])
                    pdf.set_font('DejaVu', '', 12)
                elif line.startswith('### '):
                    pdf.set_font('DejaVu', 'B', 12)
                    pdf.multi_cell(0, 6, line[4:])
                    pdf.set_font('DejaVu', '', 12)
                elif line.strip().startswith('**') and line.strip().endswith('**'):
                    # Bold text
                    pdf.set_font('DejaVu', 'B', 12)
                    pdf.multi_cell(0, 6, line.strip()[2:-2])
                    pdf.set_font('DejaVu', '', 12)
                elif line.strip():
                    pdf.multi_cell(0, 6, line)
                else:
                    pdf.ln(3)

            # Generate PDF to BytesIO
            pdf_output = BytesIO()
            pdf_output.write(pdf.output())
            pdf_output.seek(0)

            return pdf_output

        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise

    @staticmethod
    def generate_test(content: str, title: str = "Тест") -> BytesIO:
        """Generate PDF for test/quiz"""
        return PDFService.generate_lesson_plan(content, title)

    @staticmethod
    def generate_ktp(content: str, title: str = "КТП") -> BytesIO:
        """Generate PDF for calendar-thematic planning"""
        return PDFService.generate_lesson_plan(content, title)

    @staticmethod
    def generate_homework(content: str, title: str = "Домашнее задание") -> BytesIO:
        """Generate PDF for homework"""
        return PDFService.generate_lesson_plan(content, title)


# Global instance
pdf_service = PDFService()
