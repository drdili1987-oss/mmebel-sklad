import{s as o}from"./index-DK_9OF3L.js";import{r as v}from"./sidebar-D6l_IL88.js";import{c as h,f}from"./helpers-k-Czh5Xr.js";const x=()=>{var p;const n=document.getElementById("app");n.innerHTML="";const g=v(),m=h("main","main-content"),b=o.mebellar.filter(e=>e.soni<=3&&e.soni>0).length,u=o.mebellar.filter(e=>e.soni===0).length,a=o.dillerHisoblar.reduce((e,t)=>e+t.jami_narx,0),l=o.dillerHisoblar.reduce((e,t)=>e+t.tolangan_summa,0),i=a-l,y=o.dillerHisoblar.filter(e=>e.to_lov_holati!=="toliq"),s=e=>new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(e);m.innerHTML=`
    <header style="margin-bottom: 2rem;">
      <h1 style="font-size: 1.8rem; margin-bottom: 0.5rem;">Xush kelibsiz!</h1>
      <p style="color: var(--text-muted);">Sklad va buyurtmalar holati bilan tanishing</p>
    </header>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem; margin-bottom: 2.5rem;">
      <div class="card glass">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Jami Mebellar</p>
        <h3 style="font-size: 2rem; margin-top: 0.5rem;">${o.mebellar.length} <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: normal;">turda</span></h3>
      </div>
      <div class="card glass" style="border-left: 4px solid var(--warning);">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Kam qolganlar</p>
        <h3 style="font-size: 2rem; margin-top: 0.5rem; color: var(--warning);">${b}</h3>
      </div>
      <div class="card glass" style="border-left: 4px solid var(--danger);">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Tugaganlar</p>
        <h3 style="font-size: 2rem; margin-top: 0.5rem; color: var(--danger);">${u}</h3>
      </div>
      <div class="card glass" style="border-left: 4px solid var(--success);">
        <p style="color: var(--text-muted); font-size: 0.9rem;">Jami Buyurtmalar</p>
        <h3 style="font-size: 2rem; margin-top: 0.5rem; color: var(--success);">${o.buyurtmalar.length}</h3>
      </div>
    </div>

    <!-- Diller Hisob-kitob kartasi -->
    <section class="card glass" style="margin-bottom: 2.5rem; border: 1px solid ${i>0?"rgba(239,68,68,0.3)":"rgba(16,185,129,0.3)"}; overflow: hidden;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.2rem;">
        <div>
          <h2 style="font-size: 1.15rem; margin-bottom: 0.2rem;">💼 Diller Hisob-kitob</h2>
          <p style="font-size: 0.82rem; color: var(--text-muted);">Comfort mebel — dillerlar bilan to'lov holati</p>
        </div>
        ${i>0?`
          <button id="dash-yop-btn" style="
            background: linear-gradient(135deg, #10b981, #059669);
            color: white; border: none;
            padding: 0.7rem 1.4rem;
            border-radius: 10px;
            font-size: 0.9rem;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(16,185,129,0.35);
            transition: all 0.2s;
            display: flex; align-items: center; gap: 0.5rem;
          ">✅ Hisobni 0 qil — ${s(i)}</button>
        `:`
          <div style="display: flex; align-items: center; gap: 0.5rem; background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.25); border-radius: 10px; padding: 0.6rem 1.2rem;">
            <span style="font-size: 1.1rem;">✅</span>
            <span style="font-size: 0.88rem; font-weight: 700; color: #10b981;">Hisob-kitob yopiq!</span>
          </div>
        `}
      </div>

      <!-- Stats qatori -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin-bottom: 1.2rem;">
        <div style="padding: 1rem; background: rgba(99,102,241,0.08); border-radius: 10px; border: 1px solid rgba(99,102,241,0.15); text-align: center;">
          <p style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Jami Summa</p>
          <p style="font-size: 1.15rem; font-weight: 800; color: var(--primary);">${s(a)}</p>
        </div>
        <div style="padding: 1rem; background: rgba(16,185,129,0.08); border-radius: 10px; border: 1px solid rgba(16,185,129,0.15); text-align: center;">
          <p style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">To'langan</p>
          <p style="font-size: 1.15rem; font-weight: 800; color: #10b981;">${s(l)}</p>
        </div>
        <div style="padding: 1rem; background: ${i>0?"rgba(239,68,68,0.08)":"rgba(16,185,129,0.08)"}; border-radius: 10px; border: 1px solid ${i>0?"rgba(239,68,68,0.15)":"rgba(16,185,129,0.15)"}; text-align: center;">
          <p style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Qarz</p>
          <p style="font-size: 1.15rem; font-weight: 800; color: ${i>0?"#ef4444":"#10b981"};">${i>0?s(i):"✓ 0"}</p>
        </div>
        <div style="padding: 1rem; background: rgba(245,158,11,0.08); border-radius: 10px; border: 1px solid rgba(245,158,11,0.15); text-align: center;">
          <p style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Ochiq Hisob</p>
          <p style="font-size: 1.15rem; font-weight: 800; color: #f59e0b;">${y.length} ta</p>
        </div>
      </div>

      <!-- Progress bar -->
      ${a>0?`
        <div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem;">
            <span style="font-size: 0.78rem; color: var(--text-muted);">To'lov holati</span>
            <span style="font-size: 0.78rem; font-weight: 700; color: ${i>0?"var(--text)":"#10b981"};">${Math.round(l/a*100)}%</span>
          </div>
          <div style="height: 8px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden;">
            <div style="height: 100%; width: ${Math.round(l/a*100)}%; background: linear-gradient(to right, #10b981, #6366f1); border-radius: 4px; transition: width 0.5s ease;"></div>
          </div>
        </div>
      `:""}
    </section>

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
            ${o.buyurtmalar.slice(-5).reverse().map(e=>`
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
  `,n.appendChild(g),n.appendChild(m),(p=document.getElementById("dash-yop-btn"))==null||p.addEventListener("click",()=>{const e=o.dillerHisoblar.filter(t=>t.to_lov_holati!=="toliq");if(e.length!==0&&confirm(`✅ Barcha ${e.length} ta ochiq hisob yopilsinmi?
Jami qarz: ${s(i)}`)){e.forEach(r=>{o.updateDillerHisob(r.id,{tolangan_summa:r.jami_narx,to_lov_holati:"toliq"})});const t=document.createElement("div");t.textContent="✅ Barcha hisoblar yopildi! Hisob-kitob nol!",t.style.cssText=`
        position: fixed; bottom: 2rem; right: 2rem; z-index: 9999;
        background: linear-gradient(135deg, #10b981, #059669);
        color: white; padding: 1rem 1.5rem; border-radius: 12px;
        font-weight: 700; font-size: 0.95rem;
        box-shadow: 0 8px 25px rgba(16,185,129,0.4);
      `,document.body.appendChild(t),setTimeout(()=>t.remove(),3e3),x()}});const c=document.getElementById("dashboard-search"),d=document.getElementById("search-results");c.oninput=()=>{const e=c.value.toLowerCase().trim();if(!e){d.innerHTML='<p style="color: var(--text-muted); font-style: italic;">Qidiruv natijalari bu yerda chiqadi...</p>';return}const t=o.mebellar.filter(r=>r.nomi.toLowerCase().includes(e)||r.modeli.toLowerCase().includes(e));if(t.length===0){d.innerHTML='<p style="color: var(--danger);">Hech narsa topilmadi.</p>';return}d.innerHTML=`
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        ${t.map(r=>`
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; background: var(--surface-light); border-radius: var(--radius);">
            <div>
              <h4 style="margin: 0;">${r.nomi} <span style="font-weight: normal; color: var(--text-muted); font-size: 0.9rem;">(${r.modeli})</span></h4>
              <p style="font-size: 0.9rem; margin-top: 0.2rem;">${f(r.narxi,r.valyuta)}</p>
            </div>
            <div style="text-align: right;">
              <p style="font-weight: 700; color: ${r.soni<=3?"var(--warning)":"var(--success)"};">${r.soni} dona</p>
              <p style="font-size: 0.8rem; color: var(--text-muted);">Skladda qolgan</p>
            </div>
          </div>
        `).join("")}
      </div>
    `}};export{x as renderDashboard};
