import{s as r}from"./index-DakUwRTP.js";import{r as c,c as p,f as u}from"./helpers-BSqnvA6D.js";const v=()=>{const a=document.getElementById("app");a.innerHTML="";const n=c(),i=p("main","main-content"),d=r.mebellar.filter(e=>e.soni<=3&&e.soni>0).length,m=r.mebellar.filter(e=>e.soni===0).length;i.innerHTML=`
    <header style="margin-bottom: 2rem;">
      <h1 style="font-size: 1.8rem; margin-bottom: 0.5rem;">Xush kelibsiz!</h1>
      <p style="color: var(--text-muted);">Sklad va buyurtmalar holati bilan tanishing</p>
    </header>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem; margin-bottom: 2.5rem;">
      <div class="card glass">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Jami Mebellar</p>
        <h3 style="font-size: 2rem; margin-top: 0.5rem;">${r.mebellar.length} <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: normal;">turda</span></h3>
      </div>
      <div class="card glass" style="border-left: 4px solid var(--warning);">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Kam qolganlar</p>
        <h3 style="font-size: 2rem; margin-top: 0.5rem; color: var(--warning);">${d}</h3>
      </div>
      <div class="card glass" style="border-left: 4px solid var(--danger);">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Tugaganlar</p>
        <h3 style="font-size: 2rem; margin-top: 0.5rem; color: var(--danger);">${m}</h3>
      </div>
      <div class="card glass" style="border-left: 4px solid var(--success);">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Jami Buyurtmalar</p>
        <h3 style="font-size: 2rem; margin-top: 0.5rem; color: var(--success);">${r.buyurtmalar.length}</h3>
      </div>
    </div>

    <section class="card glass" style="margin-bottom: 2.5rem;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.2rem;">Tezkor Qidiruv</h2>
        <div style="position: relative; width: 300px;">
          <input type="text" id="dashboard-search" placeholder="Mebel nomi yoki modeli..." style="width: 100%; padding: 0.8rem 1rem 0.8rem 2.5rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text); outline: none;">
          <svg style="position: absolute; left: 0.8rem; top: 0.85rem; color: var(--text-muted);" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </div>
      </div>
      
      <div id="search-results">
        <p style="color: var(--text-muted); font-style: italic;">Qidiruv natijalari bu yerda chiqadi...</p>
      </div>
    </section>

    <section class="card glass">
      <h2 style="font-size: 1.2rem; margin-bottom: 1.5rem;">Oxirgi Buyurtmalar</h2>
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse;">
          <thead>
            <tr style="text-align: left; border-bottom: 1px solid var(--border);">
              <th style="padding: 1rem; color: var(--text-muted);">Mijoz</th>
              <th style="padding: 1rem; color: var(--text-muted);">Mebel</th>
              <th style="padding: 1rem; color: var(--text-muted);">Sana</th>
              <th style="padding: 1rem; color: var(--text-muted);">Holat</th>
            </tr>
          </thead>
          <tbody>
            ${r.buyurtmalar.slice(-5).reverse().map(e=>`
              <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 1rem;">${e.mijoz_ismi}</td>
                <td style="padding: 1rem;">${e.mahsulot_nomi}</td>
                <td style="padding: 1rem;">${new Date(e.sana).toLocaleDateString()}</td>
                <td style="padding: 1rem;"><span class="status-badge" style="background: rgba(99, 102, 241, 0.2); color: #818cf8;">${e.status}</span></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </section>
  `,a.appendChild(n),a.appendChild(i);const s=document.getElementById("dashboard-search"),o=document.getElementById("search-results");s.oninput=()=>{const e=s.value.toLowerCase().trim();if(!e){o.innerHTML='<p style="color: var(--text-muted); font-style: italic;">Qidiruv natijalari bu yerda chiqadi...</p>';return}const l=r.mebellar.filter(t=>t.nomi.toLowerCase().includes(e)||t.modeli.toLowerCase().includes(e));if(l.length===0){o.innerHTML='<p style="color: var(--danger);">Hech narsa topilmadi.</p>';return}o.innerHTML=`
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        ${l.map(t=>`
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: var(--surface-light); border-radius: var(--radius);">
            <div>
              <h4 style="margin: 0;">${t.nomi} <span style="font-weight: normal; color: var(--text-muted); font-size: 0.9rem;">(${t.modeli})</span></h4>
              <p style="font-size: 0.9rem; margin-top: 0.2rem;">${u(t.narxi,t.valyuta)}</p>
            </div>
            <div style="text-align: right;">
              <p style="font-weight: 700; color: ${t.soni<=3?"var(--warning)":"var(--success)"};">${t.soni} dona</p>
              <p style="font-size: 0.8rem; color: var(--text-muted);">Skladda qolgan</p>
            </div>
          </div>
        `).join("")}
      </div>
    `}};export{v as renderDashboard};
