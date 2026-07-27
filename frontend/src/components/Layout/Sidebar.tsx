import { NavLink } from 'react-router-dom';
import {
  BarChart3,
  LayoutDashboard,
  TrendingUp,
  Activity,
  Newspaper,
  Menu,
  X,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: '市场数据看板', exact: true },
  { to: '/backtest', icon: BarChart3, label: '量化回测' },
  { to: '/stock-analysis', icon: TrendingUp, label: '个股分析' },
  { to: '/news', icon: Newspaper, label: '新闻推送' },
];

interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  onNavClick?: () => void;
}

export default function Sidebar({ isOpen, onToggle, onNavClick }: SidebarProps) {
  return (
    <>
      {/* 移动端遮罩 */}
      {isOpen && (
        <div
          className="sidebar-overlay"
          onClick={onToggle}
          style={{
            display: 'none',
          }}
        />
      )}

      {/* 移动端汉堡按钮 */}
      <button
        className="mobile-menu-btn"
        onClick={onToggle}
        style={{
          display: 'none',
          position: 'fixed',
          top: 12,
          left: 12,
          zIndex: 1001,
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: 6,
          padding: 8,
          cursor: 'pointer',
          color: 'var(--text-primary)',
        }}
      >
        {isOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      <aside
        className={`sidebar${isOpen ? ' open' : ''}`}
        style={{
          width: 220,
          minWidth: 220,
          background: 'var(--bg-secondary)',
          borderRight: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          height: '100vh',
          zIndex: 1000,
        }}
      >
        {/* Logo */}
        <div
          style={{
            padding: '20px 16px',
            borderBottom: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              background: 'linear-gradient(135deg, #1a6b5a, #26a69a)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Activity size={18} color="white" />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2 }}>
              交易看板
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', letterSpacing: 1 }}>
              TRADING DASHBOARD
            </div>
          </div>
        </div>

        {/* 导航 */}
        <nav style={{ flex: 1, padding: '12px 8px' }}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.exact}
              onClick={onNavClick}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '10px 12px',
                borderRadius: 6,
                marginBottom: 2,
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                background: isActive ? 'var(--bg-tertiary)' : 'transparent',
                textDecoration: 'none',
                transition: 'all 0.15s',
                borderLeft: isActive ? '2px solid var(--accent-green)' : '2px solid transparent',
              })}
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* 底部 */}
        <div
          style={{
            padding: '12px 16px',
            borderTop: '1px solid var(--border-color)',
            fontSize: 11,
            color: 'var(--text-muted)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: 'var(--accent-green)',
              }}
            />
            系统运行中
          </div>
          <div style={{ marginTop: 4 }}>v1.0.0</div>
        </div>
      </aside>
    </>
  );
}