import { createElement } from '../utils/helpers';

export const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
  const toast = createElement('div', 'toast glass');
  const bg = type === 'success' ? 'var(--success)' : (type === 'error' ? 'var(--danger)' : 'var(--primary)');
  
  toast.style.cssText = `
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    padding: 1rem 2rem;
    background: ${bg};
    color: white;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    z-index: 2000;
    transition: all 0.3s ease;
    transform: translateY(100px);
    opacity: 0;
  `;
  
  toast.innerText = message;
  document.body.appendChild(toast);

  // Animate in
  setTimeout(() => {
    toast.style.transform = 'translateY(0)';
    toast.style.opacity = '1';
  }, 10);

  // Remove
  setTimeout(() => {
    toast.style.transform = 'translateY(100px)';
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
};
