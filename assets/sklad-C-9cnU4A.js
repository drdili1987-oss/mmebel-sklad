import{s as i}from"./index-DakUwRTP.js";import{r as p,c as g,f as y}from"./helpers-BSqnvA6D.js";import{r as u}from"./modal-BWsQC4Qk.js";const c=()=>{var m;const l=document.getElementById("app");l.innerHTML="";const v=p(),s=g("main","main-content"),b=()=>`
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
          ${i.mebellar.map(t=>`
            <tr style="border-bottom: 1px solid var(--border);">
              <td style="padding: 1rem; font-weight: 500;">${t.nomi}</td>
              <td style="padding: 1rem;">${t.modeli}</td>
              <td style="padding: 1rem;">${y(t.narxi,t.valyuta)}</td>
              <td style="padding: 1rem;">${t.soni} dona</td>
              <td style="padding: 1rem;">
                <span class="status-badge ${t.status==="sotuvda"?"status-instock":t.status==="kam_qoldi"?"status-low":"status-outofstock"}">
                  ${t.status==="sotuvda"?"Sotuvda":t.status==="kam_qoldi"?"Kam qoldi":"Tugagan"}
                </span>
              </td>
              <td style="padding: 1rem;">
                <button class="edit-btn" data-id="${t.id}" style="background: transparent; color: var(--primary); padding: 0.4rem;"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg></button>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;s.innerHTML=`
    <header style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
      <div>
        <h1 style="font-size: 1.8rem; margin-bottom: 0.5rem;">Sklad Boshqaruvi</h1>
        <p style="color: var(--text-muted);">Mahsulotlar qoldig'ini boshqarish va tahrirlash</p>
      </div>
      <button id="add-mebel-btn" class="btn-primary">+ Yangi Mahsulot</button>
    </header>

    <div class="card glass" style="overflow-x: auto;">
      <div id="sklad-table-container">
        ${b()}
      </div>
    </div>
  `,l.appendChild(v),l.appendChild(s),(m=document.getElementById("add-mebel-btn"))==null||m.addEventListener("click",()=>{u("Yangi Mahsulot Qo'shish",`
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
    `,()=>{const n=document.getElementById("m-nomi").value,e=document.getElementById("m-modeli").value,d=Number(document.getElementById("m-narxi").value),o=document.getElementById("m-valyuta").value,a=Number(document.getElementById("m-soni").value);n&&e&&(i.addMebel({nomi:n,modeli:e,narxi:d,valyuta:o,soni:a,status:a<=0?"tugagan":a<=3?"kam_qoldi":"sotuvda"}),c())})}),s.addEventListener("click",t=>{const e=t.target.closest(".edit-btn");if(e){const d=e.dataset.id,o=i.mebellar.find(r=>r.id===d),a=`
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div><label>Soni (Yangilash)</label>
          <input type="number" id="edit-soni" value="${o.soni}" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);"></div>
        </div>
      `;u(`${o.nomi} - Qoldiqni yangilash`,a,()=>{const r=Number(document.getElementById("edit-soni").value);i.updateMebel(d,{soni:r,status:r<=0?"tugagan":r<=3?"kam_qoldi":"sotuvda"}),c()})}})};export{c as renderSklad};
