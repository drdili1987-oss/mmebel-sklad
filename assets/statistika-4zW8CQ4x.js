import{s as t}from"./index-DakUwRTP.js";import{r as g,c,f as n}from"./helpers-BSqnvA6D.js";const y=()=>{const i=document.getElementById("app");i.innerHTML="";const m=g(),s=c("main","main-content"),o={};t.buyurtmalar.forEach(e=>{o[e.mahsulot_nomi]=(o[e.mahsulot_nomi]||0)+e.miqdori});const a=Object.entries(o).sort((e,r)=>r[1]-e[1]),d=a.length>0?a[0][1]:0,l=t.buyurtmalar.reduce((e,r)=>e+(r.jami_narx-(r.chegirma||0)),0);s.innerHTML=`
    <header style="margin-bottom: 2rem;">
      <h1 style="font-size: 1.8rem; margin-bottom: 0.5rem;">Statistika</h1>
      <p style="color: var(--text-muted);">Sotuvlar va sklad holati tahlili</p>
    </header>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2.5rem;">
      <!-- Eng ko'p sotilganlar -->
      <section class="card glass">
        <h2 style="font-size: 1.1rem; margin-bottom: 1.5rem;">Eng ko'p sotilgan modellar</h2>
        <div style="display: flex; flex-direction: column; gap: 1.2rem;">
          ${a.length>0?a.map(([e,r])=>`
            <div>
              <div style="display: flex; justify-content: space-between; margin-bottom: 0.4rem; font-size: 0.9rem;">
                <span>${e}</span>
                <span style="font-weight: 700;">${r} ta</span>
              </div>
              <div style="height: 8px; background: var(--surface-light); border-radius: 4px; overflow: hidden;">
                <div style="height: 100%; background: linear-gradient(to right, var(--primary), #c084fc); width: ${r/d*100}%; border-radius: 4px;"></div>
              </div>
            </div>
          `).join(""):`<p style="color: var(--text-muted);">Ma'lumot yo'q.</p>`}
        </div>
      </section>

      <!-- Moliyaviy xulosa -->
      <section class="card glass" style="display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;">
        <p style="color: var(--text-muted); margin-bottom: 1rem;">Umumiy Daromad (Demo)</p>
        <h2 style="font-size: 2.5rem; color: var(--success); font-weight: 800; margin-bottom: 0.5rem;">${n(l,"USD")}</h2>
        <p style="font-size: 0.9rem; color: var(--text-muted);">Oxirgi 30 kun ichida</p>
        
        <div style="margin-top: 2rem; width: 100%; display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
          <div style="padding: 1rem; background: rgba(16, 185, 129, 0.1); border-radius: var(--radius);">
            <p style="font-size: 0.8rem; color: var(--text-muted);">O'rtacha chek</p>
            <p style="font-weight: 700;">${n(t.buyurtmalar.length?l/t.buyurtmalar.length:0,"USD")}</p>
          </div>
          <div style="padding: 1rem; background: rgba(99, 102, 241, 0.1); border-radius: var(--radius);">
            <p style="font-size: 0.8rem; color: var(--text-muted);">Buyurtmalar</p>
            <p style="font-weight: 700;">${t.buyurtmalar.length} ta</p>
          </div>
        </div>
      </section>
    </div>

    <!-- Sklad holati breakdown -->
    <section class="card glass">
      <h2 style="font-size: 1.1rem; margin-bottom: 1.5rem;">Sklad holati (Tizimli tahlil)</h2>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem;">
        <div style="text-align: center; padding: 1.5rem; border-radius: var(--radius); background: var(--surface-light);">
          <h3 style="color: var(--success); font-size: 1.1rem; margin-bottom: 0.5rem;">Sotuvda</h3>
          <p style="font-size: 2rem; font-weight: 700;">${t.mebellar.filter(e=>e.status==="sotuvda").length}</p>
          <p style="font-size: 0.8rem; color: var(--text-muted);">Yeterli miqdorda</p>
        </div>
        <div style="text-align: center; padding: 1.5rem; border-radius: var(--radius); background: var(--surface-light);">
          <h3 style="color: var(--warning); font-size: 1.1rem; margin-bottom: 0.5rem;">Kam Qolgan</h3>
          <p style="font-size: 2rem; font-weight: 700;">${t.mebellar.filter(e=>e.status==="kam_qoldi").length}</p>
          <p style="font-size: 0.8rem; color: var(--text-muted);">Tezda buyurtma bering!</p>
        </div>
        <div style="text-align: center; padding: 1.5rem; border-radius: var(--radius); background: var(--surface-light);">
          <h3 style="color: var(--danger); font-size: 1.1rem; margin-bottom: 0.5rem;">Tugagan</h3>
          <p style="font-size: 2rem; font-weight: 700;">${t.mebellar.filter(e=>e.status==="tugagan").length}</p>
          <p style="font-size: 0.8rem; color: var(--text-muted);">Zaxira qolmadi</p>
        </div>
      </div>
    </section>
  `,i.appendChild(m),i.appendChild(s)};export{y as renderStatistika};
