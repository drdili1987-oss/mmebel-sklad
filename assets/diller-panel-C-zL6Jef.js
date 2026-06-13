import{s as d,r as z}from"./index-DK_9OF3L.js";import{c as B,a as h}from"./helpers-k-Czh5Xr.js";import{r as E}from"./modal-BYbuQYWW.js";import{s as f}from"./toast-BpzGVeOF.js";const o=s=>new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(s),k=()=>{var b,y,v,x;const s=document.getElementById("app");s.innerHTML="";const m=(b=d.user)==null?void 0:b.diller_id,u=((y=d.user)==null?void 0:y.diller_ismi)||"Diller",c=d.dillerlar.find(e=>e.id===m);if(!m||!c){z.navigate("/login");return}const t=d.dillerHisoblar.filter(e=>e.diller_id===m).sort((e,a)=>new Date(a.yaratilgan).getTime()-new Date(e.yaratilgan).getTime()),n=t.reduce((e,a)=>e+a.jami_narx,0),i=t.reduce((e,a)=>e+a.tolangan_summa,0),r=t.filter(e=>e.yetkazildi).reduce((e,a)=>e+(a.jami_narx-a.tolangan_summa),0),l=t.filter(e=>!e.yetkazildi).length,g=e=>e.yetkazildi?e.to_lov_holati==="toliq"?`<span style="background:rgba(16,185,129,0.15);color:#10b981;padding:0.28rem 0.65rem;border-radius:999px;font-size:0.72rem;font-weight:700;white-space:nowrap;">✅ To'liq to'landi</span>`:e.to_lov_holati==="qisman"?`<span style="background:rgba(245,158,11,0.15);color:#f59e0b;padding:0.28rem 0.65rem;border-radius:999px;font-size:0.72rem;font-weight:700;white-space:nowrap;">⏳ Qisman to'landi</span>`:`<span style="background:rgba(239,68,68,0.15);color:#ef4444;padding:0.28rem 0.65rem;border-radius:999px;font-size:0.72rem;font-weight:700;white-space:nowrap;">🔴 To'lov kutilmoqda</span>`:'<span style="background:rgba(99,102,241,0.15);color:#818cf8;padding:0.28rem 0.65rem;border-radius:999px;font-size:0.72rem;font-weight:700;white-space:nowrap;">📦 Omborga keldi</span>',p=B("main","main-content");p.innerHTML=`
    <!-- Topbar -->
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2rem;flex-wrap:wrap;gap:1rem;">
      <div>
        <h1 style="font-size:1.7rem;margin-bottom:0.3rem;">Salom, <span style="background:linear-gradient(to right,#818cf8,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">${u}!</span> 👋</h1>
        <p style="color:var(--text-muted);font-size:0.88rem;">${c.kompaniya} • ${c.telefon}</p>
      </div>
      <div style="display:flex;gap:0.75rem;align-items:center;">
        <button id="yangi-zakaz-btn" class="btn-primary" style="padding:0.65rem 1.3rem;border-radius:10px;font-size:0.9rem;font-weight:700;">
          📦 Yangi Zakaz
        </button>
        <button id="chiqish-btn" style="padding:0.65rem 1.1rem;border-radius:10px;border:1px solid var(--border);background:var(--surface-light);color:var(--text-muted);font-size:0.88rem;cursor:pointer;font-weight:600;">
          🚪 Chiqish
        </button>
      </div>
    </div>

    <!-- Statistika kartalar -->
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1.2rem;margin-bottom:2rem;">
      <div class="card glass" style="padding:1.2rem;border-left:3px solid #6366f1;">
        <p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">Jami Zakazlar</p>
        <p style="font-size:1.6rem;font-weight:800;color:var(--primary);">${t.length} ta</p>
        <p style="font-size:0.72rem;color:var(--text-muted);margin-top:0.25rem;">${o(n)}</p>
      </div>
      <div class="card glass" style="padding:1.2rem;border-left:3px solid #818cf8;">
        <p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">Omborga Kelgan</p>
        <p style="font-size:1.6rem;font-weight:800;color:#818cf8;">${l} ta</p>
        <p style="font-size:0.72rem;color:var(--text-muted);margin-top:0.25rem;">Hali yetkazilmagan</p>
      </div>
      <div class="card glass" style="padding:1.2rem;border-left:3px solid #10b981;">
        <p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">To'langan</p>
        <p style="font-size:1.6rem;font-weight:800;color:#10b981;">${o(i)}</p>
        <p style="font-size:0.72rem;color:var(--text-muted);margin-top:0.25rem;">${t.filter(e=>e.to_lov_holati==="toliq").length} ta yopiq</p>
      </div>
      <div class="card glass" style="padding:1.2rem;border-left:3px solid ${r>0?"#ef4444":"#10b981"};">
        <p style="font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:0.4rem;">Qarz (yetkazilgan)</p>
        <p style="font-size:1.6rem;font-weight:800;color:${r>0?"#ef4444":"#10b981"};">${r>0?o(r):"✓ 0"}</p>
        <p style="font-size:0.72rem;color:var(--text-muted);margin-top:0.25rem;">Faqat yetkazilganlar</p>
      </div>
    </div>

    <!-- Barcha zakazlar (bir jadvalda) -->
    <section class="card glass" style="overflow:hidden;">
      <div style="padding:1rem 1.5rem;background:linear-gradient(135deg,rgba(99,102,241,0.08),rgba(139,92,246,0.05));border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:0.75rem;">
        <div>
          <h2 style="font-size:1rem;font-weight:700;margin-bottom:0.15rem;">📋 Barcha Zakazlar — Hisobot</h2>
          <p style="font-size:0.78rem;color:var(--text-muted);">
            Jami: <strong>${t.length} ta</strong>
            ${l>0?`• <span style="color:#818cf8;">${l} ta omborga kelgan (qarzga kirmaydi)</span>`:""}
          </p>
        </div>
        ${t.length>0?`
          <div style="font-size:0.82rem;color:var(--text-muted);">
            Jami qarz:
            <strong style="color:${r>0?"#ef4444":"#10b981"};font-size:1rem;">
              ${r>0?o(r):"✓ 0"}
            </strong>
          </div>
        `:""}
      </div>

      ${t.length===0?`
        <div style="text-align:center;padding:4rem 2rem;color:var(--text-muted);">
          <div style="font-size:3rem;margin-bottom:1rem;">📦</div>
          <p style="font-size:1.05rem;margin-bottom:0.4rem;">Hali zakazlar yo'q</p>
          <p style="font-size:0.85rem;">Yuqoridagi "📦 Yangi Zakaz" tugmasini bosing</p>
        </div>
      `:`
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;min-width:700px;">
          <thead>
            <tr style="background:rgba(99,102,241,0.04);border-bottom:1px solid var(--border);">
              <th style="padding:0.75rem 1.2rem;text-align:left;font-size:0.73rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;">#</th>
              <th style="padding:0.75rem 1rem;text-align:left;font-size:0.73rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;">Mebel</th>
              <th style="padding:0.75rem 0.8rem;text-align:center;font-size:0.73rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;">Soni</th>
              <th style="padding:0.75rem 1rem;text-align:right;font-size:0.73rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;">Jami summa</th>
              <th style="padding:0.75rem 1rem;text-align:right;font-size:0.73rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;">To'langan</th>
              <th style="padding:0.75rem 1rem;text-align:right;font-size:0.73rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;">Qarz</th>
              <th style="padding:0.75rem 1rem;text-align:center;font-size:0.73rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;">Sana</th>
              <th style="padding:0.75rem 1rem;text-align:center;font-size:0.73rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;">Holat</th>
              <th style="padding:0.75rem 1rem;text-align:center;font-size:0.73rem;color:var(--text-muted);font-weight:600;text-transform:uppercase;">Amal</th>
            </tr>
          </thead>
          <tbody>
            ${t.map((e,a)=>`
              <tr style="border-bottom:1px solid var(--border);background:${e.yetkazildi?"transparent":"rgba(99,102,241,0.025)"};">
                <td style="padding:0.9rem 1.2rem;font-size:0.78rem;color:var(--text-muted);font-weight:600;">${t.length-a}</td>
                <td style="padding:0.9rem 1rem;">
                  <div style="font-weight:600;font-size:0.92rem;">${e.mebel_nomi}</div>
                  <div style="font-size:0.75rem;color:var(--text-muted);">${e.modeli}</div>
                </td>
                <td style="padding:0.9rem 0.8rem;text-align:center;font-weight:700;font-size:0.95rem;">${e.soni}</td>
                <td style="padding:0.9rem 1rem;text-align:right;font-weight:700;color:var(--primary);">${o(e.jami_narx)}</td>
                <td style="padding:0.9rem 1rem;text-align:right;color:#10b981;font-weight:600;">
                  ${e.yetkazildi?o(e.tolangan_summa):'<span style="color:var(--text-muted);font-size:0.78rem;">—</span>'}
                </td>
                <td style="padding:0.9rem 1rem;text-align:right;font-weight:700;">
                  ${e.yetkazildi?`<span style="color:${e.jami_narx-e.tolangan_summa>0?"#ef4444":"#10b981"};">
                        ${e.jami_narx-e.tolangan_summa>0?o(e.jami_narx-e.tolangan_summa):"✓"}
                       </span>`:'<span style="font-size:0.75rem;color:var(--text-muted);">Qarzga kirmaydi</span>'}
                </td>
                <td style="padding:0.9rem 1rem;text-align:center;font-size:0.78rem;color:var(--text-muted);">
                  ${h(e.kelgan_sana)}
                  ${e.yetkazildi_sana?`<br><span style="color:#10b981;font-size:0.7rem;">✓ ${h(e.yetkazildi_sana)}</span>`:""}
                </td>
                <td style="padding:0.9rem 1rem;text-align:center;">${g(e)}</td>
                <td style="padding:0.9rem 1rem;text-align:center;">
                  ${e.yetkazildi?'<span style="font-size:0.8rem;color:var(--text-muted);">—</span>':`
                    <button class="bekor-btn"
                      data-id="${e.id}"
                      data-nomi="${e.mebel_nomi}"
                      data-model="${e.modeli}"
                      data-soni="${e.soni}"
                      style="background:rgba(239,68,68,0.12);color:#ef4444;border:1px solid rgba(239,68,68,0.25);padding:0.38rem 0.8rem;border-radius:7px;font-size:0.78rem;font-weight:600;cursor:pointer;white-space:nowrap;">
                      ✕ Bekor
                    </button>
                  `}
                </td>
              </tr>
            `).join("")}
          </tbody>
          <tfoot>
            <tr style="border-top:2px solid var(--border);background:rgba(99,102,241,0.04);">
              <td colspan="3" style="padding:0.85rem 1.2rem;font-weight:700;font-size:0.88rem;">Jami</td>
              <td style="padding:0.85rem 1rem;text-align:right;font-weight:800;color:var(--primary);">${o(n)}</td>
              <td style="padding:0.85rem 1rem;text-align:right;font-weight:800;color:#10b981;">${o(i)}</td>
              <td style="padding:0.85rem 1rem;text-align:right;font-weight:800;color:${r>0?"#ef4444":"#10b981"};">
                ${r>0?o(r):"✓ 0"}
              </td>
              <td colspan="3"></td>
            </tr>
          </tfoot>
        </table>
      </div>`}
    </section>
  `,s.appendChild(p),(v=document.getElementById("chiqish-btn"))==null||v.addEventListener("click",()=>{d.logout(),z.navigate("/login")}),(x=document.getElementById("yangi-zakaz-btn"))==null||x.addEventListener("click",()=>{I(m,u)}),p.addEventListener("click",e=>{const a=e.target.closest(".bekor-btn");if(a){const w=a.dataset.id,$=a.dataset.nomi,_=a.dataset.model,q=a.dataset.soni;confirm(`❌ "${$} — ${_}" (${q} dona)

Zakazni bekor qilasizmi? Ombordagi soni ham kamaytiriladi.`)&&(d.cancelDillerHisob(w),f("✅ Zakaz bekor qilindi. Ombordagi soni yangilandi."),k())}})};function I(s,m){const c=`
    <div style="display:flex;flex-direction:column;gap:1rem;">
      <div style="padding:0.75rem 1rem;background:rgba(99,102,241,0.08);border-radius:10px;border:1px solid rgba(99,102,241,0.2);font-size:0.82rem;color:var(--text-muted);">
        📦 Zakaz berilgach, mebel <strong style="color:var(--text);">avtomatik ombordaga qo'shiladi</strong>
      </div>
      <div style="display:flex;gap:1rem;">
        <div style="flex:2;">
          <label style="display:block;font-size:0.85rem;color:var(--text-muted);margin-bottom:0.4rem;">Mebel nomi *</label>
          <input type="text" id="z-nomi" value="Comfort"
            style="width:100%;padding:0.7rem;border-radius:var(--radius);border:1px solid var(--border);background:var(--surface-light);color:var(--text);">
        </div>
        <div style="flex:2;">
          <label style="display:block;font-size:0.85rem;color:var(--text-muted);margin-bottom:0.4rem;">Modeli *</label>
          <input type="text" id="z-modeli" placeholder="Divan, Kreslo, Ugol..."
            style="width:100%;padding:0.7rem;border-radius:var(--radius);border:1px solid var(--border);background:var(--surface-light);color:var(--text);">
        </div>
      </div>
      <div style="display:flex;gap:1rem;">
        <div style="flex:1;">
          <label style="display:block;font-size:0.85rem;color:var(--text-muted);margin-bottom:0.4rem;">Soni (dona) *</label>
          <input type="number" id="z-soni" value="1" min="1"
            style="width:100%;padding:0.7rem;border-radius:var(--radius);border:1px solid var(--border);background:var(--surface-light);color:var(--text);">
        </div>
        <div style="flex:1;">
          <label style="display:block;font-size:0.85rem;color:var(--text-muted);margin-bottom:0.4rem;">Birlik narxi (USD) *</label>
          <input type="number" id="z-narxi" value="800" min="1" step="0.01"
            style="width:100%;padding:0.7rem;border-radius:var(--radius);border:1px solid var(--border);background:var(--surface-light);color:var(--text);">
        </div>
      </div>
      <div>
        <label style="display:block;font-size:0.85rem;color:var(--text-muted);margin-bottom:0.4rem;">Kelgan sana *</label>
        <input type="date" id="z-sana" value="${new Date().toISOString().split("T")[0]}"
          style="width:100%;padding:0.7rem;border-radius:var(--radius);border:1px solid var(--border);background:var(--surface-light);color:var(--text);">
      </div>
      <div id="z-jami-preview"
        style="padding:0.9rem 1rem;background:rgba(99,102,241,0.06);border-radius:10px;border:1px solid rgba(99,102,241,0.15);font-size:1rem;font-weight:800;color:var(--primary);text-align:center;">
        Jami: —
      </div>
    </div>
  `;E("📦 Yangi Zakaz Berish",c,()=>{const t=document.getElementById("z-nomi").value.trim(),n=document.getElementById("z-modeli").value.trim(),i=Number(document.getElementById("z-soni").value),r=Number(document.getElementById("z-narxi").value),l=document.getElementById("z-sana").value;if(!t||!n||i<=0||r<=0||!l){f("Barcha maydonlarni to'ldiring!","error");return}const g=i*r;d.addDillerHisob({diller_id:s,diller_ismi:m,mebel_nomi:t,modeli:n,soni:i,birlik_narxi:r,jami_narx:g,kelgan_sana:l,to_lov_holati:"kutilmoqda",tolangan_summa:0,yetkazildi:!1}),f(`✅ ${t} ${n} (${i} dona) zakaz berildi va ombordaga qo'shildi!`),k()}),setTimeout(()=>{var n,i;const t=()=>{var p,b;const r=Number(((p=document.getElementById("z-soni"))==null?void 0:p.value)||0),l=Number(((b=document.getElementById("z-narxi"))==null?void 0:b.value)||0),g=document.getElementById("z-jami-preview");g&&(g.textContent=r>0&&l>0?`Jami: ${new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(r*l)}`:"Jami: —")};(n=document.getElementById("z-soni"))==null||n.addEventListener("input",t),(i=document.getElementById("z-narxi"))==null||i.addEventListener("input",t)},100)}export{k as renderDillerPanel};
