from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
import os
import tempfile
import json
import re
from datetime import datetime
import PyPDF2
import docx
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io

# Create Flask app with template folder
app = Flask(__name__, 
           template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
app.config['SECRET_KEY'] = 'asdf#FGSgvasgf$5$WGT'

# Enable CORS for all routes
CORS(app)

# In-memory storage for demo (replace with database in production)
workers_data = []
assessments_data = []

@app.route('/')
def dashboard():
    """Serve the main dashboard"""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        return f"<h1>Template Error</h1><p>{str(e)}</p><p>Template folder: {app.template_folder}</p>"

@app.route('/test')
def test():
    """Test route"""
    return "<h1>✅ Test Route Working!</h1><p>Flask server is responding correctly.</p>"

@app.route('/upload')
def upload_page():
    """Upload page route"""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        return f"<h1>Template Error</h1><p>{str(e)}</p><p>Template folder: {app.template_folder}</p>"

@app.route('/dashboard')
def dashboard_direct():
    """Direct dashboard route"""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        return f"<h1>Template Error</h1><p>{str(e)}</p><p>Template folder: {app.template_folder}</p>"

# Enhanced document extraction functions
def extract_worker_name_enhanced(text, filenames):
    """Enhanced worker name extraction with filename priority"""
    
    # FIRST: Try to extract from filenames (highest priority)
    for filename in filenames:
        # Look for patterns like "Alen Thomas" in filename
        filename_clean = filename.replace('.pdf', '').replace('.docx', '').replace('.doc', '')
        
        # Pattern: "CV Alen Thomas" or "CoS-C2G8Y18250Q-Alen Thomas"
        name_match = re.search(r'(?:CV|CoS.*?-)([A-Z][a-z]+\s+[A-Z][a-z]+)', filename_clean)
        if name_match:
            name = name_match.group(1).strip()
            # Validate it's not a company name
            if not any(company_word in name.lower() for company_word in ['care', 'ltd', 'limited', 'company', 'services', 'group']):
                return name
        
        # Pattern: "Application form -Alen Thomas"
        name_match = re.search(r'-([A-Z][a-z]+\s+[A-Z][a-z]+)', filename_clean)
        if name_match:
            name = name_match.group(1).strip()
            # Validate it's not a company name
            if not any(company_word in name.lower() for company_word in ['care', 'ltd', 'limited', 'company', 'services', 'group']):
                return name
    
    # SECOND: Try to extract from document text (lower priority)
    name_patterns = [
        r'(?:Name|Full Name|Worker|Employee|Applicant)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'(?:Mr|Mrs|Ms|Miss|Dr)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'Certificate of Sponsorship.*?for\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'CoS.*?for\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'assigned.*?to\s+([A-Z][a-z]+\s+[A-Z][a-z]+)'
    ]
    
    # Clean the text and try patterns
    lines = text.split('\n')
    
    for pattern in name_patterns:
        for line in lines:
            line = line.strip()
            if len(line) > 100:  # Skip very long lines
                continue
                
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Validate the name and exclude company names
                if (2 <= len(name.split()) <= 4 and 
                    all(word.isalpha() for word in name.split()) and
                    not any(company_word in name.lower() for company_word in ['care', 'ltd', 'limited', 'company', 'services', 'group', 'greensleeves'])):
                    return name
    
    return "Unknown Worker"

def extract_cos_reference_enhanced(text, filenames):
    """Enhanced CoS reference extraction with filename fallback"""
    
    # Try to extract from document text first
    cos_patterns = [
        r'CoS[:\s]*([A-Z0-9]{10,12})',
        r'Certificate of Sponsorship[:\s]*([A-Z0-9]{10,12})',
        r'Reference[:\s]*([A-Z0-9]{10,12})',
        r'COS[:\s]*([A-Z0-9]{10,12})',
        r'\(([A-Z0-9]{10,12})\)',
        r'([A-Z]\d[A-Z]\d[A-Z]\d{6})',  # Pattern like C2G8Y18250Q
    ]
    
    for pattern in cos_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match) >= 10:
                return match.upper()
    
    # Fallback: Extract from filenames
    for filename in filenames:
        # Look for CoS reference in filename like "CoS-C2G8Y18250Q-Alen Thomas.pdf"
        cos_match = re.search(r'CoS-([A-Z0-9]{10,12})', filename)
        if cos_match:
            return cos_match.group(1)
        
        # Look for pattern like C2G8Y18250Q anywhere in filename
        cos_match = re.search(r'([A-Z]\d[A-Z]\d[A-Z]\d{6})', filename)
        if cos_match:
            return cos_match.group(1)
    
    return "Unknown CoS"

