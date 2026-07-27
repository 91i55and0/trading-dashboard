import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        onNavClick={() => setSidebarOpen(false)}
      />
      <main
        className="main-content"
        style={{
          flex: 1,
          overflow: 'auto',
          padding: '24px',
          background: 'var(--bg-primary)',
        }}
      >
        <Outlet />
      </main>
    </div>
  );
}