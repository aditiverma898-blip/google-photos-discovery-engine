import { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

const primary = [
  { to: '/', label: 'Overview', icon: 'overview', description: 'What we learned' },
  { to: '/analytics', label: 'Patterns', icon: 'analytics', description: 'Compare the findings' },
  { to: '/evidence', label: 'Evidence', icon: 'evidence', description: 'Inspect the records' },
  { to: '/copilot', label: 'Research tools', icon: 'copilot', description: 'Ask and classify' },
];

function NavIcon({ name }) {
  const paths = {
    overview: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
    analytics: <><path d="M4 20V11" /><path d="M10 20V6" /><path d="M16 20v-8" /><path d="M22 20V4" /><path d="M2 20h21" /></>,
    evidence: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 5 5" /></>,
    copilot: <><path d="M4 4h16v12H9l-5 4V4Z" /><path d="M8 8h8m-8 4h5" /></>,
    methodology: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>,
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

export default function Shell({ children }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  return <div className="app-shell">
    <a href="#main-content" className="skip-link">Skip to content</a>
    <button className="mobile-menu-button" type="button" aria-label={open ? 'Close navigation' : 'Open navigation'} aria-expanded={open} onClick={() => setOpen(!open)}>
      <span aria-hidden="true">{open ? '×' : '☰'}</span><span>Discovery study · Google Photos</span>
    </button>
    {open && <button className="mobile-scrim" aria-label="Close navigation" onClick={() => setOpen(false)} />}
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <button className="sidebar-close" type="button" aria-label="Close navigation" onClick={() => setOpen(false)}>×</button>
      <div className="brand-lockup"><svg className="study-mark" width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true"><rect x="4" y="5" width="24" height="22" rx="7" stroke="currentColor" strokeWidth="2" /><path d="M10 22V11h12M22 10v12H10" stroke="currentColor" strokeWidth="2" /><circle cx="22" cy="10" r="3" fill="#34a853" /></svg><div><strong>Discovery study</strong><span className="brand-eyebrow">Google Photos</span></div></div>
      <nav aria-label="Main navigation" className="sidebar-nav">
        <span className="nav-heading">WORKSPACE</span>
        {primary.map(item => <NavLink key={item.to} to={item.to} end={item.to === '/'} onClick={() => setOpen(false)} className={({ isActive }) => `side-link ${isActive || (item.to === '/evidence' && location.pathname.startsWith('/evidence/')) || (item.to === '/analytics' && location.pathname.startsWith('/cluster/')) ? 'active' : ''}`}>
          <span className="nav-icon"><NavIcon name={item.icon} /></span><span><strong>{item.label}</strong><small>{item.description}</small></span>
        </NavLink>)}
      </nav>
      <div className="sidebar-bottom"><span className="nav-heading">REFERENCE</span><NavLink to="/methodology" onClick={() => setOpen(false)} className={({ isActive }) => `side-link ${isActive ? 'active' : ''}`}><span className="nav-icon"><NavIcon name="methodology" /></span><span><strong>Methodology</strong><small>Sources, scope & limits</small></span></NavLink><div className="sidebar-footnote">Independent course project.<br />Not affiliated with Google.</div></div>
    </aside>
    <main id="main-content" className="main-content" key={location.pathname}>{children}</main>
  </div>;
}
