from flask import Blueprint, request, jsonify
from models.compliance import Worker, Qualification, Assessment, QualificationTemplate, db
from datetime import datetime
import json

compliance_bp = Blueprint('compliance', __name__)

@compliance_bp.route('/workers', methods=['GET'])
def get_workers():
    """Get all workers with their basic information"""
    try:
        workers = Worker.query.all()
        return jsonify({
            'success': True,
            'data': [worker.to_dict() for worker in workers]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@compliance_bp.route('/workers', methods=['POST'])
def create_worker():
    """Create a new worker"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['full_name', 'cos_reference', 'job_title', 'soc_code', 'cos_assignment_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Parse date
        cos_date = datetime.strptime(data['cos_assignment_date'], '%Y-%m-%d').date()
        
        # Create worker
        worker = Worker(
            full_name=data['full_name'],
            cos_reference=data['cos_reference'],
            job_title=data['job_title'],
            soc_code=data['soc_code'],
            cos_assignment_date=cos_date
        )
        
        db.session.add(worker)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': worker.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@compliance_bp.route('/workers/<int:worker_id>', methods=['GET'])
def get_worker(worker_id):
    """Get a specific worker with their qualifications and assessments"""
    try:
        worker = Worker.query.get_or_404(worker_id)
        worker_data = worker.to_dict()
        
        # Add qualifications
        worker_data['qualifications'] = [qual.to_dict() for qual in worker.qualifications]
        
        # Add latest assessment
        latest_assessment = Assessment.query.filter_by(worker_id=worker_id).order_by(Assessment.assessment_date.desc()).first()
        worker_data['latest_assessment'] = latest_assessment.to_dict() if latest_assessment else None
        
        return jsonify({
            'success': True,
            'data': worker_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@compliance_bp.route('/workers/<int:worker_id>/qualifications', methods=['POST'])
def add_qualification(worker_id):
    """Add a qualification to a worker"""
    try:
        data = request.get_json()
        
        # Validate worker exists
        worker = Worker.query.get_or_404(worker_id)
        
        # Validate required fields
        required_fields = ['title', 'completion_date']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        # Parse date
        completion_date = datetime.strptime(data['completion_date'], '%Y-%m-%d').date()
        
        # Create qualification
        qualification = Qualification(
            worker_id=worker_id,
            title=data['title'],
            level=data.get('level'),
            completion_date=completion_date,
            issuing_institution=data.get('issuing_institution'),
            certificate_number=data.get('certificate_number'),
            verification_status=data.get('verification_status', 'pending')
        )
        
        db.session.add(qualification)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': qualification.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@compliance_bp.route('/workers/<int:worker_id>/assess', methods=['POST'])
def assess_worker_compliance(worker_id):
    """Perform compliance assessment for a worker"""
    try:
        data = request.get_json()
        
        # Get worker and qualifications
        worker = Worker.query.get_or_404(worker_id)
        qualifications = Qualification.query.filter_by(worker_id=worker_id).all()
        
        # Perform assessment logic
        assessment_result = perform_compliance_assessment(worker, qualifications, data)
        
        # Create assessment record
        assessment = Assessment(
            worker_id=worker_id,
            compliance_status=assessment_result['status'],
            risk_score=assessment_result['risk_score'],
            assessment_outcome=assessment_result['outcome'],
            recommendations=json.dumps(assessment_result['recommendations']),
            assessed_by=data.get('assessed_by', 'AI Agent'),
            ai_confidence_score=assessment_result.get('confidence', 0.85),
            evidence_certificates=data.get('evidence_certificates', 'unknown'),
            evidence_cv_mention=data.get('evidence_cv_mention', 'unknown')
        )
        
        db.session.add(assessment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': assessment.to_dict(),
            'assessment_details': assessment_result
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@compliance_bp.route('/qualification-templates', methods=['GET'])
def get_qualification_templates():
    """Get all qualification templates"""
    try:
        templates = QualificationTemplate.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'data': [template.to_dict() for template in templates]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@compliance_bp.route('/assessments', methods=['GET'])
def get_assessments():
    """Get all assessments with optional filtering"""
    try:
        query = Assessment.query
        
        # Filter by compliance status if provided
        status = request.args.get('status')
        if status:
            query = query.filter_by(compliance_status=status)
        
        # Filter by date range if provided
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Assessment.assessment_date >= start_date)
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Assessment.assessment_date <= end_date)
        
        assessments = query.order_by(Assessment.assessment_date.desc()).all()
        
        # Enrich with worker information
        assessment_data = []
        for assessment in assessments:
            assessment_dict = assessment.to_dict()
            assessment_dict['worker'] = assessment.worker.to_dict()
            assessment_data.append(assessment_dict)
        
        return jsonify({
            'success': True,
            'data': assessment_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def perform_compliance_assessment(worker, qualifications, evidence_data):
    """Core compliance assessment logic"""
    
    # Initialize assessment result
    result = {
        'status': 'compliant',
        'risk_score': 5,
        'outcome': '',
        'recommendations': [],
        'confidence': 0.85
    }
    
    # Check if worker has any qualifications
    if not qualifications:
        result['status'] = 'serious_breach'
        result['risk_score'] = 0
        result['outcome'] = 'No qualifications found for this worker. This constitutes a serious breach of Paragraph C1.38.'
        result['recommendations'] = [
            'Obtain relevant qualifications before sponsorship',
            'Review recruitment processes',
            'Ensure proper qualification verification'
        ]
        return result
    
    # Check qualification timing
    post_cos_qualifications = []
    relevant_qualifications = []
    
    for qual in qualifications:
        if qual.completion_date > worker.cos_assignment_date:
            post_cos_qualifications.append(qual)
        else:
            # Check if qualification is relevant (simplified logic)
            if is_qualification_relevant(qual.title, worker.soc_code):
                relevant_qualifications.append(qual)
    
    # Assessment logic based on findings
    if post_cos_qualifications and not relevant_qualifications:
        result['status'] = 'breach'
        result['risk_score'] = 2
        result['outcome'] = 'Worker has qualifications obtained after CoS assignment date. Worker was not appropriately qualified when sponsored.'
        result['recommendations'] = [
            'Verify qualification completion dates',
            'Ensure pre-sponsorship qualification verification',
            'Update recruitment procedures'
        ]
    elif len(relevant_qualifications) < 3:
        result['status'] = 'breach'
        result['risk_score'] = 3
        result['outcome'] = 'Insufficient relevant qualifications found. Minimum of 3 relevant qualifications required.'
        result['recommendations'] = [
            'Obtain additional relevant qualifications',
            'Verify qualification relevance for role',
            'Consider alternative qualification pathways'
        ]
    elif evidence_data.get('evidence_certificates') == 'none':
        result['status'] = 'breach'
        result['risk_score'] = 2
        result['outcome'] = 'No certificate evidence available on file. Unable to verify claimed qualifications.'
        result['recommendations'] = [
            'Obtain and file qualification certificates',
            'Implement document retention procedures',
            'Verify qualification authenticity'
        ]
    else:
        # Fully compliant
        result['status'] = 'compliant'
        result['risk_score'] = 8
        result['outcome'] = 'Worker meets qualification requirements. All necessary evidence is available and verified.'
        result['recommendations'] = [
            'Maintain current documentation standards',
            'Regular compliance monitoring',
            'Continue best practice procedures'
        ]
    
    # Adjust risk score based on evidence quality
    evidence_certificates = evidence_data.get('evidence_certificates', 'unknown')
    evidence_cv_mention = evidence_data.get('evidence_cv_mention', 'unknown')
    
    if evidence_certificates == 'some':
        result['risk_score'] = max(0, result['risk_score'] - 1)
    elif evidence_certificates == 'none':
        result['risk_score'] = max(0, result['risk_score'] - 2)
    
    if evidence_cv_mention == 'none':
        result['risk_score'] = max(0, result['risk_score'] - 1)
    
    return result

def is_qualification_relevant(qualification_title, soc_code):
    """Check if a qualification is relevant for a given SOC code"""
    
    # Healthcare qualifications for SOC 6146 (Senior Care Worker)
    healthcare_keywords = [
        'care', 'health', 'social care', 'nursing', 'nvq', 'diploma',
        'certificate', 'dementia', 'palliative', 'safeguarding',
        'mental health', 'learning disabilities', 'infection control'
    ]
    
    if soc_code == '6146':
        title_lower = qualification_title.lower()
        return any(keyword in title_lower for keyword in healthcare_keywords)
    
    # Add more SOC code mappings as needed
    return True  # Default to relevant for now

