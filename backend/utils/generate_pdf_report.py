from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import os

async def generate_student_performance_pdf(data: list, department: str, year: int = None) -> str:
    """
    Generate PDF report for student performance
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    year_str = f"_{year}" if year else ""
    filename = f"student_performance_{department}{year_str}_{timestamp}.pdf"
    filepath = f"/tmp/{filename}"
    
    # Create PDF
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#374151'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Title
    title_text = f"Student Performance Report - {department} Department"
    if year:
        title_text += f" ({year})"
    title = Paragraph(title_text, title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Report Info
    report_info = Paragraph(
        f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>"
        f"Total Students: {len(data)}",
        styles['Normal']
    )
    elements.append(report_info)
    elements.append(Spacer(1, 0.3*inch))
    
    if len(data) == 0:
        no_data = Paragraph("No student data available for this report.", styles['Normal'])
        elements.append(no_data)
    else:
        # Table data
        table_data = [['S.No', 'Name', 'Roll Number', 'CGPA', 'Company', 'Role', 'Status']]
        
        for idx, student in enumerate(data, 1):
            table_data.append([
                str(idx),
                student.get('Name', 'N/A'),
                student.get('Roll Number', 'N/A'),
                str(student.get('CGPA', 'N/A')),
                student.get('Company', 'N/A'),
                student.get('Role', 'N/A'),
                student.get('Status', 'N/A')
            ])
        
        # Create table
        table = Table(table_data, colWidths=[0.6*inch, 1.5*inch, 1.2*inch, 0.8*inch, 1.5*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')])
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary Statistics
        if year:
            elements.append(PageBreak())
            summary_title = Paragraph("Summary Statistics", heading_style)
            elements.append(summary_title)
            elements.append(Spacer(1, 0.2*inch))
            
            placed_count = sum(1 for s in data if s.get('Status') == 'Selected')
            avg_cgpa = sum(float(s.get('CGPA', 0)) for s in data if s.get('CGPA', 0) != 'N/A') / len(data) if data else 0
            
            summary_data = [
                ['Metric', 'Value'],
                ['Total Students', str(len(data))],
                ['Placed Students', str(placed_count)],
                ['Placement Rate', f"{round((placed_count/len(data)*100), 2) if len(data) > 0 else 0}%"],
                ['Average CGPA', f"{round(avg_cgpa, 2)}"]
            ]
            
            summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 11)
            ]))
            
            elements.append(summary_table)
    
    # Build PDF
    doc.build(elements)
    
    return filepath


async def generate_student_list_pdf(students: list, department: str) -> str:
    """
    Generate PDF report for student list with details
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"student_list_{department}_{timestamp}.pdf"
    filepath = f"/tmp/{filename}"
    
    # Create PDF
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Title
    title = Paragraph(f"Student List - {department} Department", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Report Info
    report_info = Paragraph(
        f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}<br/>"
        f"Total Students: {len(students)}",
        styles['Normal']
    )
    elements.append(report_info)
    elements.append(Spacer(1, 0.3*inch))
    
    if len(students) == 0:
        no_data = Paragraph("No students found in this department.", styles['Normal'])
        elements.append(no_data)
    else:
        # Table data
        table_data = [['S.No', 'Name', 'Email', 'Roll Number', 'CGPA', 'Skills', 'Status']]
        
        for idx, student in enumerate(students, 1):
            skills_str = ', '.join(student.get('skills', [])[:3])
            if len(student.get('skills', [])) > 3:
                skills_str += '...'
            
            table_data.append([
                str(idx),
                student.get('name', 'N/A'),
                student.get('email', 'N/A'),
                student.get('roll_number', 'N/A'),
                str(student.get('cgpa', 'N/A')),
                skills_str or 'N/A',
                'Approved' if student.get('is_approved') else 'Pending'
            ])
        
        # Create table with adjusted widths
        table = Table(table_data, colWidths=[0.5*inch, 1.3*inch, 1.5*inch, 1*inch, 0.7*inch, 1.8*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')])
        ]))
        
        elements.append(table)
    
    # Build PDF
    doc.build(elements)
    
    return filepath
