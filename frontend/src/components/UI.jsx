import { Check, X, Search } from "./Icons";
import { useLanguage } from "../contexts/LanguageContext";

export function Card({ children, className="", ...props }) {
  return <div className={`card ${className}`} {...props}>{children}</div>;
}

export function Badge({ children, tone="default" }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function ProgressBar({ value, showValue=false }) {
  return <div className="progress-wrap">
    <div className="progress-track"><div className="progress-fill" style={{width:`${value}%`}} /></div>
    {showValue && <span className="progress-value">{value}%</span>}
  </div>;
}

export function Button({ children, variant="primary", icon, ...props }) {
  return <button className={`btn btn-${variant}`} {...props}>{icon}{children}</button>;
}

export function SectionHeader({ title, subtitle, action }) {
  return <div className="section-header">
    <div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>
    {action}
  </div>;
}

export function EmptyState({ title, description, action }) {
  return <div className="empty-state"><div className="empty-icon">✦</div><h3>{title}</h3><p>{description}</p>{action}</div>;
}

export function Modal({ open, title, onClose, children, width="560px" }) {
  if (!open) return null;
  return <div className="modal-backdrop" onMouseDown={onClose}>
    <div className="modal" style={{maxWidth: width}} onMouseDown={e=>e.stopPropagation()}>
      <div className="modal-header"><h3>{title}</h3><button className="icon-btn" onClick={onClose}><X size={18}/></button></div>
      <div className="modal-body">{children}</div>
    </div>
  </div>;
}

export function Toast({ message, onClose }) {
  if (!message) return null;
  return <div className="toast"><span>{message}</span><button onClick={onClose}><Check size={16}/></button></div>;
}

export function StatCard({ label, value, change, icon: Icon, tone="" }) {
  return <Card className="stat-card">
    <div className={`stat-icon ${tone}`}><Icon size={20}/></div>
    <div className="stat-copy"><span>{label}</span><strong>{value}</strong>{change && <small>{change}</small>}</div>
  </Card>;
}

export function SearchInput({ value, onChange, placeholder }) {
  const { t } = useLanguage();
  return <div className="search-input"><Search size={17}/><input value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder ?? t("search_placeholder")}/></div>;
}