def extract_assignment_date(text):
    """Extract assignment date from document text"""
    date_patterns = [
        r'(?:assigned|assignment|start|commencement).*?(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
        r'(?:assigned|assignment|start|commencement).*?(\d{1,2}\s+\w+\s+\d{4})',
        r'(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})',
        r'(\d{1,2}\s+\w+\s+\d{4})'
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return matches[0]
    
    return "Date not found"

def extract_text_from_pdf(file_path):
    """Extract text from PDF file"""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(file_path):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting text from DOCX: {e}")
        return ""

def generate_compliance_assessment(worker_name, cos_reference, assignment_date, job_title, soc_code, document_text, filenames):
    """Generate comprehensive compliance assessment using your professional template"""
    
    # Check for healthcare qualifications
    healthcare_qualifications = [
        "Care Certificate", "Level 2 Diploma in Care", "Level 3 Diploma in Health and Social Care",
        "Level 3 Diploma in Adult Care", "Level 4 Diploma in Adult Care", 
        "Level 5 Diploma in Leadership for Health and Social Care",
        "NVQ Level 2 in Health and Social Care", "NVQ Level 3 in Health and Social Care",
        "NVQ Level 4 in Health and Social Care", "SVQ Level 2 in Health and Social Care",
        "SVQ Level 3 in Health and Social Care", "QCF Level 2 Diploma in Health and Social Care",
        "QCF Level 3 Diploma in Health and Social Care", "BTEC Level 2 in Health and Social Care",
        "BTEC Level 3 in Health and Social Care", "City & Guilds Level 2 in Care",
        "City & Guilds Level 3 in Health and Social Care", "BSc Nursing", "Bachelor of Social Work"
    ]
    
    # Check for non-care qualifications (engineering, etc.)
    non_care_qualifications = [
        "engineering", "mechanical", "electrical", "civil", "chemical", "software",
        "computer science", "IT", "technology", "mathematics", "physics", "chemistry",
        "business", "finance", "accounting", "marketing", "management"
    ]
    
    # Analyze qualifications
    found_healthcare_quals = []
    found_non_care_quals = []
    
    text_lower = document_text.lower()
    
    for qual in healthcare_qualifications:
        if qual.lower() in text_lower:
            found_healthcare_quals.append(qual)
    
    for qual in non_care_qualifications:
        if qual in text_lower:
            found_non_care_quals.append(qual)
    
    # Determine compliance status
    if found_non_care_quals and not found_healthcare_quals:
        compliance_status = "SERIOUS_BREACH"
        status_color = "#dc3545"
        risk_level = "HIGH"
    elif not found_healthcare_quals:
        compliance_status = "BREACH"
        status_color = "#fd7e14"
        risk_level = "MEDIUM"
    elif found_healthcare_quals:
        compliance_status = "COMPLIANT"
        status_color = "#28a745"
        risk_level = "LOW"
    else:
        compliance_status = "PENDING"
        status_color = "#6c757d"
        risk_level = "MEDIUM"
    
    # Generate professional assessment report using your template format
    if compliance_status == "SERIOUS_BREACH":
        report_text = f"""You assigned Certificate of Sponsorship (CoS) for {worker_name} ({cos_reference}) on {assignment_date} to work as a {job_title} under Standard Occupational Classification (SOC) code {soc_code} Care workers and home carers.

{worker_name}'s file has been reviewed for evidence of appropriate qualifications and training for the care role. The documentation provided shows qualifications in {', '.join(found_non_care_quals) if found_non_care_quals else 'non-care related fields'}, which are not relevant to health and social care work.

The file does not include complete proof of recognised care qualifications such as a Care Certificate, NVQ Level 2 or 3 in Health and Social Care, or other UK-recognised care qualifications. Additionally, there may be insufficient evidence of training in key care-related courses, such as First Aid, Manual Handling, or Safeguarding.

The care role requires specific qualifications and training to ensure safe and lawful practice when working with vulnerable individuals. Complete documentation of appropriate qualifications is essential for compliance with regulatory requirements.

In summary, while {worker_name} may have relevant experience in other fields, the incomplete documentation of recognised care qualifications indicates potential non-compliance with Sponsor Guidance Rule C1.38, which requires that all sponsored workers be appropriately qualified, registered, or experienced for the job they are assigned.

Furthermore, any qualifications obtained after the CoS assignment date of {assignment_date} cannot be used to demonstrate eligibility at the time of sponsorship, which constitutes a serious breach of sponsor duties."""

    elif compliance_status == "BREACH":
        report_text = f"""You assigned Certificate of Sponsorship (CoS) for {worker_name} ({cos_reference}) on {assignment_date} to work as a {job_title} under Standard Occupational Classification (SOC) code {soc_code} Care workers and home carers.

{worker_name}'s file has been reviewed for evidence of appropriate qualifications and training for the care role. While some documentation has been provided, there are gaps in the evidence of required qualifications for health and social care work.

The file does not include complete proof of recognised care qualifications such as a Care Certificate, NVQ Level 2 or 3 in Health and Social Care, or other UK-recognised care qualifications. Additionally, there may be insufficient evidence of training in key care-related courses, such as First Aid, Manual Handling, or Safeguarding.

The care role requires specific qualifications and training to ensure safe and lawful practice when working with vulnerable individuals. Complete documentation of appropriate qualifications is essential for compliance with regulatory requirements.

In summary, while {worker_name} may have some relevant experience, the incomplete documentation of recognised care qualifications indicates potential non-compliance with Sponsor Guidance Rule C1.38, which requires that all sponsored workers be appropriately qualified, registered, or experienced for the job they are assigned."""

    else:  # COMPLIANT
        report_text = f"""You assigned Certificate of Sponsorship (CoS) for {worker_name} ({cos_reference}) on {assignment_date} to work as a {job_title} under Standard Occupational Classification (SOC) code {soc_code} Care workers and home carers.

{worker_name}'s file has been reviewed for evidence of appropriate qualifications and training for the care role. The documentation provided demonstrates relevant qualifications including {', '.join(found_healthcare_quals)}.

The file includes evidence of recognised care qualifications that are appropriate for health and social care work. The qualifications demonstrated are suitable for the assigned role and meet the requirements for working with vulnerable individuals.

The care role requires specific qualifications and training to ensure safe and lawful practice when working with vulnerable individuals. The documentation provided demonstrates compliance with these requirements.

In summary, {worker_name} has demonstrated appropriate qualifications for the assigned care role, indicating compliance with Sponsor Guidance Rule C1.38, which requires that all sponsored workers be appropriately qualified, registered, or experienced for the job they are assigned."""

    return {
        'id': len(assessments_data) + 1,
        'worker_name': worker_name,
        'cos_reference': cos_reference,
        'assignment_date': assignment_date,
        'job_title': job_title,
        'soc_code': soc_code,
        'compliance_status': compliance_status,
        'status_color': status_color,
        'risk_level': risk_level,
        'report_text': report_text,
        'found_healthcare_quals': found_healthcare_quals,
        'found_non_care_quals': found_non_care_quals,
        'assessment_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# API Routes
@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'AI Qualification Compliance System is running',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/dashboard-stats')
def dashboard_stats():
    """Get dashboard statistics with visual analytics data"""
    try:
        total_workers = len(workers_data)
        compliant_workers = len([w for w in workers_data if w.get('compliance_status') == 'COMPLIANT'])
        breach_workers = len([w for w in workers_data if w.get('compliance_status') == 'BREACH'])
        serious_breach_workers = len([w for w in workers_data if w.get('compliance_status') == 'SERIOUS_BREACH'])
        pending_workers = len([w for w in workers_data if w.get('compliance_status') == 'PENDING'])
        
        compliance_rate = round((compliant_workers / total_workers * 100) if total_workers > 0 else 0)
        
        # Risk distribution
        high_risk = len([w for w in workers_data if w.get('risk_level') == 'HIGH'])
        medium_risk = len([w for w in workers_data if w.get('risk_level') == 'MEDIUM'])
        low_risk = len([w for w in workers_data if w.get('risk_level') == 'LOW'])
        
        # Recent assessments (last 5)
        recent_assessments = []
        for assessment in assessments_data[-5:]:
            recent_assessments.append({
                'worker_name': assessment['worker_name'],
                'status': assessment['compliance_status'],
                'date': assessment['assessment_date']
            })
        
        return jsonify({
            'success': True,
            'data': {
                'total_workers': total_workers,
                'compliant_workers': compliant_workers,
                'breach_workers': breach_workers,
                'serious_breach_workers': serious_breach_workers,
                'compliance_rate': compliance_rate,
                'compliance_breakdown': {
                    'compliant': compliant_workers,
                    'breach': breach_workers,
                    'serious_breach': serious_breach_workers,
                    'pending': pending_workers
                },
                'risk_distribution': {
                    'high': high_risk,
                    'medium': medium_risk,
                    'low': low_risk
                },
                'recent_assessments': recent_assessments
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/workers', methods=['GET'])
def get_workers():
    """Get all workers"""
    try:
        return jsonify({
            'success': True,
            'data': workers_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/workers', methods=['POST'])
def add_worker():
    """Add a new worker"""
    try:
        data = request.get_json()
        
        worker = {
            'id': len(workers_data) + 1,
            'full_name': data['full_name'],
            'cos_reference': data['cos_reference'],
            'job_title': data['job_title'],
            'soc_code': data['soc_code'],
            'compliance_status': 'PENDING',
            'risk_level': 'MEDIUM',
            'date_added': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        workers_data.append(worker)
        
        return jsonify({
            'success': True,
            'data': worker
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/worker/<int:worker_id>/report')
def get_worker_report(worker_id):
    """Get specific worker's compliance report"""
    try:
        # Find worker
        worker = next((w for w in workers_data if w['id'] == worker_id), None)
        if not worker:
            return jsonify({'success': False, 'error': 'Worker not found'}), 404
        
        # Find assessment for this worker
        assessment = next((a for a in assessments_data if a['worker_name'] == worker['full_name']), None)
        if not assessment:
            return jsonify({'success': False, 'error': 'No assessment found for this worker'}), 404
        
        return jsonify({
            'success': True,
            'data': {
                'worker': worker,
                'compliance_report': assessment
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-documents', methods=['POST'])
def upload_documents():
    """Upload and analyze documents"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'success': False, 'error': 'No files selected'}), 400
        
        # Save uploaded files temporarily
        temp_files = []
        filenames = []
        
        for file in files:
            if file.filename:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1])
                file.save(temp_file.name)
                temp_files.append(temp_file.name)
                filenames.append(file.filename)
        
        # Extract text from all documents
        combined_text = ""
        for temp_file in temp_files:
            if temp_file.endswith('.pdf'):
                combined_text += extract_text_from_pdf(temp_file) + "\n"
            elif temp_file.endswith(('.docx', '.doc')):
                combined_text += extract_text_from_docx(temp_file) + "\n"
        
        # Extract information
        worker_name = extract_worker_name_enhanced(combined_text, filenames)
        cos_reference = extract_cos_reference_enhanced(combined_text, filenames)
        assignment_date = extract_assignment_date(combined_text)
        
        # Default job details (can be enhanced to extract from documents)
        job_title = "Care Assistant Job type"
        soc_code = "6145"
        
        # Generate compliance assessment
        assessment = generate_compliance_assessment(
            worker_name, cos_reference, assignment_date, job_title, soc_code, combined_text, filenames
        )
        
        # Store assessment
        assessments_data.append(assessment)
        
        # Add or update worker in workers_data
        existing_worker = next((w for w in workers_data if w['full_name'] == worker_name), None)
        if existing_worker:
            # Update existing worker
            existing_worker['compliance_status'] = assessment['compliance_status']
            existing_worker['risk_level'] = assessment['risk_level']
            existing_worker['cos_reference'] = cos_reference
            existing_worker['job_title'] = job_title
            existing_worker['soc_code'] = soc_code
        else:
            # Add new worker
            new_worker = {
                'id': len(workers_data) + 1,
                'full_name': worker_name,
                'cos_reference': cos_reference,
                'job_title': job_title,
                'soc_code': soc_code,
                'compliance_status': assessment['compliance_status'],
                'risk_level': assessment['risk_level'],
                'date_added': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            workers_data.append(new_worker)
        
        # Clean up temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': {
                'compliance_report': assessment,
                'worker_added': True
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-pdf/<int:assessment_id>')
def generate_pdf(assessment_id):
    """Generate PDF report for assessment"""
    try:
        # Find assessment
        assessment = next((a for a in assessments_data if a['id'] == assessment_id), None)
        if not assessment:
            return jsonify({'success': False, 'error': 'Assessment not found'}), 404
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            textColor='#212529'
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            alignment=4,  # Justify
            leading=16
        )
        
        # Build PDF content
        story = []
        
        # Title
        story.append(Paragraph("📋 Compliance Analysis Report", title_style))
        story.append(Spacer(1, 20))
        
        # Status alert
        if assessment['compliance_status'] == 'SERIOUS_BREACH':
            status_text = "🚨 SERIOUS BREACH DETECTED - Qualification requirements not met"
        elif assessment['compliance_status'] == 'BREACH':
            status_text = "⚠️ COMPLIANCE BREACH DETECTED - Review required"
        else:
            status_text = "✅ COMPLIANT - All requirements met"
        
        story.append(Paragraph(status_text, heading_style))
        story.append(Spacer(1, 20))
        
        # Assessment report
        story.append(Paragraph("Assessment Report", heading_style))
        story.append(Paragraph(assessment['report_text'], body_style))
        story.append(Spacer(1, 20))
        
        # Summary
        story.append(Paragraph("Assessment Summary", heading_style))
        summary_text = f"""
        <b>Worker:</b> {assessment['worker_name']}<br/>
        <b>CoS Reference:</b> {assessment['cos_reference']}<br/>
        <b>Job Title:</b> {assessment['job_title']}<br/>
        <b>SOC Code:</b> {assessment['soc_code']}<br/>
        <b>Assignment Date:</b> {assessment['assignment_date']}<br/>
        <b>Status:</b> {assessment['compliance_status']}<br/>
        <b>Risk Level:</b> {assessment['risk_level']}<br/>
        <b>Assessment Date:</b> {assessment['assessment_date']}
        """
        story.append(Paragraph(summary_text, body_style))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Return PDF file
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"compliance_report_{assessment['worker_name'].replace(' ', '_')}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/email-report', methods=['POST'])
def email_report():
    """Email compliance report"""
    try:
        data = request.get_json()
        assessment_id = data.get('assessment_id')
        email = data.get('email')
        
        if not assessment_id or not email:
            return jsonify({'success': False, 'error': 'Missing assessment ID or email'}), 400
        
        # Find assessment
        assessment = next((a for a in assessments_data if a['id'] == assessment_id), None)
        if not assessment:
            return jsonify({'success': False, 'error': 'Assessment not found'}), 404
        
        # For demo purposes, just return success
        # In production, implement actual email sending
        return jsonify({
            'success': True,
            'message': f'Report for {assessment["worker_name"]} would be sent to {email}'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/query', methods=['POST'])
def ai_query():
    """Handle AI assistant queries"""
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        
        response = get_ai_response(query)
        
        return jsonify({
            'success': True,
            'data': {
                'response': response['answer'],
                'confidence': response['confidence'],
                'suggestions': response['suggestions']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_ai_response(query):
    """Generate AI responses for compliance questions"""
    responses = {
        'care assistant': {
            'answer': 'Care Assistants (SOC 6145) typically require: Care Certificate, NVQ Level 2/3 in Health and Social Care, or equivalent qualifications. Essential training includes First Aid, Manual Handling, Safeguarding, and Infection Control.',
            'confidence': 0.95,
            'suggestions': ['Required qualifications', 'Essential training', 'SOC codes']
        },
        'soc 6145': {
            'answer': 'SOC 6145 covers Care workers and home carers. This includes care assistants, home care workers, and support workers in residential care. Minimum qualification is typically Care Certificate or NVQ Level 2.',
            'confidence': 0.92,
            'suggestions': ['Care Certificate requirements', 'NVQ qualifications', 'Training requirements']
        },
        'qualification': {
            'answer': 'Key qualifications for care roles include: Care Certificate (entry level), NVQ/QCF Level 2-3 in Health and Social Care, BTEC qualifications, and relevant degree programs. All must be UK-recognized.',
            'confidence': 0.88,
            'suggestions': ['Mandatory training', 'Qualification levels']
        },
        'training': {
            'answer': 'Mandatory training includes: First Aid, Manual Handling, Safeguarding Adults, Safeguarding Children, Infection Control, Health and Safety, Fire Safety, and Food Hygiene.',
            'confidence': 0.90,
            'suggestions': ['Training frequency', 'Certification requirements']
        }
    }
    
    # Find best match
    for key, response in responses.items():
        if key in query:
            return response
    
    # Default response
    return {
        'answer': 'I can help you with qualification requirements, SOC codes, training needs, and compliance questions. Please ask about specific topics like "Care Assistant qualifications" or "SOC code 6145".',
        'confidence': 0.75,
        'suggestions': ['Care Assistant qualifications', 'SOC code 6145', 'Required training', 'Compliance requirements']
    }

if __name__ == '__main__':
    print("🚀 Starting AI Qualification Compliance System...")
    print("📊 Dashboard: http://localhost:5000" )
    print("🧪 Test: http://localhost:5000/test" )
    print("📁 Upload: http://localhost:5000/upload" )
    print("🤖 AI API: http://localhost:5000/api/ai/query" )
    print("📋 Health: http://localhost:5000/api/health" )
    app.run(host='0.0.0.0', port=8000, debug=True)

