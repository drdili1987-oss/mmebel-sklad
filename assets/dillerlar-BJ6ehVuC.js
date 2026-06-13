import{s as i}from"./index-DKpDt1A6.js";import{r as M}from"./sidebar-DTSFREI6.js";import{c as O,a as j}from"./helpers-k-Czh5Xr.js";import{r as H}from"./modal-BYbuQYWW.js";import{s as u}from"./toast-BpzGVeOF.js";const r=f=>new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(f),k=()=>{var I,D;const f=document.getElementById("app");f.innerHTML="";const B=M(),g=O("main","main-content"),E=i.dillerHisoblar.reduce((e,t)=>e+t.jami_narx,0),w=i.dillerHisoblar.reduce((e,t)=>e+t.tolangan_summa,0),p=i.dillerHisoblar.filter(e=>e.yetkazildi).reduce((e,t)=>e+(t.jami_narx-t.tolangan_summa),0),y=i.dillerHisoblar.filter(e=>!e.yetkazildi).length,s={};i.dillerHisoblar.forEach(e=>{s[e.diller_id]||(s[e.diller_id]={diller_ismi:e.diller_ismi,jami:0,tolangan:0,qarz:0,kutilmoqda:0,hisoblar:[]}),s[e.diller_id].jami+=e.jami_narx,s[e.diller_id].tolangan+=e.tolangan_summa,e.yetkazildi?s[e.diller_id].qarz+=e.jami_narx-e.tolangan_summa:s[e.diller_id].kutilmoqda+=e.jami_narx,s[e.diller_id].hisoblar.push(e)});const q=e=>e.yetkazildi?e.to_lov_holati==="toliq"?`<span style="background: rgba(16,185,129,0.15); color: #10b981; padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700;">✅ To'liq to'langan</span>`:e.to_lov_holati==="qisman"?`<span style="background: rgba(245,158,11,0.15); color: #f59e0b; padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700;">⏳ Qisman to'langan</span>`:`<span style="background: rgba(239,68,68,0.15); color: #ef4444; padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700;">🔴 To'lov kutilmoqda</span>`:'<span style="background: rgba(99,102,241,0.15); color: #818cf8; padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700;">⏳ Omborga kelgan</span>',$=e=>`
    <tr style="border-bottom: 1px solid var(--border);" class="hisob-row">
      <td style="padding: 0.9rem 1.2rem;">
        <div style="font-weight: 600; font-size: 0.92rem;">${e.mebel_nomi}</div>
        <div style="font-size: 0.78rem; color: var(--text-muted);">${e.modeli}</div>
      </td>
      <td style="padding: 0.9rem 1rem; text-align: center; font-weight: 700;">${e.soni} <span style="font-size: 0.72rem; color: var(--text-muted); font-weight: 400;">dona</span></td>
      <td style="padding: 0.9rem 1rem; text-align: right; font-weight: 600;">${r(e.birlik_narxi)}</td>
      <td style="padding: 0.9rem 1rem; text-align: right; font-weight: 700; color: var(--primary);">${r(e.jami_narx)}</td>
      <td style="padding: 0.9rem 1rem; text-align: right; color: #10b981; font-weight: 600;">${e.yetkazildi?r(e.tolangan_summa):'<span style="color: var(--text-muted); font-size: 0.8rem;">—</span>'}</td>
      <td style="padding: 0.9rem 1rem; text-align: right; font-weight: 700;">
        ${e.yetkazildi?`<span style="color: ${e.jami_narx-e.tolangan_summa>0?"#ef4444":"#10b981"};">${e.jami_narx-e.tolangan_summa>0?"-"+r(e.jami_narx-e.tolangan_summa):"✓"}</span>`:'<span style="color: #818cf8; font-size: 0.78rem;">Qarzga kirmaydi</span>'}
      </td>
      <td style="padding: 0.9rem 1rem; text-align: center; font-size: 0.82rem;">${j(e.kelgan_sana)}</td>
      <td style="padding: 0.9rem 1rem; text-align: center;">${q(e)}</td>
      <td style="padding: 0.9rem 1rem; text-align: center; white-space: nowrap;">
        ${e.yetkazildi?"":`
          <button class="bekor-btn" data-id="${e.id}" title="Zakazni bekor qilish"
            style="background: rgba(239,68,68,0.12); color: #ef4444; border: none; padding: 0.38rem 0.75rem; border-radius: 6px; font-size: 0.78rem; font-weight: 600; cursor: pointer; margin-right: 3px;">
            ✕ Bekor
          </button>
        `}
        ${e.yetkazildi&&e.to_lov_holati!=="toliq"?`
          <button class="tolov-btn" data-id="${e.id}"
            style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none; padding: 0.38rem 0.75rem; border-radius: 6px; font-size: 0.78rem; font-weight: 600; cursor: pointer; margin-right: 3px;">
            💳 To'lov
          </button>
        `:""}
        ${e.yetkazildi&&e.to_lov_holati==="toliq"?`
          <span style="font-size: 0.78rem; color: #10b981;">✅</span>
        `:""}
      </td>
    </tr>
  `,z=e=>{const t=s[e],m=i.dillerlar.find(d=>d.id===e),x=t.jami-t.kutilmoqda,c=x>0?Math.round(t.tolangan/x*100):0,b=t.hisoblar.filter(d=>d.yetkazildi).length,v=t.hisoblar.filter(d=>!d.yetkazildi).length;return`
      <section class="card glass diller-section" style="margin-bottom: 1.5rem; overflow: hidden;" data-diller="${e}">
        <!-- Diller sarlavhasi -->
        <div style="background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08)); padding: 1.2rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 1.1rem; font-weight: 800; color: white; flex-shrink: 0;">
              ${t.diller_ismi.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 style="font-size: 1.05rem; font-weight: 700; margin-bottom: 0.1rem;">${t.diller_ismi}</h2>
              <p style="font-size: 0.78rem; color: var(--text-muted);">${(m==null?void 0:m.kompaniya)||""} ${m!=null&&m.telefon?"• "+m.telefon:""}</p>
            </div>
          </div>
          <div style="display: flex; gap: 1.2rem; flex-wrap: wrap; align-items: center;">
            <div style="text-align: center;">
              <p style="font-size: 0.68rem; color: var(--text-muted); margin-bottom: 0.15rem; text-transform: uppercase;">JAMI</p>
              <p style="font-weight: 800; font-size: 1rem; color: var(--text);">${r(t.jami)}</p>
            </div>
            <div style="text-align: center;">
              <p style="font-size: 0.68rem; color: var(--text-muted); margin-bottom: 0.15rem; text-transform: uppercase;">TO'LANGAN</p>
              <p style="font-weight: 800; font-size: 1rem; color: #10b981;">${r(t.tolangan)}</p>
            </div>
            <div style="text-align: center;">
              <p style="font-size: 0.68rem; color: var(--text-muted); margin-bottom: 0.15rem; text-transform: uppercase;">QARZ</p>
              <p style="font-weight: 800; font-size: 1rem; color: ${t.qarz>0?"#ef4444":"#10b981"};">${t.qarz>0?r(t.qarz):"✓ 0"}</p>
            </div>
            ${t.kutilmoqda>0?`
            <div style="text-align: center;">
              <p style="font-size: 0.68rem; color: var(--text-muted); margin-bottom: 0.15rem; text-transform: uppercase;">OMBORGA KELGAN</p>
              <p style="font-weight: 800; font-size: 1rem; color: #818cf8;">${v} ta</p>
            </div>`:""}
          </div>
        </div>

        <!-- Progress bar va tugmalar -->
        <div style="padding: 0.75rem 1.5rem; background: var(--surface-light); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
          <div style="flex: 1; min-width: 100px; height: 7px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
            <div style="height: 100%; width: ${c}%; background: linear-gradient(to right, #10b981, #6366f1); border-radius: 4px;"></div>
          </div>
          <span style="font-size: 0.78rem; font-weight: 700; color: ${c>=100?"#10b981":"var(--text)"};">${c}%</span>
          <!-- Tarixi tugmasi -->
          <button class="tarixi-btn" data-diller-id="${e}" data-diller-ismi="${t.diller_ismi}"
            style="background: rgba(99,102,241,0.12); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); padding: 0.4rem 0.9rem; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; white-space: nowrap;">
            📋 Tarixi (${b}/${t.hisoblar.length})
          </button>
          <!-- Yangi zakaz -->
          <button class="add-hisob-btn" data-diller-id="${e}" data-diller-ismi="${t.diller_ismi}"
            style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none; padding: 0.4rem 0.9rem; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; white-space: nowrap;">
            + Zakaz
          </button>
          <!-- Hisobni yop (faqat qarz bo'lsa) -->
          ${t.qarz>0?`<button class="yop-diller-btn" data-diller-id="${e}" data-diller-ismi="${t.diller_ismi}" data-qarz="${t.qarz}"
            style="background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 0.4rem 0.9rem; border-radius: 8px; font-size: 0.8rem; font-weight: 700; cursor: pointer; white-space: nowrap;">
            ✅ Hisobni yop — ${r(t.qarz)}
          </button>`:t.qarz===0&&b>0?'<span style="font-size: 0.78rem; font-weight: 700; color: #10b981; white-space: nowrap;">✅ Hisob-kitob yopiq</span>':""}
        </div>

        <!-- Jadval -->
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; min-width: 780px;">
            <thead>
              <tr style="background: rgba(99,102,241,0.05); border-bottom: 1px solid var(--border);">
                <th style="padding: 0.7rem 1.2rem; text-align: left; font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Mebel</th>
                <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Soni</th>
                <th style="padding: 0.7rem 1rem; text-align: right; font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Birlik</th>
                <th style="padding: 0.7rem 1rem; text-align: right; font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Jami</th>
                <th style="padding: 0.7rem 1rem; text-align: right; font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">To'langan</th>
                <th style="padding: 0.7rem 1rem; text-align: right; font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Qarz</th>
                <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Kelgan sana</th>
                <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Holat</th>
                <th style="padding: 0.7rem 1rem; text-align: center; font-size: 0.75rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Amallar</th>
              </tr>
            </thead>
            <tbody>
              ${t.hisoblar.map($).join("")}
            </tbody>
            <tfoot>
              <tr style="background: rgba(99,102,241,0.05); border-top: 2px solid var(--border);">
                <td colspan="3" style="padding: 0.8rem 1.2rem; font-weight: 700; font-size: 0.88rem;">
                  Jami — ${t.hisoblar.length} ta zakaz
                  ${v>0?`<span style="font-size: 0.75rem; color: #818cf8; margin-left: 0.5rem;">(${v} ta omborga kelgan, qarzga kirmaydi)</span>`:""}
                </td>
                <td style="padding: 0.8rem 1rem; text-align: right; font-weight: 800; color: var(--primary);">${r(t.jami)}</td>
                <td style="padding: 0.8rem 1rem; text-align: right; font-weight: 800; color: #10b981;">${r(t.tolangan)}</td>
                <td style="padding: 0.8rem 1rem; text-align: right; font-weight: 800; color: ${t.qarz>0?"#ef4444":"#10b981"};">${t.qarz>0?"-"+r(t.qarz):"✓"}</td>
                <td colspan="3"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>
    `},S=`
    <div style="text-align: center; padding: 4rem 2rem; color: var(--text-muted);">
      <div style="font-size: 3rem; margin-bottom: 1rem;">📋</div>
      <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">Hozircha hisob-kitoblar yo'q</p>
      <p style="font-size: 0.85rem;">Yangi diller yoki zakaz qo'shing</p>
    </div>
  `;g.innerHTML=`
    <header style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
      <div>
        <h1 style="font-size: 1.8rem; margin-bottom: 0.4rem;">Dillerlardan Comfort Mebel</h1>
        <p style="color: var(--text-muted);">Zakaz va to'lov boshqaruvi • Omborga tushgan mebellar avtomatik qo'shiladi</p>
      </div>
      <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
        <button id="add-diller-btn" style="padding: 0.65rem 1.2rem; border-radius: 10px; border: 1px solid var(--border); background: var(--surface-light); color: var(--text); font-weight: 600; cursor: pointer; font-size: 0.9rem;">👤 Yangi Diller</button>
        <button id="add-global-hisob-btn" class="btn-primary" style="padding: 0.65rem 1.2rem; border-radius: 10px;">+ Zakaz qo'sh</button>
        ${p>0?`<button id="yop-hammasi-btn" style="padding: 0.65rem 1.4rem; border-radius: 10px; background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; font-weight: 700; cursor: pointer; font-size: 0.9rem; box-shadow: 0 4px 15px rgba(16,185,129,0.3);">✅ Barcha hisoblarni yop — ${r(p)}</button>`:""}
      </div>
    </header>

    <!-- Umumiy statistika -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr)); gap: 1.2rem; margin-bottom: 2rem;">
      <div class="card glass" style="padding: 1.2rem; border-left: 3px solid #6366f1;">
        <p style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Jami Summa</p>
        <p style="font-size: 1.5rem; font-weight: 800; color: var(--primary);">${r(E)}</p>
        <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.3rem;">${i.dillerHisoblar.length} ta zakaz</p>
      </div>
      <div class="card glass" style="padding: 1.2rem; border-left: 3px solid #10b981;">
        <p style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">To'langan</p>
        <p style="font-size: 1.5rem; font-weight: 800; color: #10b981;">${r(w)}</p>
        <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.3rem;">${i.dillerHisoblar.filter(e=>e.yetkazildi&&e.to_lov_holati==="toliq").length} ta yopiq</p>
      </div>
      <div class="card glass" style="padding: 1.2rem; border-left: 3px solid #ef4444;">
        <p style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Haqiqiy Qarz</p>
        <p style="font-size: 1.5rem; font-weight: 800; color: ${p>0?"#ef4444":"#10b981"};">${p>0?r(p):"✓ 0"}</p>
        <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.3rem;">Faqat yetkazilgan zakazlar</p>
      </div>
      <div class="card glass" style="padding: 1.2rem; border-left: 3px solid #818cf8;">
        <p style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem;">Omborga Kelgan</p>
        <p style="font-size: 1.5rem; font-weight: 800; color: #818cf8;">${y} ta</p>
        <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.3rem;">Qarzga kirmaydi</p>
      </div>
    </div>

    <!-- Diller jadvallar -->
    <div id="dillerlar-container">
      ${Object.keys(s).length>0?Object.keys(s).map(z).join(""):S}
    </div>
  `,f.appendChild(B),f.appendChild(g),g.addEventListener("click",e=>{const t=e.target;if(t.closest("#yop-hammasi-btn")){const d=i.dillerHisoblar.filter(a=>a.yetkazildi&&a.to_lov_holati!=="toliq");if(!d.length)return;confirm(`✅ Barcha ${d.length} ta ochiq hisob yopilsinmi?
Jami: ${r(p)}`)&&(d.forEach(a=>i.updateDillerHisob(a.id,{tolangan_summa:a.jami_narx,to_lov_holati:"toliq"})),u("✅ Barcha hisoblar yopildi! Hisob-kitob nol!"),k());return}const m=t.closest(".tolov-btn");if(m){const d=m.dataset.id,a=i.dillerHisoblar.find(l=>l.id===d),n=a.jami_narx-a.tolangan_summa,h=`
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div style="padding: 1rem; background: rgba(99,102,241,0.08); border-radius: 10px; border: 1px solid rgba(99,102,241,0.2);">
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Mebel: <strong>${a.mebel_nomi} — ${a.modeli}</strong></p>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Jami: <strong style="color: var(--primary);">${r(a.jami_narx)}</strong></p>
            <p style="font-size: 0.85rem; color: var(--text-muted);">Qolgan qarz: <strong style="color: #ef4444;">${r(n)}</strong></p>
          </div>
          <div>
            <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">To'lov summasi (USD)</label>
            <input type="number" id="tolov-summa" value="${n}" max="${n}" min="1" step="0.01"
              style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text); font-size: 1rem; font-weight: 600;">
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button type="button" class="quick-sum" data-val="${n}" style="flex: 1; padding: 0.5rem; background: rgba(16,185,129,0.12); color: #10b981; border: 1px solid rgba(16,185,129,0.3); border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.82rem;">To'liq ${r(n)}</button>
            <button type="button" class="quick-sum" data-val="${Math.round(n/2)}" style="flex: 1; padding: 0.5rem; background: rgba(99,102,241,0.1); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.82rem;">Yarmi ${r(Math.round(n/2))}</button>
          </div>
        </div>`;H("💳 To'lov qilish",h,()=>{const l=Number(document.getElementById("tolov-summa").value);if(l>0&&l<=n){const _=a.tolangan_summa+l;i.updateDillerHisob(d,{tolangan_summa:_,to_lov_holati:_>=a.jami_narx?"toliq":_>0?"qisman":"kutilmoqda"}),u(`✅ ${r(l)} to'lov qilindi!`),k()}else u("Noto'g'ri summa!","error")}),setTimeout(()=>{document.querySelectorAll(".quick-sum").forEach(l=>{l.addEventListener("click",()=>{document.getElementById("tolov-summa").value=l.dataset.val})})},100);return}const x=t.closest(".bekor-btn");if(x){const d=x.dataset.id,a=i.dillerHisoblar.find(n=>n.id===d);confirm(`❌ "${a.mebel_nomi} — ${a.modeli}" (${a.soni} dona) zakazini bekor qilasizmi?
