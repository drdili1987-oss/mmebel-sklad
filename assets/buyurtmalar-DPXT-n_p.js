import{s as o}from"./index-DK_9OF3L.js";import{r as v}from"./sidebar-D6l_IL88.js";import{c as f,a as h,f as x}from"./helpers-k-Czh5Xr.js";import{r as $}from"./modal-BYbuQYWW.js";import{s}from"./toast-BpzGVeOF.js";const l=()=>{var u;const m=document.getElementById("app");m.innerHTML="";const b=v(),c=f("main","main-content"),y=()=>o.buyurtmalar.length===0?`<p style="color: var(--text-muted); text-align: center; padding: 2rem;">Hozircha buyurtmalar yo'q.</p>`:`
      <div style="display: grid; gap: 1rem;">
        ${o.buyurtmalar.slice().sort((t,r)=>new Date(r.sana).getTime()-new Date(t.sana).getTime()).map(t=>`
          <div class="card glass" style="display: flex; justify-content: space-between; align-items: center; padding: 1.2rem;">
            <div>
              <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
                <h3 style="font-size: 1.1rem;">${t.mijoz_ismi}</h3>
                <span class="status-badge" style="background: rgba(99, 102, 241, 0.1); color: #818cf8; font-size: 0.7rem;">${t.id}</span>
              </div>
              <p style="font-size: 0.9rem; color: var(--text-muted); margin-bottom: 0.3rem;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"></path></svg>
                ${t.mahsulot_nomi} (${t.miqdori} dona)
              </p>
              <p style="font-size: 0.9rem; color: var(--text-muted);">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 4px;"><path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                Muddati: <span style="font-weight: 600; color: var(--accent);">${h(t.tayyor_sana)}</span>
              </p>
            </div>
            <div style="text-align: right;">
              <p style="font-weight: 700; margin-bottom: 0.8rem;">
                ${t.chegirma?`<span style="text-decoration: line-through; color: var(--text-muted); font-size: 0.85rem; margin-right: 0.4rem;">$${t.jami_narx}</span><span style="color: #7c3aed;">$${t.jami_narx-t.chegirma}</span>`:x(t.jami_narx,"USD")}
              </p>
              <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: flex-end;">
                <button class="status-btn ${t.status==="tayyorlanmoqda"?"active":""}" data-id="${t.id}" data-status="tayyorlanmoqda" style="padding: 0.4rem 0.8rem; font-size: 0.75rem; background: ${t.status==="tayyorlanmoqda"?"var(--warning)":"var(--surface-light)"};">Tayyorlanmoqda</button>
                <button class="status-btn ${t.status==="tayyor"?"active":""}" data-id="${t.id}" data-status="tayyor" style="padding: 0.4rem 0.8rem; font-size: 0.75rem; background: ${t.status==="tayyor"?"var(--success)":"var(--surface-light)"};">Tayyor</button>
                <button class="status-btn ${t.status==="yetkazildi"?"active":""}" data-id="${t.id}" data-status="yetkazildi" style="padding: 0.4rem 0.8rem; font-size: 0.75rem; background: ${t.status==="yetkazildi"?"var(--primary)":"var(--surface-light)"};">Yetkazildi</button>
                <button class="olib-ketdi-btn" data-id="${t.id}" style="padding: 0.4rem 0.8rem; font-size: 0.75rem; border-radius: var(--radius); border: none; cursor: pointer; font-weight: 600; background: ${t.ozi_olib_ketdi?"#7c3aed":"var(--surface-light)"}; color: ${t.ozi_olib_ketdi?"#fff":"var(--text)"}; transition: all 0.2s;">🚗 Mijoz ozi olib ketdi</button>
              </div>
              ${t.ozi_olib_ketdi?`
              <div style="display: flex; gap: 0.5rem; margin-top: 0.6rem; justify-content: flex-end; align-items: center;">
                <span style="font-size: 0.75rem; color: var(--text-muted);">Chegirma:</span>
                <button class="chegirma-btn" data-id="${t.id}" data-chegirma="6" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; font-weight: 700; border-radius: var(--radius); border: 2px solid ${t.chegirma===6?"#7c3aed":"var(--border)"}; cursor: pointer; background: ${t.chegirma===6?"#7c3aed":"transparent"}; color: ${t.chegirma===6?"#fff":"var(--text)"}; transition: all 0.2s;">$6</button>
                <button class="chegirma-btn" data-id="${t.id}" data-chegirma="8" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; font-weight: 700; border-radius: var(--radius); border: 2px solid ${t.chegirma===8?"#7c3aed":"var(--border)"}; cursor: pointer; background: ${t.chegirma===8?"#7c3aed":"transparent"}; color: ${t.chegirma===8?"#fff":"var(--text)"}; transition: all 0.2s;">$8</button>
                <button class="chegirma-btn" data-id="${t.id}" data-chegirma="10" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; font-weight: 700; border-radius: var(--radius); border: 2px solid ${t.chegirma===10?"#7c3aed":"var(--border)"}; cursor: pointer; background: ${t.chegirma===10?"#7c3aed":"transparent"}; color: ${t.chegirma===10?"#fff":"var(--text)"}; transition: all 0.2s;">$10</button>
                ${t.chegirma?`<span style="font-size: 0.8rem; color: #7c3aed; font-weight: 700; margin-left: 0.3rem;">-$${t.chegirma} chegirma</span>`:""}
              </div>`:""}
            </div>
          </div>
        `).join("")}
      </div>
    `;c.innerHTML=`
    <header style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
      <div>
        <h1 style="font-size: 1.8rem; margin-bottom: 0.5rem;">Buyurtmalar</h1>
        <p style="color: var(--text-muted);">Mijozlardan olingan zakazlar va ularning nazorati</p>
      </div>
      <button id="add-zakaz-btn" class="btn-primary">+ Yangi Buyurtma</button>
    </header>

    <div id="buyurtmalar-list-container">
      ${y()}
    </div>
  `,m.appendChild(b),m.appendChild(c),c.addEventListener("click",t=>{const r=t.target;if(r.classList.contains("status-btn")){const e=r.dataset.id,a=r.dataset.status,i=o.buyurtmalar.find(d=>d.id===e);i&&(i.status=a,localStorage.setItem("mmebel_buyurtmalar",JSON.stringify(o.buyurtmalar)),s(`Buyurtma holati "${a}"ga o'zgartirildi`),l());return}if(r.classList.contains("olib-ketdi-btn")){const e=r.dataset.id,a=o.buyurtmalar.find(i=>i.id===e);a&&(a.ozi_olib_ketdi=!a.ozi_olib_ketdi,a.ozi_olib_ketdi||(a.chegirma=void 0),localStorage.setItem("mmebel_buyurtmalar",JSON.stringify(o.buyurtmalar)),s(a.ozi_olib_ketdi?"🚗 Mijoz ozi olib ketdi! Chegirma tanlang.":"Bekor qilindi"),l());return}if(r.classList.contains("chegirma-btn")){const e=r.dataset.id,a=Number(r.dataset.chegirma),i=o.buyurtmalar.find(d=>d.id===e);i&&(i.chegirma===a?(i.chegirma=void 0,s("Chegirma bekor qilindi")):(i.chegirma=a,s(`✅ $${a} chegirma qo'llanildi!`)),localStorage.setItem("mmebel_buyurtmalar",JSON.stringify(o.buyurtmalar)),l());return}}),(u=document.getElementById("add-zakaz-btn"))==null||u.addEventListener("click",()=>{const t=o.mebellar.filter(e=>e.soni>0);if(t.length===0){s("Skladda mahsulot yo'q!","error");return}const r=`
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
            ${t.map(e=>`<option value="${e.id}">${e.nomi} (${e.soni} dona bor)</option>`).join("")}
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
    `;$("Yangi Buyurtma Qo'shish",r,()=>{const e=document.getElementById("z-mijoz").value,a=document.getElementById("z-tel").value,i=document.getElementById("z-mahsulot").value,d=Number(document.getElementById("z-soni").value),g=document.getElementById("z-sana").value,n=o.mebellar.find(p=>p.id===i);if(e&&g&&d>0){if(d>n.soni){s(`Skladda faqat ${n.soni} dona bor!`,"error");return}o.addBuyurtma({mijoz_ismi:e,mijoz_telefon:a,mahsulot_id:i,mahsulot_nomi:n.nomi,miqdori:d,jami_narx:n.narxi*d,tayyor_sana:g,status:"tayyorlanmoqda"}),s("Buyurtma muvaffaqiyatli qo'shildi!"),l()}else s("Iltimos, barcha maydonlarni to'ldiring","error")})})};export{l as renderBuyurtmalar};
