import { Modal, Button } from "../UI";
import { Award, Download } from "../Icons";
import { useLanguage } from "../../contexts/LanguageContext";
import { useAuth } from "../../hooks/useAuth";
import { formatLocalDate } from "../../utils/helpers";
import "../../styles/certificate.css";

export default function CertificateModal({ path, employee, enrollment, onClose }) {
  const { t, pick, locale } = useLanguage();
  const { user } = useAuth();
  
  const currentEmp = employee || user || { name: "Employee" };
  const empName = currentEmp.name || "Employee";
  const empCode = currentEmp.employee_code || (currentEmp.id ? `EMP-${String(currentEmp.id).slice(0, 4)}` : "EMP-2026");
  const pathIdStr = typeof path === "object" ? path?.id : String(path || "PATH");
  const pathTitleStr = typeof path === "object" ? (pick ? pick(path, "title") : path?.title) : String(path || "Onboarding");
  const certId = `SSA-${empCode}-${pathIdStr.substring(0, 6).toUpperCase()}`;
  const todayStr = new Date().toISOString();
  const completionDate = (enrollment && (enrollment.completedAt || enrollment.completed_at)) || todayStr;
  
  const handlePrint = () => {
    const node = document.getElementById("certificate-node");
    if (!node) return;
    const content = node.innerHTML;
    
    // Create hidden iframe for direct printing, avoiding popup blocker issues
    let iframe = document.getElementById("certificate-print-frame");
    if (!iframe) {
      iframe = document.createElement("iframe");
      iframe.id = "certificate-print-frame";
      iframe.style.position = "fixed";
      iframe.style.right = "0";
      iframe.style.bottom = "0";
      iframe.style.width = "0";
      iframe.style.height = "0";
      iframe.style.border = "0";
      document.body.appendChild(iframe);
    }
    
    const doc = iframe.contentWindow.document;
    doc.open();
    doc.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <meta charset="utf-8" />
          <title>SkillSprint_Certificate_${empName.replace(/\\s+/g, '_')}</title>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Inter:wght@400;600;700;800&display=swap');
            @page { size: A4 landscape; margin: 8mm; }
            body { 
              font-family: 'Inter', sans-serif; 
              display: flex; 
              align-items: center; 
              justify-content: center; 
              min-height: 95vh; 
              margin: 0; 
              padding: 10px;
              background: #fff;
              -webkit-print-color-adjust: exact;
              print-color-adjust: exact;
            }
            .certificate-wrapper { max-width: 950px; width: 100%; font-family: "Playfair Display", serif; }
            .cert-border-outer { border: 10px solid #e2e8f0; padding: 10px; background: #f8fafc; }
            .cert-border-inner { border: 2px solid #cbd5e1; padding: 40px 30px; background: #fff; text-align: center; position: relative; }
            .cert-header { display: flex; align-items: center; justify-content: center; gap: 14px; margin-bottom: 25px; }
            .cert-logo { height: 50px; border-radius: 8px; }
            .cert-header h2 { font-size: 28px; color: #1e3a8a; margin: 0; font-family: 'Inter', sans-serif; font-weight: 800; letter-spacing: -1px; }
            .cert-subtitle { font-size: 14px; letter-spacing: 5px; color: #64748b; margin-bottom: 20px; text-transform: uppercase; font-family: 'Inter', sans-serif; font-weight: 700; }
            .cert-presented { font-size: 15px; color: #475569; margin-bottom: 5px; font-style: italic; }
            .cert-name { font-size: 42px; font-style: italic; margin: 10px 0; color: #0f172a; font-weight: 700; }
            .cert-text { font-size: 16px; color: #475569; font-style: italic; margin: 10px 0; }
            .cert-path-title { font-size: 24px; color: #1e3a8a; margin: 15px 0; font-weight: 700; font-family: 'Inter', sans-serif; }
            .cert-points { font-size: 14px; color: #334155; font-family: 'Inter', sans-serif; }
            .cert-footer { display: flex; justify-content: space-between; align-items: flex-end; margin-top: 40px; padding: 0 30px; }
            .sig-line { border-bottom: 1px solid #94a3b8; padding-bottom: 4px; font-size: 18px; font-style: italic; color: #0f172a; margin-bottom: 5px; width: 200px; text-align: center; }
            .cert-date .sig-line { font-family: 'Inter', sans-serif; font-style: normal; font-size: 15px; }
            .cert-footer span { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; font-family: 'Inter', sans-serif; font-weight: 600; }
            .cert-seal { width: 95px; height: 95px; border-radius: 50%; background: #fef08a; border: 3px dashed #ca8a04; display: grid; place-items: center; box-shadow: 0 4px 10px rgba(0,0,0,0.06); }
            .seal-inner { font-size: 12px; font-family: 'Inter', sans-serif; font-weight: 800; color: #854d0e; text-transform: uppercase; transform: rotate(-15deg); border-top: 2px solid #ca8a04; border-bottom: 2px solid #ca8a04; padding: 2px 0; letter-spacing: 2px; }
            .cert-meta { font-family: 'Inter', sans-serif; font-size: 11px; color: #94a3b8; margin-top: 30px; text-align: center; }
          </style>
        </head>
        <body>
          <div class="certificate-wrapper">${content}</div>
        </body>
      </html>
    `);
    doc.close();
    setTimeout(() => {
      iframe.contentWindow.focus();
      iframe.contentWindow.print();
    }, 300);
  };

  return (
    <Modal open title={t("certificate")} onClose={onClose} width={850}>
      <div id="certificate-node" className="certificate-wrapper">
        <div className="cert-border-outer">
          <div className="cert-border-inner">
            <div className="cert-header">
              <img src="/logonhomai.jpg" alt="Logo" className="cert-logo" />
              <h2>SkillSprint AI</h2>
            </div>
            
            <div className="cert-body">
              <div className="cert-subtitle">CERTIFICATE OF COMPLETION</div>
              <p className="cert-presented">This is to certify that</p>
              <h1 className="cert-name">{empName}</h1>
              <p className="cert-text">has successfully completed the training path</p>
              <h3 className="cert-path-title">{pathTitleStr}</h3>
              <p className="cert-points">Earning <strong>{path?.points || 100}</strong> Points with Excellent Grades</p>
            </div>
            
            <div className="cert-footer">
              <div className="cert-signature">
                <div className="sig-line" style={{ fontFamily: "cursive", fontSize: "28px", color: "#1e3a8a" }}>RajPham</div>
                <span>Authorized Signature</span>
              </div>
              <div className="cert-seal">
                <div className="seal-inner">CERTIFIED</div>
              </div>
              <div className="cert-date">
                <div className="sig-line">{formatLocalDate(completionDate, locale, { year: 'numeric', month: 'long', day: 'numeric' })}</div>
                <span>Date Completed</span>
              </div>
            </div>
            <div className="cert-meta">
              Verify at: skillsprint.fourangrybirds.vn/verify/{certId}
            </div>
          </div>
        </div>
      </div>
      <div className="modal-actions" style={{ marginTop: 25, justifyContent: "center", gap: 12 }}>
         <Button onClick={handlePrint} icon={<Download size={16} />}>
           {t("export_pdf_certificate") || "Export PDF / Print Certificate"}
         </Button>
         <Button variant="secondary" onClick={onClose}>{t("close")}</Button>
      </div>
    </Modal>
  );
}