Ombordagi soni ham kamaytiriladi.`)&&(i.cancelDillerHisob(d),u("Zakaz bekor qilindi. Ombordagi soni yangilandi."),k());return}const c=t.closest(".yop-diller-btn");if(c){const d=c.dataset.dillerId,a=c.dataset.dillerIsmi,n=Number(c.dataset.qarz),h=i.dillerHisoblar.filter(l=>l.diller_id===d&&l.yetkazildi&&l.to_lov_holati!=="toliq");confirm(`✅ ${a} bilan hisob-kitob yopilsinmi?
Jami qarz: ${r(n)}`)&&(h.forEach(l=>i.updateDillerHisob(l.id,{tolangan_summa:l.jami_narx,to_lov_holati:"toliq"})),u(`✅ ${a} bilan hisob-kitob yopildi!`),k());return}const b=t.closest(".tarixi-btn");if(b){const d=b.dataset.dillerId,a=b.dataset.dillerIsmi,n=i.dillerHisoblar.filter(o=>o.diller_id===d),h=n.filter(o=>o.yetkazildi),l=n.filter(o=>!o.yetkazildi),_=`
        <div style="display: flex; flex-direction: column; gap: 1rem; max-height: 60vh; overflow-y: auto; padding-right: 0.5rem;">
          ${h.length>0?`
            <div>
              <h3 style="font-size: 0.82rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem;">✅ Yetkazilgan zakazlar (${h.length} ta)</h3>
              ${h.map(o=>`
                <div style="padding: 0.9rem 1rem; background: rgba(16,185,129,0.06); border: 1px solid rgba(16,185,129,0.15); border-radius: 10px; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;">
                  <div>
                    <div style="font-weight: 600; font-size: 0.92rem;">${o.mebel_nomi} — ${o.modeli}</div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem;">
                      ${o.soni} dona • Kelgan: ${j(o.kelgan_sana)}
                      ${o.yetkazildi_sana?` • Yetkazildi: ${j(o.yetkazildi_sana)}`:""}
                    </div>
                  </div>
                  <div style="text-align: right;">
                    <div style="font-weight: 800; color: var(--primary);">${r(o.jami_narx)}</div>
                    <div style="font-size: 0.78rem; color: ${o.to_lov_holati==="toliq"?"#10b981":"#f59e0b"}; margin-top: 0.2rem;">
                      ${o.to_lov_holati==="toliq"?"✅ To'liq to'langan":`⏳ ${r(o.tolangan_summa)} to'langan`}
                    </div>
                  </div>
                </div>
              `).join("")}
            </div>
          `:""}
          ${l.length>0?`
            <div>
              <h3 style="font-size: 0.82rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem;">⏳ Omborga kelgan (${l.length} ta) — qarzga kirmaydi</h3>
              ${l.map(o=>`
                <div style="padding: 0.9rem 1rem; background: rgba(99,102,241,0.06); border: 1px solid rgba(99,102,241,0.15); border-radius: 10px; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;">
                  <div>
                    <div style="font-weight: 600; font-size: 0.92rem;">${o.mebel_nomi} — ${o.modeli}</div>
                    <div style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.2rem;">${o.soni} dona • Kelgan: ${j(o.kelgan_sana)}</div>
                  </div>
                  <div style="font-weight: 800; color: #818cf8;">${r(o.jami_narx)}</div>
                </div>
              `).join("")}
            </div>
          `:""}
          ${n.length===0?`<p style="color: var(--text-muted); text-align: center; padding: 2rem;">Hali zakazlar yo'q</p>`:""}
        </div>
      `;H(`📋 ${a} — Zakazlar Tarixi`,_,()=>{});return}const v=t.closest(".add-hisob-btn");if(v){T(v.dataset.dillerId);return}}),(I=document.getElementById("add-diller-btn"))==null||I.addEventListener("click",()=>{H("👤 Yangi Diller",`
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div><label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Ismi *</label>
          <input type="text" id="d-ismi" placeholder="Diller ismi" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);"></div>
        <div><label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Kompaniya nomi</label>
          <input type="text" id="d-kompaniya" placeholder="Kompaniya" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);"></div>
        <div><label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Telefon</label>
          <input type="text" id="d-tel" value="+998 " style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);"></div>
        <div><label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Manzil</label>
          <input type="text" id="d-manzil" placeholder="Shahar, tuman" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);"></div>
        <div style="padding: 0.75rem 1rem; background: rgba(99,102,241,0.08); border-radius: 10px; border: 1px solid rgba(99,102,241,0.2); font-size: 0.8rem; color: var(--text-muted);">
          🔐 Diller tizimga kirish uchun login/parol
        </div>
        <div style="display: flex; gap: 1rem;">
          <div style="flex: 1;"><label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Login *</label>
            <input type="text" id="d-login" placeholder="masalan: bobur" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);"></div>
          <div style="flex: 1;"><label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Parol *</label>
            <input type="text" id="d-parol" placeholder="masalan: 1234" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);"></div>
        </div>
      </div>`,()=>{const t=document.getElementById("d-ismi").value.trim(),m=document.getElementById("d-kompaniya").value.trim(),x=document.getElementById("d-tel").value.trim(),c=document.getElementById("d-manzil").value.trim(),b=document.getElementById("d-login").value.trim(),v=document.getElementById("d-parol").value.trim();t&&b&&v?(i.addDiller({ismi:t,kompaniya:m,telefon:x,manzil:c,login:b,parol:v}),u(`✅ ${t} qo'shildi! Login: ${b}`),k()):u("Ismi, login va parol majburiy!","error")})}),(D=document.getElementById("add-global-hisob-btn"))==null||D.addEventListener("click",()=>{if(i.dillerlar.length===0){u("Avval diller qo'shing!","error");return}T(i.dillerlar[0].id)})};function T(f){const B=`
    <div style="display: flex; flex-direction: column; gap: 1rem;">
      <div style="padding: 0.8rem 1rem; background: rgba(99,102,241,0.08); border-radius: 10px; border: 1px solid rgba(99,102,241,0.15); font-size: 0.82rem; color: var(--text-muted);">
        📦 Zakaz qo'shilganda mebel <strong style="color: var(--text);">avtomatik ombordaga qo'shiladi</strong>
      </div>
      <div>
        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Diller *</label>
        <select id="h-diller" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
          ${i.dillerlar.map(g=>`<option value="${g.id}" ${g.id===f?"selected":""}>${g.ismi} — ${g.kompaniya}</option>`).join("")}
        </select>
      </div>
      <div style="display: flex; gap: 1rem;">
        <div style="flex: 1;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Mebel nomi *</label>
          <input type="text" id="h-nomi" value="Comfort" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div style="flex: 1;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Modeli *</label>
          <input type="text" id="h-modeli" placeholder="Divan, Kreslo..." style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
      </div>
      <div style="display: flex; gap: 1rem;">
        <div style="flex: 1;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Soni (dona) *</label>
          <input type="number" id="h-soni" value="1" min="1" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div style="flex: 1;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Birlik narxi (USD) *</label>
          <input type="number" id="h-narxi" value="800" min="0" step="0.01" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
      </div>
      <div style="display: flex; gap: 1rem;">
        <div style="flex: 1;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Kelgan sana *</label>
          <input type="date" id="h-sana" value="${new Date().toISOString().split("T")[0]}" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div style="flex: 1;">
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Boshlang'ich to'lov (USD)</label>
          <input type="number" id="h-tolov" value="0" min="0" step="0.01" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
      </div>
    </div>
  `;H("📦 Yangi Zakaz Qo'shish",B,()=>{const g=document.getElementById("h-diller").value,E=i.dillerlar.find(z=>z.id===g),w=document.getElementById("h-nomi").value.trim(),p=document.getElementById("h-modeli").value.trim(),y=Number(document.getElementById("h-soni").value),s=Number(document.getElementById("h-narxi").value),q=document.getElementById("h-sana").value,$=Math.min(Number(document.getElementById("h-tolov").value),y*s);if(w&&p&&y>0&&s>0&&q){const z=y*s;i.addDillerHisob({diller_id:g,diller_ismi:E.ismi,mebel_nomi:w,modeli:p,soni:y,birlik_narxi:s,jami_narx:z,kelgan_sana:q,to_lov_holati:$>=z?"toliq":$>0?"qisman":"kutilmoqda",tolangan_summa:$,yetkazildi:!1}),u(`✅ Zakaz qo'shildi! ${w} ${p} (${y} dona) ombordaga avtomatik qo'shildi.`),k()}else u("Iltimos, barcha maydonlarni to'ldiring!","error")})}export{k as renderDillerlar};
