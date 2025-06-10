from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
from ai_processor import AIDocumentProcessor
import json

ai_compliance_bp = Blueprint('ai_compliance', __name__)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc', 'txt'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@ai_compliance_bp.route('/upload-documents', methods=['POST'])
def upload_documents():
    """Handle multiple document upload and AI analysis"""
    try:
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            return jsonify({'success': False, 'error': 'No files selected'}), 400
        
        # Process each uploaded file
        uploaded_files = []
        document_texts = {}
        
        for file in files:
            if file and allowed_file(file.filename):
                # Generate unique filename
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
                
                # Save file
                file.save(file_path)
                
                # Extract text using AI processor
                processor = AIDocumentProcessor()
                extracted_text = processor.extract_text_from_file(file_path)
                
                # Determine document type based on content
                doc_type = determine_document_type(extracted_text, filename)
                
                uploaded_files.append({
                    'filename': filename,
                    'file_path': file_path,
                    'document_type': doc_type,
                    'upload_time': datetime.now().isoformat()
                })
                
                document_texts[doc_type] = extracted_text
        
        # Perform AI analysis
        analysis_result = perform_ai_analysis(document_texts)
        
        # Generate compliance report
        compliance_report = generate_compliance_report(analysis_result)
        
        return jsonify({
            'success': True,
            'data': {
                'uploaded_files': uploaded_files,
                'analysis_result': analysis_result,
                'compliance_report': compliance_report,
                'processing_time': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def determine_document_type(text, filename):
    """Determine document type based on content and filename"""
    text_lower = text.lower()
    filename_lower = filename.lower()
    
    # Check for CoS document
    if any(keyword in text_lower for keyword in ['certificate of sponsorship', 'cos reference', 'sponsorship certificate']):
        return 'cos_document'
    
    # Check for CV
    if any(keyword in text_lower for keyword in ['curriculum vitae', 'cv', 'resume', 'work experience', 'employment history']):
        return 'cv_document'
    
    # Check for application form
    if any(keyword in text_lower for keyword in ['application form', 'job application', 'application for', 'applicant']):
        return 'application_document'
    
    # Check for qualification certificate
    if any(keyword in text_lower for keyword in ['certificate', 'diploma', 'qualification', 'nvq', 'level']):
        return 'certificate_document'
    
    # Default based on filename
    if 'cos' in filename_lower or 'sponsorship' in filename_lower:
        return 'cos_document'
    elif 'cv' in filename_lower or 'resume' in filename_lower:
        return 'cv_document'
    elif 'application' in filename_lower:
        return 'application_document'
    elif 'certificate' in filename_lower or 'diploma' in filename_lower:
        return 'certificate_document'
    
    return 'other_document'

def perform_ai_analysis(document_texts):
    """Perform comprehensive AI analysis on all documents"""
    processor = AIDocumentProcessor()
    analysis = {}
    
    for doc_type, text in document_texts.items():
        doc_analysis = {
            'document_type': doc_type,
            'text_length': len(text),
            'qualifications': processor.find_qualifications(text),
            'dates_found': [d.strftime('%Y-%m-%d') for d in processor.extract_dates(text)],
            'processed_at': datetime.now().isoformat()
        }
        
        # Extract specific information based on document type
        if doc_type == 'cos_document':
            doc_analysis.update(processor.extract_cos_info(text))
        
        analysis[doc_type] = doc_analysis
    
    # Perform compliance assessment
    compliance_assessment = processor.assess_compliance(analysis)
    analysis['compliance_assessment'] = compliance_assessment
    
    return analysis

def generate_compliance_report(analysis_result):
    """Generate professional compliance report"""
    compliance = analysis_result.get('compliance_assessment', {})
    cos_info = analysis_result.get('cos_document', {})
    
    report = {
        'report_id': str(uuid.uuid4()),
        'generated_at': datetime.now().isoformat(),
        'worker_information': {
            'cos_reference': cos_info.get('cos_reference', 'Not found'),
            'job_title': cos_info.get('job_title', 'Not found'),
            'soc_code': cos_info.get('soc_code', 'Not found'),
            'assignment_date': cos_info.get('assignment_date', 'Not found')
        },
        'compliance_status': compliance.get('compliance_status', 'UNKNOWN'),
        'risk_level': compliance.get('risk_level', 'HIGH'),
        'assessment_findings': compliance.get('findings', []),
        'recommendations': compliance.get('recommendations', []),
        'breach_type': compliance.get('breach_type'),
        'qualifications_found': [],
        'evidence_status': 'UNKNOWN'
    }
    
    # Collect all qualifications found
    for doc_type, doc_data in analysis_result.items():
        if doc_type != 'compliance_assessment' and 'qualifications' in doc_data:
            for qual in doc_data['qualifications']:
                report['qualifications_found'].append({
                    'qualification': qual['qualification'],
                    'found_in': doc_type,
                    'dates': qual.get('potential_dates', [])
                })
    
    # Determine evidence status
    has_certificates = any('certificate' in doc_type for doc_type in analysis_result.keys())
    if has_certificates:
        report['evidence_status'] = 'CERTIFICATES_AVAILABLE'
    elif report['qualifications_found']:
        report['evidence_status'] = 'QUALIFICATIONS_CLAIMED_NO_CERTIFICATES'
    else:
        report['evidence_status'] = 'NO_QUALIFICATIONS_FOUND'
    
    # Generate detailed assessment text
    report['detailed_assessment'] = generate_detailed_assessment_text(report, compliance)
    
    return report

def generate_detailed_assessment_text(report, compliance):
    """Generate detailed assessment text matching the template format"""
    status = compliance.get('compliance_status')
    
    if status == 'COMPLIANT':
        return {
            'outcome': 'FULLY COMPLIANT',
            'home_office_view': 'The Home Office is likely to accept that the sponsored worker met the qualification requirements at the time of sponsorship.',
            'assessment_finding': 'We are satisfied that the sponsored worker held a recognised, care-related qualification prior to the Certificate of Sponsorship (CoS) being assigned, and that evidence of the qualification is retained in the personnel file. No breach of Paragraph C1.38 is identified.'
        }
    
    elif status == 'SERIOUS_BREACH' and compliance.get('breach_type') == 'NO_QUALIFICATION':
        return {
            'outcome': 'SERIOUS BREACH - NO RELEVANT QUALIFICATION',
            'home_office_view': 'The Home Office will likely conclude that the worker lacked the minimum qualification required for the role, resulting in a serious breach of sponsor duties.',
            'assessment_finding': 'You have sponsored a worker who does not hold any relevant qualification for their role. This constitutes a serious breach of Paragraph C1.38, which requires sponsors not to employ individuals who do not have the qualifications, experience, or immigration permission necessary for the job.'
        }
    
    elif status == 'BREACH' and compliance.get('breach_type') == 'POST_COS_QUALIFICATION':
        return {
            'outcome': 'BREACH - QUALIFICATION OBTAINED AFTER CoS',
            'home_office_view': 'The Home Office may determine that the worker was not suitably qualified at the time of sponsorship, leading to a breach of sponsor duties.',
            'assessment_finding': 'Although a qualification has been declared, it was obtained after the Certificate of Sponsorship was issued. The worker was therefore not appropriately qualified when sponsored. This represents a breach of Paragraph C1.38 of the sponsor guidance.'
        }
    
    elif status == 'BREACH' and compliance.get('breach_type') == 'NO_EVIDENCE':
        return {
            'outcome': 'BREACH - NO CERTIFICATE EVIDENCE',
            'home_office_view': 'The Home Office may treat the absence of evidence as non-compliance, particularly if no audit trail exists to support the worker\'s qualifications.',
            'assessment_finding': 'The sponsored worker claims to hold a relevant qualification, but there is no certificate or formal documentation on file. This is a breach of Paragraph C1.38, which requires sponsors to retain evidence that the worker met the requirements at the time of sponsorship.'
        }
    
    else:
        return {
            'outcome': 'ASSESSMENT INCOMPLETE',
            'home_office_view': 'Unable to determine compliance status based on available information.',
            'assessment_finding': 'Insufficient information available to complete compliance assessment. Additional documentation may be required.'
        }

@ai_compliance_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'AI Compliance Processor'})
