"""
PDF Test Data Generator
Generates 100 sample PDFs across diverse categories for testing the PDF search system.
Categories: Financial Reports, Technical Docs, HR Policies, Legal Contracts, Research Papers
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
import random

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "pdfs"

# Content templates for each category
CATEGORIES = {
    "financial": {
        "filenames": [
            "Q{quarter}_2024_Financial_Report.pdf",
            "Annual_Budget_{year}_Summary.pdf",
            "Revenue_Analysis_{month}_2024.pdf",
            "Expense_Report_Q{quarter}_2024.pdf",
            "Investment_Portfolio_Review_{year}.pdf",
            "Cash_Flow_Statement_{month}_2024.pdf",
            "Profit_Loss_Statement_Q{quarter}.pdf",
            "Financial_Forecast_2025.pdf",
            "Audit_Report_{year}.pdf",
            "Tax_Filing_Summary_2024.pdf",
        ],
        "content_templates": [
            """
            <b>Executive Summary</b><br/><br/>
            This financial report covers the period ending {period}. Total revenue reached ${revenue:,}, 
            representing a {growth}% increase compared to the previous period. Operating expenses 
            were ${expenses:,}, resulting in a net profit margin of {margin}%.<br/><br/>
            
            <b>Key Highlights</b><br/><br/>
            • Revenue growth driven primarily by expansion in enterprise sales<br/>
            • Cost optimization initiatives reduced overhead by {savings}%<br/>
            • Cash reserves remain strong at ${cash:,}<br/>
            • Accounts receivable turnover improved to {ar_days} days<br/><br/>
            
            <b>Segment Performance</b><br/><br/>
            The {segment} division contributed {segment_pct}% of total revenue, with particularly 
            strong performance in {region}. New customer acquisition increased by {new_customers}%, 
            while customer retention remained stable at {retention}%.<br/><br/>
            
            <b>Outlook</b><br/><br/>
            Management expects continued growth in the upcoming quarter, with projected revenue 
            of ${projected:,}. Key initiatives include expansion of the sales team, investment 
            in R&D, and strategic partnerships in emerging markets.
            """,
        ],
    },
    "technical": {
        "filenames": [
            "API_Documentation_v{version}.pdf",
            "System_Architecture_Overview.pdf",
            "Database_Schema_Design.pdf",
            "Security_Best_Practices_Guide.pdf",
            "Deployment_Guide_AWS.pdf",
            "Performance_Optimization_Report.pdf",
            "Code_Review_Standards.pdf",
            "Microservices_Migration_Plan.pdf",
            "CI_CD_Pipeline_Setup.pdf",
            "Kubernetes_Configuration_Guide.pdf",
            "Data_Pipeline_Architecture.pdf",
            "Machine_Learning_Model_Specs.pdf",
            "Network_Infrastructure_Design.pdf",
            "Backup_Recovery_Procedures.pdf",
            "Load_Testing_Results_{date}.pdf",
        ],
        "content_templates": [
            """
            <b>Technical Overview</b><br/><br/>
            This document describes the {system_name} system architecture and implementation details.
            The system is designed to handle {throughput:,} requests per second with 99.9% uptime.<br/><br/>
            
            <b>Architecture Components</b><br/><br/>
            • <b>Frontend</b>: React.js application with TypeScript, hosted on CloudFront CDN<br/>
            • <b>API Layer</b>: RESTful services built with {framework}, running on {compute}<br/>
            • <b>Database</b>: {database} cluster with {replicas} read replicas<br/>
            • <b>Cache</b>: Redis cluster for session management and hot data caching<br/>
            • <b>Message Queue</b>: {queue} for async processing<br/><br/>
            
            <b>Security Considerations</b><br/><br/>
            All API endpoints require JWT authentication. Data is encrypted at rest using AES-256 
            and in transit using TLS 1.3. Rate limiting is enforced at {rate_limit} requests per minute 
            per user. SQL injection and XSS protections are implemented at the framework level.<br/><br/>
            
            <b>Scalability</b><br/><br/>
            The system uses horizontal scaling with auto-scaling groups. Current capacity supports 
            {users:,} concurrent users. Database sharding is implemented by {shard_key} to distribute 
            load across {shards} shards.
            """,
        ],
    },
    "hr": {
        "filenames": [
            "Employee_Handbook_2024.pdf",
            "Remote_Work_Policy.pdf",
            "Benefits_Overview_2024.pdf",
            "Performance_Review_Guidelines.pdf",
            "Onboarding_Checklist.pdf",
            "Leave_Policy_Update.pdf",
            "Compensation_Structure.pdf",
            "Training_Development_Program.pdf",
            "Diversity_Inclusion_Report.pdf",
            "Workplace_Safety_Guidelines.pdf",
            "Travel_Expense_Policy.pdf",
            "Code_of_Conduct.pdf",
            "Termination_Procedures.pdf",
            "Interview_Guidelines.pdf",
            "Promotion_Criteria.pdf",
        ],
        "content_templates": [
            """
            <b>Policy Overview</b><br/><br/>
            This document outlines the company's {policy_name} policy, effective {effective_date}. 
            All employees are expected to review and comply with these guidelines.<br/><br/>
            
            <b>Eligibility</b><br/><br/>
            This policy applies to all {employee_type} employees who have completed their 
            {probation_period}-day probationary period. Contractors and temporary workers should 
            refer to their specific agreements.<br/><br/>
            
            <b>Key Provisions</b><br/><br/>
            • Employees are entitled to {days} days of paid time off annually<br/>
            • Health insurance coverage includes medical, dental, and vision<br/>
            • 401(k) matching up to {match}% of base salary<br/>
            • Professional development budget of ${dev_budget:,} per year<br/>
            • Flexible work arrangements available upon manager approval<br/><br/>
            
            <b>Compliance Requirements</b><br/><br/>
            Employees must complete mandatory training within {training_days} days of hire. 
            Annual compliance certifications are required by {compliance_date}. Violations may 
            result in disciplinary action up to and including termination.<br/><br/>
            
            <b>Questions and Support</b><br/><br/>
            For questions regarding this policy, contact HR at hr@company.com or extension {ext}.
            """,
        ],
    },
    "legal": {
        "filenames": [
            "Master_Service_Agreement_Template.pdf",
            "NDA_Standard_Form.pdf",
            "Software_License_Agreement.pdf",
            "Data_Processing_Agreement.pdf",
            "Terms_of_Service_v{version}.pdf",
            "Privacy_Policy_2024.pdf",
            "Vendor_Contract_Guidelines.pdf",
            "Intellectual_Property_Policy.pdf",
            "Litigation_Hold_Notice.pdf",
            "Compliance_Audit_Report.pdf",
            "GDPR_Compliance_Framework.pdf",
            "Employment_Agreement_Template.pdf",
            "Shareholder_Agreement.pdf",
            "Merger_Acquisition_Checklist.pdf",
            "Regulatory_Filing_Requirements.pdf",
        ],
        "content_templates": [
            """
            <b>AGREEMENT</b><br/><br/>
            This {agreement_type} Agreement ("Agreement") is entered into as of {effective_date} 
            by and between {party_a} ("Company") and {party_b} ("Counterparty").<br/><br/>
            
            <b>1. DEFINITIONS</b><br/><br/>
            "Confidential Information" means any non-public information disclosed by either party, 
            including but not limited to trade secrets, business plans, customer data, and 
            technical specifications.<br/><br/>
            
            <b>2. TERM AND TERMINATION</b><br/><br/>
            This Agreement shall commence on the Effective Date and continue for a period of 
            {term} years, unless earlier terminated. Either party may terminate with {notice} days 
            written notice. Upon termination, all rights granted hereunder shall cease.<br/><br/>
            
            <b>3. LIMITATION OF LIABILITY</b><br/><br/>
            IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, 
            CONSEQUENTIAL, OR PUNITIVE DAMAGES. Total liability shall not exceed ${liability:,} 
            or the fees paid in the preceding {fee_period} months, whichever is greater.<br/><br/>
            
            <b>4. GOVERNING LAW</b><br/><br/>
            This Agreement shall be governed by and construed in accordance with the laws of the 
            State of {state}, without regard to conflict of law principles.
            """,
        ],
    },
    "research": {
        "filenames": [
            "Market_Analysis_Report_{industry}.pdf",
            "Competitive_Landscape_2024.pdf",
            "Customer_Survey_Results_Q{quarter}.pdf",
            "Industry_Trends_Forecast.pdf",
            "Product_Feasibility_Study.pdf",
            "User_Experience_Research.pdf",
            "Technology_Assessment_{tech}.pdf",
            "Emerging_Markets_Analysis.pdf",
            "Consumer_Behavior_Study.pdf",
            "Benchmarking_Report_2024.pdf",
            "Innovation_Pipeline_Review.pdf",
            "Patent_Landscape_Analysis.pdf",
            "Sustainability_Report_2024.pdf",
            "Digital_Transformation_Study.pdf",
            "AI_Implementation_Roadmap.pdf",
        ],
        "content_templates": [
            """
            <b>Research Summary</b><br/><br/>
            This study examines {topic} in the {industry} sector. Data was collected from 
            {sample_size:,} respondents across {regions} geographic regions between 
            {start_date} and {end_date}.<br/><br/>
            
            <b>Key Findings</b><br/><br/>
            • {finding_pct}% of respondents indicated preference for {preference}<br/>
            • Market size is projected to reach ${market_size:,} billion by 2027<br/>
            • Growth rate of {cagr}% CAGR expected over the next 5 years<br/>
            • Primary barriers to adoption include {barrier1} and {barrier2}<br/><br/>
            
            <b>Methodology</b><br/><br/>
            The research employed a mixed-methods approach combining quantitative surveys and 
            qualitative interviews. Statistical analysis was performed using {stat_method} with 
            a confidence level of {confidence}%. The margin of error is +/- {margin}%.<br/><br/>
            
            <b>Competitive Analysis</b><br/><br/>
            The market is dominated by {top_players} leading players who collectively hold 
            {market_share}% market share. Key differentiators include {differentiator1}, 
            {differentiator2}, and {differentiator3}.<br/><br/>
            
            <b>Recommendations</b><br/><br/>
            Based on the findings, we recommend: (1) prioritizing investment in {rec1}, 
            (2) developing strategic partnerships with {rec2}, and (3) accelerating {rec3} 
            initiatives to capture emerging opportunities.
            """,
        ],
    },
}

# Random data generators
def random_money(min_val: int, max_val: int) -> int:
    return random.randint(min_val, max_val) * 1000

def random_percent(min_val: int, max_val: int) -> float:
    return round(random.uniform(min_val, max_val), 1)

def fill_financial_template(template: str) -> str:
    months = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]
    segments = ["Enterprise", "SMB", "Consumer", "Government", "Healthcare"]
    regions = ["North America", "EMEA", "APAC", "Latin America"]
    
    return template.format(
        period=random.choice(months) + " 2024",
        revenue=random_money(5000, 50000),
        growth=random_percent(3, 25),
        expenses=random_money(2000, 30000),
        margin=random_percent(8, 35),
        savings=random_percent(5, 20),
        cash=random_money(10000, 100000),
        ar_days=random.randint(25, 60),
        segment=random.choice(segments),
        segment_pct=random.randint(20, 45),
        region=random.choice(regions),
        new_customers=random.randint(10, 50),
        retention=random_percent(85, 98),
        projected=random_money(6000, 60000),
    )

def fill_technical_template(template: str) -> str:
    systems = ["OrderManagement", "CustomerPortal", "Analytics", "DataPipeline", "AuthService"]
    frameworks = ["Spring Boot", "FastAPI", "Express.js", "Django", "Go Fiber"]
    databases = ["PostgreSQL", "MongoDB", "MySQL", "DynamoDB"]
    queues = ["RabbitMQ", "Apache Kafka", "AWS SQS", "Redis Streams"]
    compute = ["EKS", "ECS", "Lambda", "EC2 Auto Scaling"]
    
    return template.format(
        system_name=random.choice(systems),
        throughput=random.randint(5000, 100000),
        framework=random.choice(frameworks),
        compute=random.choice(compute),
        database=random.choice(databases),
        replicas=random.randint(2, 5),
        queue=random.choice(queues),
        rate_limit=random.randint(100, 1000),
        users=random.randint(10000, 500000),
        shard_key="customer_id",
        shards=random.randint(4, 16),
    )

def fill_hr_template(template: str) -> str:
    policies = ["Remote Work", "Leave", "Benefits", "Performance Review", "Travel Expense"]
    employee_types = ["full-time", "exempt", "salaried"]
    
    return template.format(
        policy_name=random.choice(policies),
        effective_date="January 1, 2024",
        employee_type=random.choice(employee_types),
        probation_period=random.choice([30, 60, 90]),
        days=random.randint(15, 30),
        match=random.choice([3, 4, 5, 6]),
        dev_budget=random.randint(1000, 5000),
        training_days=random.choice([30, 60, 90]),
        compliance_date="December 31st",
        ext=random.randint(1000, 9999),
    )

def fill_legal_template(template: str) -> str:
    agreement_types = ["Master Service", "Software License", "Data Processing", "Non-Disclosure"]
    companies = ["Acme Corporation", "TechVentures Inc.", "Global Solutions Ltd.", "Innovation Partners"]
    states = ["Delaware", "California", "New York", "Texas"]
    
    return template.format(
        agreement_type=random.choice(agreement_types),
        effective_date="January 15, 2024",
        party_a=random.choice(companies),
        party_b=random.choice([c for c in companies if c != companies[0]]),
        term=random.choice([1, 2, 3, 5]),
        notice=random.choice([30, 60, 90]),
        liability=random_money(100, 1000),
        fee_period=12,
        state=random.choice(states),
    )

def fill_research_template(template: str) -> str:
    industries = ["Technology", "Healthcare", "Financial Services", "Retail", "Manufacturing"]
    topics = ["digital adoption", "customer preferences", "market dynamics", "technology trends"]
    barriers = ["cost concerns", "lack of expertise", "regulatory uncertainty", "legacy systems"]
    stat_methods = ["regression analysis", "ANOVA", "chi-square testing", "factor analysis"]
    
    return template.format(
        topic=random.choice(topics),
        industry=random.choice(industries),
        sample_size=random.randint(500, 5000),
        regions=random.randint(3, 12),
        start_date="Q1 2024",
        end_date="Q3 2024",
        finding_pct=random.randint(45, 85),
        preference="digital-first solutions",
        market_size=random.randint(50, 500),
        cagr=random_percent(8, 25),
        barrier1=random.choice(barriers),
        barrier2=random.choice([b for b in barriers if b != barriers[0]]),
        stat_method=random.choice(stat_methods),
        confidence=random.choice([90, 95, 99]),
        margin=random_percent(2, 5),
        top_players=random.randint(3, 7),
        market_share=random.randint(55, 80),
        differentiator1="pricing strategy",
        differentiator2="product innovation",
        differentiator3="customer service",
        rec1="core technology infrastructure",
        rec2="key industry players",
        rec3="go-to-market",
    )

TEMPLATE_FILLERS = {
    "financial": fill_financial_template,
    "technical": fill_technical_template,
    "hr": fill_hr_template,
    "legal": fill_legal_template,
    "research": fill_research_template,
}

def generate_filename(category: str, index: int) -> str:
    """Generate a unique filename from the category templates."""
    templates = CATEGORIES[category]["filenames"]
    template = templates[index % len(templates)]
    
    # Fill in template variables with index-based values for uniqueness
    base_name = template.format(
        quarter=(index % 4) + 1,
        year=2023 + (index % 2),
        month=["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][index % 12],
        version=f"{(index % 5) + 1}.{index % 10}",
        date=f"2024{(index % 12) + 1:02d}",
        industry=["Tech", "Healthcare", "Finance", "Retail"][index % 4],
        tech=["AI", "Cloud", "Blockchain", "IoT"][index % 4],
    )
    # Add suffix for uniqueness within same template
    if index >= len(templates):
        suffix = f"_{index // len(templates) + 1}"
        base_name = base_name.replace(".pdf", f"{suffix}.pdf")
    return base_name

def create_pdf(filepath: Path, content: str, title: str) -> None:
    """Create a PDF with the given content."""
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
    )
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
    )
    
    story = []
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph(content, body_style))
    
    doc.build(story)

def main():
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating 100 PDFs in {OUTPUT_DIR}...")
    
    # Generate 20 PDFs per category (5 categories × 20 = 100)
    pdf_count = 0
    
    for category in CATEGORIES:
        for i in range(20):
            # Generate unique filename (now deterministic based on index)
            filename = generate_filename(category, i)
            filepath = OUTPUT_DIR / filename
            
            # Get content template and fill it
            template = random.choice(CATEGORIES[category]["content_templates"])
            filler = TEMPLATE_FILLERS[category]
            content = filler(template)
            
            # Create the PDF
            title = filename.replace("_", " ").replace(".pdf", "")
            create_pdf(filepath, content, title)
            
            pdf_count += 1
            print(f"  [{pdf_count}/100] Created: {filename}")
    
    print(f"\n✓ Successfully generated {pdf_count} PDFs in: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
