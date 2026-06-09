import { router, Route } from '../router';
import { store } from '../data/store';

export const renderSidebar = () => {
  const sidebar = document.createElement('aside');
  sidebar.className = 'glass';
  sidebar.style.cssText = `
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: var(--sidebar-width);
    padding: 2rem 1.5rem;
    display: flex;
    flex-direction: column;
    z-index: 100;
  `;

  const navItems: { label: string; route: Route; icon: string }[] = [
    { label: 'Asosiy', route: '/dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
    { label: 'Sklad', route: '/sklad', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
    { label: 'Buyurtmalar', route: '/buyurtmalar', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 0h6' },
    { label: 'Statistika', route: '/statistika', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
  ];

  const currentPath = window.location.hash.slice(1) || '/dashboard';

  sidebar.innerHTML = `
    <div style="margin-bottom: 3rem;">
      <h2 style="font-size: 1.5rem; color: var(--primary); font-weight: 700;">MMEBEL</h2>
    </div>
    
    <nav style="flex: 1;">
      <ul style="display: flex; flex-direction: column; gap: 0.5rem;">
        ${navItems.map(item => `
          <li>
            <a href="#${item.route}" class="nav-link ${currentPath === item.route ? 'active' : ''}" style="
              display: flex;
              align-items: center;
              gap: 1rem;
              padding: 0.8rem 1rem;
              border-radius: var(--radius);
              color: ${currentPath === item.route ? 'white' : 'var(--text-muted)'};
              background: ${currentPath === item.route ? 'var(--primary)' : 'transparent'};
              transition: all 0.2s ease;
            ">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="${item.icon}"></path>
              </svg>
              <span>${item.label}</span>
            </a>
          </li>
        `).join('')}
      </ul>
    </nav>
    
    <button id="logout-btn" style="
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.8rem 1rem;
      border-radius: var(--radius);
      color: var(--danger);
      background: transparent;
      margin-top: auto;
      width: 100%;
      text-align: left;
    ">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
      </svg>
      <span>Chiqish</span>
    </button>
  `;

  sidebar.querySelector('#logout-btn')?.addEventListener('click', () => {
    store.logout();
    router.navigate('/login');
  });

  return sidebar;
};
