import { createElement } from '../utils/helpers';

export const renderModal = (title: string, content: string, onConfirm: () => void) => {
  const overlay = createElement('div', 'modal-overlay');
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  `;

  const modal = createElement('div', 'card glass');
  modal.style.cssText = `
    width: 90%;
    max-width: 500px;
    padding: 2rem;
    position: relative;
    animation: modalAppear 0.3s ease;
  `;

  modal.innerHTML = `
    <h2 style="margin-bottom: 1.5rem; font-size: 1.3rem;">${title}</h2>
    <div id="modal-body">${content}</div>
    <div style="display: flex; justify-content: flex-end; gap: 1rem; margin-top: 2rem;">
      <button id="modal-cancel" style="padding: 0.6rem 1.2rem; background: var(--surface-light); color: var(--text);">Bekor qilish</button>
      <button id="modal-confirm" class="btn-primary" style="padding: 0.6rem 1.2rem;">Saqlash</button>
    </div>
  `;

  overlay.appendChild(modal);
  document.body.appendChild(overlay);

  const style = document.createElement('style');
  style.innerHTML = `
    @keyframes modalAppear {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `;
  document.head.appendChild(style);

  overlay.querySelector('#modal-cancel')?.addEventListener('click', () => overlay.remove());
  overlay.querySelector('#modal-confirm')?.addEventListener('click', () => {
    onConfirm();
    overlay.remove();
  });

  return overlay;
};
