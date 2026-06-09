import { store } from '../data/store';
import { renderSidebar } from '../components/sidebar';
import { formatCurrency, createElement } from '../utils/helpers';
import { renderModal } from '../components/modal';

export const renderSklad = () => {
  const app = document.getElementById('app')!;
  app.innerHTML = '';
  
  const sidebar = renderSidebar();
  const mainContent = createElement('main', 'main-content');

  const renderTable = () => {
    return `
      <table style="width: 100%; border-collapse: collapse;">
        <thead>
          <tr style="text-align: left; border-bottom: 1px solid var(--border);">
            <th style="padding: 1rem; color: var(--text-muted);">Nomi</th>
            <th style="padding: 1rem; color: var(--text-muted);">Modeli</th>
            <th style="padding: 1rem; color: var(--text-muted);">Narxi</th>
            <th style="padding: 1rem; color: var(--text-muted);">Soni</th>
            <th style="padding: 1rem; color: var(--text-muted);">Holat</th>
            <th style="padding: 1rem; color: var(--text-muted);">Amallar</th>
          </tr>
        </thead>
        <tbody>
          ${store.mebellar.map(m => `
            <tr style="border-bottom: 1px solid var(--border);">
              <td style="padding: 1rem; font-weight: 500;">${m.nomi}</td>
              <td style="padding: 1rem;">${m.modeli}</td>
              <td style="padding: 1rem;">${formatCurrency(m.narxi, m.valyuta)}</td>
              <td style="padding: 1rem;">${m.soni} dona</td>
              <td style="padding: 1rem;">
                <span class="status-badge ${m.status === 'sotuvda' ? 'status-instock' : (m.status === 'kam_qoldi' ? 'status-low' : 'status-outofstock')}">
                  ${m.status === 'sotuvda' ? 'Sotuvda' : (m.status === 'kam_qoldi' ? 'Kam qoldi' : 'Tugagan')}
                </span>
              </td>
              <td style="padding: 1rem;">
                <button class="edit-btn" data-id="${m.id}" style="background: transparent; color: var(--primary); padding: 0.4rem;"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg></button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  };

  mainContent.innerHTML = `
    <header style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
      <div>
        <h1 style="font-size: 1.8rem; margin-bottom: 0.5rem;">Sklad Boshqaruvi</h1>
        <p style="color: var(--text-muted);">Mahsulotlar qoldig'ini boshqarish va tahrirlash</p>
      </div>
      <button id="add-mebel-btn" class="btn-primary">+ Yangi Mahsulot</button>
    </header>

    <div class="card glass" style="overflow-x: auto;">
      <div id="sklad-table-container">
        ${renderTable()}
      </div>
    </div>
  `;

  app.appendChild(sidebar);
  app.appendChild(mainContent);

  // Add Mebel Event
  document.getElementById('add-mebel-btn')?.addEventListener('click', () => {
    const formHtml = `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Nomi</label>
          <input type="text" id="m-nomi" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Modeli</label>
          <input type="text" id="m-modeli" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div style="display: flex; gap: 1rem;">
          <div style="flex: 2;">
            <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Narxi</label>
            <input type="number" id="m-narxi" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
          </div>
          <div style="flex: 1;">
            <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Valyuta</label>
            <select id="m-valyuta" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
              <option value="USD">USD</option>
              <option value="UZS">UZS</option>
            </select>
          </div>
        </div>
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Soni</label>
          <input type="number" id="m-soni" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
      </div>
    `;

    renderModal('Yangi Mahsulot Qo\'shish', formHtml, () => {
      const nomi = (document.getElementById('m-nomi') as HTMLInputElement).value;
      const modeli = (document.getElementById('m-modeli') as HTMLInputElement).value;
      const narxi = Number((document.getElementById('m-narxi') as HTMLInputElement).value);
      const valyuta = (document.getElementById('m-valyuta') as HTMLSelectElement).value as 'USD' | 'UZS';
      const soni = Number((document.getElementById('m-soni') as HTMLInputElement).value);

      if (nomi && modeli) {
        store.addMebel({
          nomi, modeli, narxi, valyuta, soni,
          status: soni <= 0 ? 'tugagan' : (soni <= 3 ? 'kam_qoldi' : 'sotuvda')
        });
        renderSklad(); // Re-render
      }
    });
  });

  // Edit Event
  mainContent.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    const btn = target.closest('.edit-btn') as HTMLButtonElement;
    if (btn) {
      const id = btn.dataset.id!;
      const mebel = store.mebellar.find(m => m.id === id)!;

      const editHtml = `
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div><label>Soni (Yangilash)</label>
          <input type="number" id="edit-soni" value="${mebel.soni}" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);"></div>
        </div>
      `;

      renderModal(`${mebel.nomi} - Qoldiqni yangilash`, editHtml, () => {
        const yangiSoni = Number((document.getElementById('edit-soni') as HTMLInputElement).value);
        store.updateMebel(id, { 
          soni: yangiSoni,
          status: yangiSoni <= 0 ? 'tugagan' : (yangiSoni <= 3 ? 'kam_qoldi' : 'sotuvda')
        });
        renderSklad();
      });
    }
  });
};
