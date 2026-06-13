import{s,r as k}from"./index-UZxus3QL.js";import{c as E,a as u}from"./helpers-k-Czh5Xr.js";import{r as I}from"./modal-BYbuQYWW.js";import{s as y}from"./toast-BpzGVeOF.js";const i=g=>new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(g),w=()=>{var v,x,z,h;const g=document.getElementById("app");g.innerHTML="";const p=(v=s.user)==null?void 0:v.diller_id,c=((x=s.user)==null?void 0:x.diller_ismi)||"Diller",o=s.dillerlar.find(e=>e.id===p);if(!p||!o){k.navigate("/login");return}const r=s.dillerHisoblar.filter(e=>e.diller_id===p),n=r.reduce((e,t)=>e+t.jami_narx,0),m=r.reduce((e,t)=>e+t.tolangan_summa,0),a=r.filter(e=>e.yetkazildi).reduce((e,t)=>e+(t.jami_narx-t.tolangan_summa),0),l=r.filter(e=>!e.yetkazildi),d=r.filter(e=>e.yetkazildi),b=e=>e.yetkazildi?e.to_lov_holati==="toliq"?`<span style="background:rgba(16,185,129,0.15);color:#10b981;padding:0.25rem 0.6rem;border-radius:999px;font-size:0.72rem;font-weight:700;">✅ To'liq to'langan</span>`:e.to_lov_holati==="qisman"?`<span style="background:rgba(245,158,11,0.15);color:#f59e0b;padding:0.25rem 0.6rem;border-radius:999px;font-size:0.72rem;font-weight:700;">⏳ Qisman to'langan</span>`:`<span style="background:rgba(239,68,68,0.15);color:#ef4444;padding:0.25rem 0.6rem;border-radius:999px;font-size:0.72rem;font-weight:700;">🔴 To'lov kutilmoqda</span>`:'<span style="background:rgba(99,102,241,0.15);color:#818cf8;padding:0.25rem 0.6rem;border-radius:999px;font-size:0.72rem;font-weight:700;">📦 Omborga kelgan</span>',f=E("main","main-content");f.innerHTML=`
    <!-- Diller topbar -->
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
      <div>
        <h1 style="font-size: 1.7rem; margin-bottom: 0.3rem;">
          Salom, ${c}! 👋
        </h1>
        <p style="color: var(--text-muted); font-size: 0.9rem;">${o.kompaniya} • ${o.telefon}</p>
      </div>
      <div style="display: flex; gap: 0.75rem; align-items: center;">
        <button id="yangi-zakaz-btn" class="btn-primary" style="padding: 0.65rem 1.3rem; border-radius: 10px; font-size: 0.9rem; font-weight: 700;">
          📦 Yangi Zakaz
        </button>
        <button id="chiqish-btn" style="padding: 0.65rem 1.1rem; border-radius: 10px; border: 1px solid var(--border); background: var(--surface-light); color: var(--text-muted); font-size: 0.88rem; cursor: pointer; font-weight: 600;">
          🚪 Chiqish
        </button>
      </div>
    </div>

    <!-- Statistika kartalar -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); gap: 1.2rem; margin-bottom: 2rem;">
      <div class="card glass" style="padding: 1.2rem; border-left: 3px solid #6366f1;">
        <p style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Jami Zakazlar</p>
        <p style="font-size: 1.6rem; font-weight: 800; color: var(--primary);">${r.length} ta</p>
        <p style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.25rem;">${i(n)}</p>
      </div>
      <div class="card glass" style="padding: 1.2rem; border-left: 3px solid #818cf8;">
        <p style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Omborga Kelgan</p>
        <p style="font-size: 1.6rem; font-weight: 800; color: #818cf8;">${l.length} ta</p>
        <p style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.25rem;">Hali yetkazilmagan</p>
      </div>
      <div class="card glass" style="padding: 1.2rem; border-left: 3px solid #10b981;">
        <p style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">To'langan</p>
        <p style="font-size: 1.6rem; font-weight: 800; color: #10b981;">${i(m)}</p>
        <p style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.25rem;">${d.filter(e=>e.to_lov_holati==="toliq").length} ta yopiq</p>
      </div>
      <div class="card glass" style="padding: 1.2rem; border-left: 3px solid ${a>0?"#ef4444":"#10b981"};">
        <p style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Haqiqiy Qarz</p>
        <p style="font-size: 1.6rem; font-weight: 800; color: ${a>0?"#ef4444":"#10b981"};">${a>0?i(a):"✓ 0"}</p>
        <p style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.25rem;">Faqat yetkazilganlar</p>
      </div>
    </div>

    <!-- Omborga kelgan zakazlar (yetkazilmagan) -->
    ${l.length>0?`
    <section class="card glass" style="margin-bottom: 1.5rem; overflow: hidden; border: 1px solid rgba(99,102,241,0.25);">
      <div style="padding: 1rem 1.5rem; background: rgba(99,102,241,0.07); border-bottom: 1px solid rgba(99,102,241,0.15);">
        <h2 style="font-size: 1rem; font-weight: 700; color: #818cf8;">📦 Omborga kelgan — hali yetkazilmagan (${l.length} ta)</h2>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem;">Bu zakazlar qarzga kirmaydi. Bekor qilishingiz mumkin.</p>
      </div>
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; min-width: 600px;">
          <thead>
            <tr style="border-bottom: 1px solid var(--border);">
              <th style="padding: 0.7rem 1.2rem; text-align: left; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Mebel</th>
              <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Soni</th>
              <th style="padding: 0.7rem 1rem; text-align: right; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Summa</th>
              <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Kelgan sana</th>
              <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Amal</th>
            </tr>
          </thead>
          <tbody>
            ${l.map(e=>`
              <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 0.9rem 1.2rem;">
                  <div style="font-weight: 600; font-size: 0.9rem;">${e.mebel_nomi}</div>
                  <div style="font-size: 0.75rem; color: var(--text-muted);">${e.modeli}</div>
                </td>
                <td style="padding: 0.9rem 1rem; text-align: center; font-weight: 700;">${e.soni} dona</td>
                <td style="padding: 0.9rem 1rem; text-align: right; font-weight: 700; color: #818cf8;">${i(e.jami_narx)}</td>
                <td style="padding: 0.9rem 1rem; text-align: center; font-size: 0.82rem; color: var(--text-muted);">${u(e.kelgan_sana)}</td>
                <td style="padding: 0.9rem 1rem; text-align: center;">
                  <button class="bekor-btn" data-id="${e.id}" data-nomi="${e.mebel_nomi}" data-model="${e.modeli}" data-soni="${e.soni}"
                    style="background: rgba(239,68,68,0.12); color: #ef4444; border: none; padding: 0.38rem 0.85rem; border-radius: 7px; font-size: 0.8rem; font-weight: 600; cursor: pointer;">
                    ✕ Bekor qilish
                  </button>
                </td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    </section>`:""}

    <!-- Zakazlar tarixi (yetkazilgan) -->
    <section class="card glass" style="overflow: hidden;">
      <div style="padding: 1rem 1.5rem; background: rgba(16,185,129,0.06); border-bottom: 1px solid rgba(16,185,129,0.15);">
        <h2 style="font-size: 1rem; font-weight: 700; color: #10b981;">📋 Zakazlar tarixi — yetkazilgan (${d.length} ta)</h2>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem;">To'lov holatini faqat admin belgilaydi</p>
      </div>
      ${d.length===0?`
        <div style="text-align: center; padding: 3rem; color: var(--text-muted);">
          <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">📋</div>
          <p>Hali yetkazilgan zakazlar yo'q</p>
        </div>
      `:`
      <div style="overflow-x: auto;">
        <table style="width: 100%; border-collapse: collapse; min-width: 680px;">
          <thead>
            <tr style="border-bottom: 1px solid var(--border);">
              <th style="padding: 0.7rem 1.2rem; text-align: left; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Mebel</th>
              <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Soni</th>
              <th style="padding: 0.7rem 1rem; text-align: right; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Jami</th>
              <th style="padding: 0.7rem 1rem; text-align: right; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">To'langan</th>
              <th style="padding: 0.7rem 1rem; text-align: right; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Qarz</th>
              <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Kelgan sana</th>
              <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.73rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Holat</th>
            </tr>
          </thead>
          <tbody>
            ${d.map(e=>`
              <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 0.85rem 1.2rem;">
                  <div style="font-weight: 600; font-size: 0.9rem;">${e.mebel_nomi}</div>
                  <div style="font-size: 0.75rem; color: var(--text-muted);">${e.modeli}</div>
                </td>
                <td style="padding: 0.85rem 1rem; text-align: center; font-weight: 700;">${e.soni}</td>
                <td style="padding: 0.85rem 1rem; text-align: right; font-weight: 700; color: var(--primary);">${i(e.jami_narx)}</td>
                <td style="padding: 0.85rem 1rem; text-align: right; color: #10b981; font-weight: 600;">${i(e.tolangan_summa)}</td>
                <td style="padding: 0.85rem 1rem; text-align: right; font-weight: 700; color: ${e.jami_narx-e.tolangan_summa>0?"#ef4444":"#10b981"};">
                  ${e.jami_narx-e.tolangan_summa>0?i(e.jami_narx-e.tolangan_summa):"✓"}
                </td>
                <td style="padding: 0.85rem 1rem; text-align: center; font-size: 0.82rem; color: var(--text-muted);">
                  ${u(e.kelgan_sana)}
                  ${e.yetkazildi_sana?`<br><span style="color: #10b981; font-size: 0.72rem;">↳ ${u(e.yetkazildi_sana)}</span>`:""}
                </td>
                <td style="padding: 0.85rem 1rem; text-align: center;">${b(e)}</td>
              </tr>
            `).join("")}
          </tbody>
          <tfoot>
            <tr style="border-top: 2px solid var(--border); background: rgba(99,102,241,0.04);">
              <td colspan="2" style="padding: 0.85rem 1.2rem; font-weight: 700; font-size: 0.88rem;">Jami (yetkazilgan)</td>
              <td style="padding: 0.85rem 1rem; text-align: right; font-weight: 800; color: var(--primary);">${i(d.reduce((e,t)=>e+t.jami_narx,0))}</td>
              <td style="padding: 0.85rem 1rem; text-align: right; font-weight: 800; color: #10b981;">${i(d.reduce((e,t)=>e+t.tolangan_summa,0))}</td>
              <td style="padding: 0.85rem 1rem; text-align: right; font-weight: 800; color: ${a>0?"#ef4444":"#10b981"};">${a>0?i(a):"✓"}</td>
              <td colspan="2"></td>
            </tr>
          </tfoot>
        </table>
      </div>`}
    </section>
  `,g.appendChild(f),(z=document.getElementById("chiqish-btn"))==null||z.addEventListener("click",()=>{s.logout(),k.navigate("/login")}),(h=document.getElementById("yangi-zakaz-btn"))==null||h.addEventListener("click",()=>{j(p,c)}),f.addEventListener("click",e=>{const t=e.target.closest(".bekor-btn");if(t){const $=t.dataset.id,_=t.dataset.nomi,q=t.dataset.model,B=t.dataset.soni;confirm(`❌ "${_} — ${q}" (${B} dona) zakazini bekor qilasizmi?
Ombordagi soni ham kamaytiriladi.`)&&(s.cancelDillerHisob($),y("Zakaz bekor qilindi. Ombordagi soni yangilandi."),w())}})};function j(g,p){const c=`
    <div style="display: flex; flex-direction: column; gap: 1rem;">
      <div style="padding: 0.75rem 1rem; background: rgba(99,102,241,0.08); border-radius: 10px; border: 1px solid rgba(99,102,241,0.15); font-size: 0.82rem; color: var(--text-muted);">
        📦 Zakaz berilgach, mebel <strong style="color: var(--text);">avtomatik ombordaga qo'shiladi</strong>
      </div>
      <div style="display: flex; gap: 1rem;">
        <div style="flex: 2;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Mebel nomi *</label>
          <input type="text" id="z-nomi" value="Comfort" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div style="flex: 2;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Modeli *</label>
          <input type="text" id="z-modeli" placeholder="Divan, Kreslo, Set..." style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
      </div>
      <div style="display: flex; gap: 1rem;">
        <div style="flex: 1;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Soni (dona) *</label>
          <input type="number" id="z-soni" value="1" min="1" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div style="flex: 1;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Birlik narxi (USD) *</label>
          <input type="number" id="z-narxi" value="800" min="1" step="0.01" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
      </div>
      <div>
        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Kelgan sana *</label>
        <input type="date" id="z-sana" value="${new Date().toISOString().split("T")[0]}" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
      </div>
      <div id="z-jami-preview" style="padding: 0.75rem 1rem; background: rgba(99,102,241,0.06); border-radius: 10px; border: 1px solid rgba(99,102,241,0.15); font-size: 0.88rem; font-weight: 700; color: var(--primary); text-align: center;">
        Jami: —
      </div>
    </div>
  `;I("📦 Yangi Zakaz Berish",c,()=>{const o=document.getElementById("z-nomi").value.trim(),r=document.getElementById("z-modeli").value.trim(),n=Number(document.getElementById("z-soni").value),m=Number(document.getElementById("z-narxi").value),a=document.getElementById("z-sana").value;if(o&&r&&n>0&&m>0&&a){const l=n*m;s.addDillerHisob({diller_id:g,diller_ismi:p,mebel_nomi:o,modeli:r,soni:n,birlik_narxi:m,jami_narx:l,kelgan_sana:a,to_lov_holati:"kutilmoqda",tolangan_summa:0,yetkazildi:!1}),y(`✅ Zakaz qo'shildi! ${o} ${r} (${n} dona) ombordaga qo'shildi.`),w()}else y("Iltimos, barcha maydonlarni to'ldiring!","error")}),setTimeout(()=>{var r,n;const o=()=>{var d,b;const m=Number(((d=document.getElementById("z-soni"))==null?void 0:d.value)||0),a=Number(((b=document.getElementById("z-narxi"))==null?void 0:b.value)||0),l=document.getElementById("z-jami-preview");l&&(l.textContent=`Jami: ${m>0&&a>0?new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(m*a):"—"}`)};(r=document.getElementById("z-soni"))==null||r.addEventListener("input",o),(n=document.getElementById("z-narxi"))==null||n.addEventListener("input",o)},100)}export{w as renderDillerPanel};
