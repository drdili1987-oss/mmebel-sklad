import { store, Buyurtma } from '../data/store';
import { renderSidebar } from '../components/sidebar';
import { formatCurrency, createElement, formatDate } from '../utils/helpers';
import { renderModal } from '../components/modal';
import { showToast } from '../components/toast';

export const renderBuyurtmalar = () => {
  const app = document.getElementById('app')!;
  app.innerHTML = '';
  
  const sidebar = renderSidebar();
  const mainContent = createElement('main', 'main-content');

  const renderOrderList = () => {
    if (store.buyurtmalar.length === 0) {
      return '<p style="color: var(--text-muted); text-align: center; padding: 2rem;">Hozircha buyurtmalar yo\'q.</p>';
    }

    return `
      <div style="display: grid; gap: 1rem;">
        ${store.buyurtmalar.slice().sort((a, b) => new Date(b.sana).getTime() - new Date(a.sana).getTime()).map(z => `
          <div class="card glass" style="display: flex; justify-content: space-between; align-items: center; padding: 1.2rem;">
            <div>
              <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
                <h3 style="font-size: 1.1rem;">${z.mijoz_ismi}</h3>
                <span class="status-badge" style="background: rgba(99, 102, 241, 0.1); color: #818cf8; font-size: 0.7rem;">${z.id}</span>
              </div>
              <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.3rem;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"></path></svg>
                ${z.mahsulot_nomi} (${z.miqdori} dona)
              </p>
              <p style="font-size: 0.9rem; color: var(--text-muted);">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                Muddati: <span style="font-weight: 600; color: var(--accent);">${formatDate(z.tayyor_sana)}</span>
              </p>
            </div>
            <div style="text-align: right;">
              <p style="font-weight: 700; margin-bottom: 0.8rem;">
                ${z.chegirma ? `<span style="text-decoration: line-through; color: var(--text-muted); font-size: 0.85rem; margin-right: 0.4rem;">$${z.jami_narx}</span><span style="color: #7c3aed;">$${z.jami_narx - z.chegirma}</span>` : formatCurrency(z.jami_narx, 'USD')}
              </p>
              <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: flex-end;">
                <button class="status-btn ${z.status === 'tayyorlanmoqda' ? 'active' : ''}" data-id="${z.id}" data-status="tayyorlanmoqda" style="padding: 0.4rem 0.8rem; font-size: 0.75rem; background: ${z.status === 'tayyorlanmoqda' ? 'var(--warning)' : 'var(--surface-light)'};">Tayyorlanmoqda</button>
                <button class="status-btn ${z.status === 'tayyor' ? 'active' : ''}" data-id="${z.id}" data-status="tayyor" style="padding: 0.4rem 0.8rem; font-size: 0.75rem; background: ${z.status === 'tayyor' ? 'var(--success)' : 'var(--surface-light)'};">Tayyor</button>
                <button class="status-btn ${z.status === 'yetkazildi' ? 'active' : ''}" data-id="${z.id}" data-status="yetkazildi" style="padding: 0.4rem 0.8rem; font-size: 0.75rem; background: ${z.status === 'yetkazildi' ? 'var(--primary)' : 'var(--surface-light)'};">Yetkazildi</button>
                <button class="olib-ketdi-btn" data-id="${z.id}" style="padding: 0.4rem 0.8rem; font-size: 0.75rem; border-radius: var(--radius); border: none; cursor: pointer; font-weight: 600; background: ${z.ozi_olib_ketdi ? '#7c3aed' : 'var(--surface-light)'}; color: ${z.ozi_olib_ketdi ? '#fff' : 'var(--text)'}; transition: all 0.2s;">🚗 Mijoz ozi olib ketdi</button>
              </div>
              ${z.ozi_olib_ketdi ? `
              <div style="display: flex; gap: 0.5rem; margin-top: 0.6rem; justify-content: flex-end; align-items: center;">
                <span style="font-size: 0.75rem; color: var(--text-muted);">Chegirma:</span>
                <button class="chegirma-btn" data-id="${z.id}" data-chegirma="6" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; font-weight: 700; border-radius: var(--radius); border: 2px solid ${z.chegirma === 6 ? '#7c3aed' : 'var(--border)'}; cursor: pointer; background: ${z.chegirma === 6 ? '#7c3aed' : 'transparent'}; color: ${z.chegirma === 6 ? '#fff' : 'var(--text)'}; transition: all 0.2s;">$6</button>
                <button class="chegirma-btn" data-id="${z.id}" data-chegirma="8" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; font-weight: 700; border-radius: var(--radius); border: 2px solid ${z.chegirma === 8 ? '#7c3aed' : 'var(--border)'}; cursor: pointer; background: ${z.chegirma === 8 ? '#7c3aed' : 'transparent'}; color: ${z.chegirma === 8 ? '#fff' : 'var(--text)'}; transition: all 0.2s;">$8</button>
                <button class="chegirma-btn" data-id="${z.id}" data-chegirma="10" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; font-weight: 700; border-radius: var(--radius); border: 2px solid ${z.chegirma === 10 ? '#7c3aed' : 'var(--border)'}; cursor: pointer; background: ${z.chegirma === 10 ? '#7c3aed' : 'transparent'}; color: ${z.chegirma === 10 ? '#fff' : 'var(--text)'}; transition: all 0.2s;">$10</button>
                ${z.chegirma ? `<span style="font-size: 0.8rem; color: #7c3aed; font-weight: 700; margin-left: 0.3rem;">-$${z.chegirma} chegirma</span>` : ''}
              </div>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
    `;
  };

  mainContent.innerHTML = `
    <header style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
      <div>
        <h1 style="font-size: 1.8rem; margin-bottom: 0.5rem;">Buyurtmalar</h1>
        <p style="color: var(--text-muted);">Mijozlardan olingan zakazlar va ularning nazorati</p>
      </div>
      <button id="add-zakaz-btn" class="btn-primary">+ Yangi Buyurtma</button>
    </header>

    <div id="buyurtmalar-list-container">
      ${renderOrderList()}
    </div>
  `;

  app.appendChild(sidebar);
  app.appendChild(mainContent);

  // Click event listener (status + olib ketdi + chegirma)
  mainContent.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;

    // Status tugmalari
    if (target.classList.contains('status-btn')) {
      const id = target.dataset.id!;
      const status = target.dataset.status as Buyurtma['status'];
      const order = store.buyurtmalar.find(z => z.id === id);
      if (order) {
        order.status = status;
        localStorage.setItem('mmebel_buyurtmalar', JSON.stringify(store.buyurtmalar));
        showToast(`Buyurtma holati "${status}"ga o'zgartirildi`);
        renderBuyurtmalar();
      }
      return;
    }

    // 🚗 Mijoz ozi olib ketdi tugmasi
    if (target.classList.contains('olib-ketdi-btn')) {
      const id = target.dataset.id!;
      const order = store.buyurtmalar.find(z => z.id === id);
      if (order) {
        order.ozi_olib_ketdi = !order.ozi_olib_ketdi;
        if (!order.ozi_olib_ketdi) {
          order.chegirma = undefined;
        }
        localStorage.setItem('mmebel_buyurtmalar', JSON.stringify(store.buyurtmalar));
        showToast(order.ozi_olib_ketdi ? '🚗 Mijoz ozi olib ketdi! Chegirma tanlang.' : 'Bekor qilindi');
        renderBuyurtmalar();
      }
      return;
    }

    // 💰 Chegirma tugmalari ($6, $8, $10)
    if (target.classList.contains('chegirma-btn')) {
      const id = target.dataset.id!;
      const chegirma = Number(target.dataset.chegirma);
      const order = store.buyurtmalar.find(z => z.id === id);
      if (order) {
        if (order.chegirma === chegirma) {
          order.chegirma = undefined;
          showToast('Chegirma bekor qilindi');
        } else {
          order.chegirma = chegirma;
          showToast(`✅ $${chegirma} chegirma qo'llanildi!`);
        }
        localStorage.setItem('mmebel_buyurtmalar', JSON.stringify(store.buyurtmalar));
        renderBuyurtmalar();
      }
      return;
    }
  });

  // Add Order logic
  document.getElementById('add-zakaz-btn')?.addEventListener('click', () => {
    const products = store.mebellar.filter(m => m.soni > 0);
    
    if (products.length === 0) {
      showToast('Skladda mahsulot yo\'q!', 'error');
      return;
    }

    const formHtml = `
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Mijoz Ismi</label>
          <input type="text" id="z-mijoz" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Telefon Raqami</label>
          <input type="text" id="z-tel" value="+998 " style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Mahsulot Tanlash</label>
          <select id="z-mahsulot" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
            ${products.map(p => `<option value="${p.id}">${p.nomi} (${p.soni} dona bor)</option>`).join('')}
          </select>
        </div>
        <div style="display: flex; gap: 1rem;">
          <div style="flex: 1;">
            <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Soni</label>
            <input type="number" id="z-soni" value="1" min="1" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
          </div>
          <div style="flex: 1;">
            <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Tayyor bo'lish muddati</label>
            <input type="date" id="z-sana" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
          </div>
        </div>
      </div>
    `;

    renderModal('Yangi Buyurtma Qo\'shish', formHtml, () => {
      const mijoz_ismi = (document.getElementById('z-mijoz') as HTMLInputElement).value;
      const mijoz_telefon = (document.getElementById('z-tel') as HTMLInputElement).value;
      const mahsulot_id = (document.getElementById('z-mahsulot') as HTMLSelectElement).value;
      const miqdori = Number((document.getElementById('z-soni') as HTMLInputElement).value);
      const tayyor_sana = (document.getElementById('z-sana') as HTMLInputElement).value;

      const product = store.mebellar.find(m => m.id === mahsulot_id)!;

      if (mijoz_ismi && tayyor_sana && miqdori > 0) {
        if (miqdori > product.soni) {
          showToast(`Skladda faqat ${product.soni} dona bor!`, 'error');
          return;
        }

        store.addBuyurtma({
          mijoz_ismi,
          mijoz_telefon,
          mahsulot_id,
          mahsulot_nomi: product.nomi,
          miqdori,
          jami_narx: product.narxi * miqdori,
          tayyor_sana,
          status: 'tayyorlanmoqda'
        });

        showToast('Buyurtma muvaffaqiyatli qo\'shildi!');
        renderBuyurtmalar();
      } else {
        showToast('Iltimos, barcha maydonlarni to\'ldiring', 'error');
      }
    });
  });
};
