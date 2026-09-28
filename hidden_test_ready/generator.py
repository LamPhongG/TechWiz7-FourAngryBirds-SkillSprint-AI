# Generates an unseen corporate policy PDF for automated Hidden Test verification.

from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    import fitz



def create_unseen_policy_pdf(output_path: Path) -> Path:
    """Create a realistic unseen corporate security & remote work policy PDF."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    # Page 1: Remote Work Infrastructure
    page1 = doc.new_page()
    text_p1 = (
        "SKILLSPRINT GLOBAL — REMOTE WORK & DATA PROTECTION POLICY 2026\n\n"
        "SECTION 1: REMOTE WORK INFRASTRUCTURE AND ACCESS\n"
        "1.1 Virtual Private Network Requirements:\n"
        "All remote employees must connect to the corporate WireGuard VPN before accessing "
        "internal cloud infrastructure, staging environments, or production databases. "
        "Split-tunneling is strictly disabled to prevent data leakage across insecure networks.\n\n"
        "1.2 Full Disk Encryption:\n"
        "Laptops and workstations used for company business must maintain 256-bit AES disk encryption. "
        "Recovery keys must be escrowed in the corporate key vault during initial device setup.\n\n"
        "1.3 Session Timeout Policy:\n"
        "Remote desktop and cloud console sessions automatically terminate after 15 minutes of inactivity."
    )
    rect = fitz.Rect(50, 50, 550, 780)
    page1.insert_textbox(rect, text_p1, fontsize=11)

    # Page 2: Incident Response & Data Handling
    page2 = doc.new_page()
    text_p2 = (
        "SECTION 2: SECURITY INCIDENT RESPONSE PROTOCOL\n\n"
        "2.1 Immediate Incident Notification:\n"
        "Employees must notify the Security Operations Center at security@skillsprint.io within "
        "2 hours of detecting any unauthorized access, phishing compromise, or lost device.\n\n"
        "2.2 Data Classification and Export:\n"
        "Customer personally identifiable information (PII) must never be stored on local drives. "
        "All export operations require explicit written authorization from the Data Protection Officer."
    )
    page2.insert_textbox(rect, text_p2, fontsize=11)

    doc.save(str(output_path))
    doc.close()
    return output_path


if __name__ == "__main__":
    target = Path(__file__).parent / "sample_unseen_policy.pdf"
    create_unseen_policy_pdf(target)
    print(f"Created unseen policy at: {target}")
