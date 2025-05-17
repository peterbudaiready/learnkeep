from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, ListItem, ListFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import matplotlib.pyplot as plt
import pandas as pd
from typing import Dict, Any, List
import base64

def generate_course_pdf(course_dict: Dict[str, Any], subject: str) -> bytes:
    """
    Generate a PDF document from course content.
    
    Args:
        course_dict: Dictionary containing course content
        subject: Course subject/title
    
    Returns:
        bytes: PDF file content
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER
    ))
    
    styles.add(ParagraphStyle(
        name='WeekTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        spaceBefore=20
    ))
    
    styles.add(ParagraphStyle(
        name='Paragraph',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12
    ))
    
    # Build the document content
    story = []
    
    # Add main title
    story.append(Paragraph(subject, styles['CustomTitle']))
    story.append(Spacer(1, 0.5*inch))
    
    # Process each week
    for week_key in sorted(course_dict.keys()):
        week_data = course_dict[week_key]
        
        # Add week title
        story.append(Paragraph(week_key.replace('Week', 'Week '), styles['WeekTitle']))
        
        # Process paragraphs
        for para_key, para_data in week_data.get('paragraphs', {}).items():
            # Add paragraph text
            story.append(Paragraph(para_data['text'], styles['Paragraph']))
            
            # Add resources as bullet points if any
            if para_data.get('resources'):
                resources = []
                for text, url in para_data['resources']:
                    resources.append(f"{text}: {url}")
                story.append(ListFlowable(
                    [ListItem(Paragraph(resource, styles['Paragraph'])) for resource in resources],
                    bulletType='bullet'
                ))
        
        # Process supplemental materials
        supp = week_data.get('supplemental', {})
        
        # Add bullet points
        if supp.get('bulletpoints'):
            story.append(Paragraph("Key Takeaways:", styles['Heading2']))
            story.append(ListFlowable(
                [ListItem(Paragraph(bp, styles['Paragraph'])) for bp in supp['bulletpoints']],
                bulletType='bullet'
            ))
        
        # Add images
        for img_url in supp.get('images', []):
            try:
                img = Image(img_url, width=400, height=300)
                story.append(img)
                story.append(Spacer(1, 0.2*inch))
            except Exception:
                pass
        
        # Add charts and tables
        for chart_code in supp.get('charts', []):
            try:
                # Create a new figure for each chart
                plt.figure(figsize=(6, 4))
                # Execute the chart code
                exec(chart_code, globals())
                # Save the chart to a bytes buffer
                buf = io.BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                plt.close()
                buf.seek(0)
                # Add the chart to the PDF
                img = Image(buf, width=400, height=300)
                story.append(img)
                story.append(Spacer(1, 0.2*inch))
            except Exception:
                pass
        
        for table_code in supp.get('tables', []):
            try:
                # Execute the table code
                exec(table_code, globals())
                # Get the last created DataFrame
                df = pd.DataFrame(locals().get('df', pd.DataFrame()))
                if not df.empty:
                    # Convert DataFrame to list of lists for ReportLab
                    data = [df.columns.tolist()] + df.values.tolist()
                    # Create table
                    table = Table(data)
                    # Add table style
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 12),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 10),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(table)
                    story.append(Spacer(1, 0.2*inch))
            except Exception:
                pass
        
        story.append(Spacer(1, 0.5*inch))
    
    # Build the PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue() 