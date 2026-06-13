import{s as o}from"./index-BE7OVh5U.js";import{r as I,c as D,a as E}from"./helpers-DZ8h-Pb2.js";import{r as _}from"./modal-BJCNLt4E.js";import{s as p}from"./toast-BkXjzw36.js";const r=g=>new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(g),u=()=>{var b,w;const g=document.getElementById("app");g.innerHTML="";const q=I(),v=D("main","main-content"),d=o.dillerHisoblar.reduce((e,t)=>e+t.jami_narx,0),f=o.dillerHisoblar.reduce((e,t)=>e+t.tolangan_summa,0),c=d-f,s={};o.dillerHisoblar.forEach(e=>{s[e.diller_id]||(s[e.diller_id]={diller_ismi:e.diller_ismi,jami:0,tolangan:0,qarz:0,hisoblar:[]}),s[e.diller_id].jami+=e.jami_narx,s[e.diller_id].tolangan+=e.tolangan_summa,s[e.diller_id].qarz+=e.jami_narx-e.tolangan_summa,s[e.diller_id].hisoblar.push(e)});const x=e=>e==="toliq"?`<span style="background: rgba(16,185,129,0.15); color: #10b981; padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700;">✅ To'liq to'langan</span>`:e==="qisman"?`<span style="background: rgba(245,158,11,0.15); color: #f59e0b; padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700;">⏳ Qisman to'langan</span>`:'<span style="background: rgba(239,68,68,0.15); color: #ef4444; padding: 0.3rem 0.8rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700;">🔴 Kutilmoqda</span>',y=e=>`
    <tr style="border-bottom: 1px solid var(--border); transition: background 0.15s;" class="hisob-row">
      <td style="padding: 1rem 1.2rem;">
        <div style="font-weight: 600; font-size: 0.95rem;">${e.mebel_nomi}</div>
        <div style="font-size: 0.8rem; color: var(--text-muted);">${e.modeli}</div>
      </td>
      <td style="padding: 1rem; text-align: center;">
        <span style="font-weight: 700; font-size: 1rem;">${e.soni}</span>
        <span style="font-size: 0.75rem; color: var(--text-muted);"> dona</span>
      </td>
      <td style="padding: 1rem; text-align: right; font-weight: 600;">${r(e.birlik_narxi)}</td>
      <td style="padding: 1rem; text-align: right; font-weight: 700; color: var(--primary);">${r(e.jami_narx)}</td>
      <td style="padding: 1rem; text-align: right; color: #10b981; font-weight: 600;">${r(e.tolangan_summa)}</td>
      <td style="padding: 1rem; text-align: right; color: ${e.jami_narx-e.tolangan_summa>0?"#ef4444":"#10b981"}; font-weight: 700;">
        ${e.jami_narx-e.tolangan_summa>0?"-"+r(e.jami_narx-e.tolangan_summa):"✓"}
      </td>
      <td style="padding: 1rem; text-align: center;">${E(e.kelgan_sana)}</td>
      <td style="padding: 1rem; text-align: center;">${x(e.to_lov_holati)}</td>
      <td style="padding: 1rem; text-align: center; white-space: nowrap;">
        ${e.to_lov_holati!=="toliq"?`<button class="tolov-btn" data-id="${e.id}" style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none; padding: 0.4rem 0.9rem; border-radius: 6px; font-size: 0.78rem; font-weight: 600; cursor: pointer; margin-right: 4px; transition: opacity 0.2s;">💳 To'lov</button>`:""}
        <button class="del-hisob-btn" data-id="${e.id}" style="background: rgba(239,68,68,0.12); color: #ef4444; border: none; padding: 0.4rem 0.7rem; border-radius: 6px; font-size: 0.78rem; font-weight: 600; cursor: pointer; transition: opacity 0.2s;">🗑</button>
      </td>
    </tr>
  `,h=e=>{const t=s[e],n=o.dillerlar.find(i=>i.id===e),a=t.jami>0?Math.round(t.tolangan/t.jami*100):0;return`
      <section class="card glass diller-section" style="margin-bottom: 1.5rem; overflow: hidden;" data-diller="${e}">
        <!-- Diller sarlavhasi -->
        <div style="background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(139,92,246,0.08)); padding: 1.3rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="width: 46px; height: 46px; border-radius: 50%; background: linear-gradient(135deg, #6366f1, #8b5cf6); display: flex; align-items: center; justify-content: center; font-size: 1.2rem; font-weight: 800; color: white; flex-shrink: 0;">
              ${t.diller_ismi.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 style="font-size: 1.1rem; font-weight: 700; margin-bottom: 0.15rem;">${t.diller_ismi}</h2>
              <p style="font-size: 0.8rem; color: var(--text-muted);">${(n==null?void 0:n.kompaniya)||""} ${n!=null&&n.telefon?"• "+n.telefon:""}</p>
            </div>
          </div>
          <div style="display: flex; gap: 1.5rem; flex-wrap: wrap;">
            <div style="text-align: center;">
              <p style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.2rem;">JAMI SUMMA</p>
              <p style="font-weight: 800; font-size: 1.05rem; color: var(--text);">${r(t.jami)}</p>
            </div>
            <div style="text-align: center;">
              <p style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.2rem;">TO'LANGAN</p>
              <p style="font-weight: 800; font-size: 1.05rem; color: #10b981;">${r(t.tolangan)}</p>
            </div>
            <div style="text-align: center;">
              <p style="font-size: 0.72rem; color: var(--text-muted); margin-bottom: 0.2rem;">QARZ</p>
              <p style="font-weight: 800; font-size: 1.05rem; color: ${t.qarz>0?"#ef4444":"#10b981"};">${t.qarz>0?r(t.qarz):"✓ Hisob-kitob"}</p>
            </div>
          </div>
        </div>
        <!-- To'lov progressi -->
        <div style="padding: 0.8rem 1.5rem; background: var(--surface-light); border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">
          <div style="flex: 1; min-width: 120px; height: 8px; background: rgba(255,255,255,0.1); border-radius: 4px; overflow: hidden;">
            <div style="height: 100%; width: ${a}%; background: linear-gradient(to right, #10b981, #6366f1); border-radius: 4px; transition: width 0.5s ease;"></div>
          </div>
          <span style="font-size: 0.8rem; font-weight: 700; min-width: 40px; text-align: right; color: ${a===100?"#10b981":"var(--text)"};">${a}%</span>
          <button class="add-hisob-btn" data-diller-id="${e}" data-diller-ismi="${t.diller_ismi}" style="background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; border: none; padding: 0.45rem 1rem; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; white-space: nowrap; transition: opacity 0.2s;">+ Yozuv qo'sh</button>
          ${t.qarz>0?`<button class="yop-diller-btn" data-diller-id="${e}" data-diller-ismi="${t.diller_ismi}" data-qarz="${t.qarz}" style="background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 0.45rem 1rem; border-radius: 8px; font-size: 0.8rem; font-weight: 700; cursor: pointer; white-space: nowrap; transition: opacity 0.2s;">✅ Hisobni yop — ${r(t.qarz)}</button>`:'<span style="font-size: 0.82rem; font-weight: 700; color: #10b981; white-space: nowrap;">✅ Hisob-kitob yopiq</span>'}
        </div>
        <!-- Jadval -->
        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; min-width: 750px;">
            <thead>
              <tr style="background: rgba(99,102,241,0.06); border-bottom: 1px solid var(--border);">
                <th style="padding: 0.8rem 1.2rem; text-align: left; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Mebel nomi</th>
                <th style="padding: 0.8rem 1rem; text-align: center; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Soni</th>
                <th style="padding: 0.8rem 1rem; text-align: right; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Birlik narxi</th>
                <th style="padding: 0.8rem 1rem; text-align: right; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Jami summa</th>
                <th style="padding: 0.8rem 1rem; text-align: right; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">To'langan</th>
                <th style="padding: 0.8rem 1rem; text-align: right; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Qarz</th>
                <th style="padding: 0.8rem 1rem; text-align: center; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Kelgan sana</th>
                <th style="padding: 0.8rem 1rem; text-align: center; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Holat</th>
                <th style="padding: 0.8rem 1rem; text-align: center; font-size: 0.78rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Amallar</th>
              </tr>
            </thead>
            <tbody>
              ${t.hisoblar.map(y).join("")}
            </tbody>
            <tfoot>
              <tr style="background: rgba(99,102,241,0.06); border-top: 2px solid var(--border);">
                <td colspan="3" style="padding: 0.9rem 1.2rem; font-weight: 700; font-size: 0.9rem;">Jami (${t.diller_ismi})</td>
                <td style="padding: 0.9rem 1rem; text-align: right; font-weight: 800; color: var(--primary);">${r(t.jami)}</td>
                <td style="padding: 0.9rem 1rem; text-align: right; font-weight: 800; color: #10b981;">${r(t.tolangan)}</td>
                <td style="padding: 0.9rem 1rem; text-align: right; font-weight: 800; color: ${t.qarz>0?"#ef4444":"#10b981"};">${t.qarz>0?"-"+r(t.qarz):"✓"}</td>
                <td colspan="3"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </section>
    `},z=`
    <div style="text-align: center; padding: 4rem 2rem; color: var(--text-muted);">
      <div style="font-size: 3rem; margin-bottom: 1rem;">📋</div>
      <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">Hozircha hisob-kitoblar yo'q</p>
      <p style="font-size: 0.85rem;">Yangi diller yoki hisob-kitob qo'shing</p>
    </div>
  `;v.innerHTML=`
    <header style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem;">
      <div>
        <h1 style="font-size: 1.8rem; margin-bottom: 0.4rem;">Dillerlardan Comfort Mebel</h1>
        <p style="color: var(--text-muted);">Dillerlar bilan hisob-kitob va to'lov nazorati</p>
      </div>
      <div style="display: flex; gap: 0.75rem; flex-wrap: wrap;">
        <button id="add-diller-btn" class="btn-secondary" style="padding: 0.65rem 1.2rem; border-radius: 10px; border: 1px solid var(--border); background: var(--surface-light); color: var(--text); font-weight: 600; cursor: pointer; font-size: 0.9rem; transition: all 0.2s;">👤 Yangi Diller</button>
        <button id="add-global-hisob-btn" class="btn-primary" style="padding: 0.65rem 1.2rem; border-radius: 10px;">+ Hisob-kitob qo'sh</button>
        ${c>0?`<button id="yop-hammasi-btn" style="padding: 0.65rem 1.4rem; border-radius: 10px; background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; font-weight: 700; cursor: pointer; font-size: 0.9rem; transition: all 0.2s; box-shadow: 0 4px 15px rgba(16,185,129,0.3);">✅ Barcha hisoblarni yop — ${r(c)}</button>`:""}
      </div>
    </header>

    <!-- Umumiy statistika kartalari -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.2rem; margin-bottom: 2rem;">
      <div class="card glass" style="padding: 1.3rem; border-left: 3px solid #6366f1;">
        <p style="font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Jami Summa</p>
        <p style="font-size: 1.6rem; font-weight: 800; color: var(--primary);">${r(d)}</p>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.3rem;">${o.dillerHisoblar.length} ta yozuv</p>
      </div>
      <div class="card glass" style="padding: 1.3rem; border-left: 3px solid #10b981;">
        <p style="font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">To'langan</p>
        <p style="font-size: 1.6rem; font-weight: 800; color: #10b981;">${r(f)}</p>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.3rem;">${d>0?Math.round(f/d*100):0}% to'langan</p>
      </div>
      <div class="card glass" style="padding: 1.3rem; border-left: 3px solid #ef4444;">
        <p style="font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Umumiy Qarz</p>
        <p style="font-size: 1.6rem; font-weight: 800; color: ${c>0?"#ef4444":"#10b981"};">${c>0?r(c):"✓ Hisob-kitob"}</p>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.3rem;">${o.dillerHisoblar.filter(e=>e.to_lov_holati!=="toliq").length} ta ochiq hisob</p>
      </div>
      <div class="card glass" style="padding: 1.3rem; border-left: 3px solid #f59e0b;">
        <p style="font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Dillerlar soni</p>
        <p style="font-size: 1.6rem; font-weight: 800; color: #f59e0b;">${o.dillerlar.length}</p>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 0.3rem;">${Object.keys(s).length} ta faol diller</p>
      </div>
    </div>

    <!-- Diller bo'yicha jadvallar -->
    <div id="dillerlar-container">
      ${Object.keys(s).length>0?Object.keys(s).map(h).join(""):z}
    </div>
  `,g.appendChild(q),g.appendChild(v),v.addEventListener("click",e=>{const t=e.target;if(t.closest("#yop-hammasi-btn")){const a=o.dillerHisoblar.filter(i=>i.to_lov_holati!=="toliq");if(a.length===0)return;confirm(`✅ Barcha ${a.length} ta ochiq hisob yopilsinmi?
Jami: ${r(c)}`)&&(a.forEach(i=>{o.updateDillerHisob(i.id,{tolangan_summa:i.jami_narx,to_lov_holati:"toliq"})}),p("✅ Barcha hisoblar yopildi! Hisob-kitob nol!"),u());return}if(t.classList.contains("tolov-btn")){const a=t.dataset.id,i=o.dillerHisoblar.find(l=>l.id===a),m=i.jami_narx-i.tolangan_summa,k=`
        <div style="display: flex; flex-direction: column; gap: 1rem;">
          <div style="padding: 1rem; background: rgba(99,102,241,0.08); border-radius: 10px; border: 1px solid rgba(99,102,241,0.2);">
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.3rem;">Mebel: <strong style="color: var(--text);">${i.mebel_nomi} — ${i.modeli}</strong></p>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.3rem;">Jami summa: <strong style="color: var(--primary);">${r(i.jami_narx)}</strong></p>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.3rem;">To'langan: <strong style="color: #10b981;">${r(i.tolangan_summa)}</strong></p>
            <p style="font-size: 0.85rem; color: var(--text-muted);">Qolgan qarz: <strong style="color: #ef4444;">${r(m)}</strong></p>
          </div>
          <div>
            <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">To'lov summasi (USD)</label>
            <input type="number" id="tolov-summa" value="${m}" max="${m}" min="1" step="0.01"
              style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text); font-size: 1rem; font-weight: 600;">
          </div>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <button type="button" class="quick-sum" data-val="${m}" style="flex: 1; padding: 0.5rem; background: rgba(16,185,129,0.12); color: #10b981; border: 1px solid rgba(16,185,129,0.3); border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.82rem;">To'liq ${r(m)}</button>
            <button type="button" class="quick-sum" data-val="${Math.round(m/2)}" style="flex: 1; padding: 0.5rem; background: rgba(99,102,241,0.1); color: #818cf8; border: 1px solid rgba(99,102,241,0.2); border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 0.82rem;">Yarmi ${r(Math.round(m/2))}</button>
          </div>
        </div>
      `;_("💳 To'lov qilish",k,()=>{const l=Number(document.getElementById("tolov-summa").value);if(l>0&&l<=m){const $=i.tolangan_summa+l,j=$>=i.jami_narx?"toliq":$>0?"qisman":"kutilmoqda";o.updateDillerHisob(a,{tolangan_summa:$,to_lov_holati:j}),p(`✅ ${r(l)} to'lov qilindi!`),u()}else p("Noto'g'ri summa kiritildi!","error")}),setTimeout(()=>{document.querySelectorAll(".quick-sum").forEach(l=>{l.addEventListener("click",()=>{document.getElementById("tolov-summa").value=l.dataset.val})})},100);return}if(t.classList.contains("del-hisob-btn")){const a=t.dataset.id;confirm("Bu yozuvni o'chirishni tasdiqlaysizmi?")&&(o.deleteDillerHisob(a),p("Yozuv o'chirildi"),u());return}if(t.classList.contains("add-hisob-btn")){const a=t.dataset.dillerId;t.dataset.dillerIsmi,H(a);return}const n=t.closest(".yop-diller-btn");if(n){const a=n.dataset.dillerId,i=n.dataset.dillerIsmi,m=Number(n.dataset.qarz),k=o.dillerHisoblar.filter(l=>l.diller_id===a&&l.to_lov_holati!=="toliq");confirm(`✅ ${i} bilan hisob-kitob yopilsinmi?
Ochiq hisoblar: ${k.length} ta
Jami qarz: ${r(m)}`)&&(k.forEach(l=>{o.updateDillerHisob(l.id,{tolangan_summa:l.jami_narx,to_lov_holati:"toliq"})}),p(`✅ ${i} bilan hisob-kitob yopildi!`),u());return}}),(b=document.getElementById("add-diller-btn"))==null||b.addEventListener("click",()=>{_("👤 Yangi Diller Qo'shish",`
      <div style="display: flex; flex-direction: column; gap: 1rem;">
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Ismi *</label>
          <input type="text" id="d-ismi" placeholder="Diller ismi" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Kompaniya nomi</label>
          <input type="text" id="d-kompaniya" placeholder="Kompaniya nomi" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Telefon raqami</label>
          <input type="text" id="d-tel" value="+998 " style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
        <div>
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Manzil</label>
          <input type="text" id="d-manzil" placeholder="Shahar, tuman" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
        </div>
      </div>
    `,()=>{const t=document.getElementById("d-ismi").value.trim(),n=document.getElementById("d-kompaniya").value.trim(),a=document.getElementById("d-tel").value.trim(),i=document.getElementById("d-manzil").value.trim();t?(o.addDiller({ismi:t,kompaniya:n,telefon:a,manzil:i}),p(`✅ ${t} diller ro'yxatga qo'shildi!`),u()):p("Iltimos, diller ismini kiriting!","error")})}),(w=document.getElementById("add-global-hisob-btn"))==null||w.addEventListener("click",()=>{if(o.dillerlar.length===0){p("Avval diller qo'shing!","error");return}H(o.dillerlar[0].id,o.dillerlar[0].ismi)})};function H(g,q){const v=`
    <div style="display: flex; flex-direction: column; gap: 1rem;">
      <div>
        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Diller *</label>
        <select id="h-diller" style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
          ${o.dillerlar.map(d=>`<option value="${d.id}|${d.ismi}" ${d.id===g?"selected":""}>${d.ismi} — ${d.kompaniya}</option>`).join("")}
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
          <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Soni *</label>
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
      <div>
        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.4rem;">Izoh</label>
        <input type="text" id="h-izoh" placeholder="Ixtiyoriy izoh..." style="width: 100%; padding: 0.7rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text);">
      </div>
    </div>
  `;_("📦 Hisob-kitob Qo'shish",v,()=>{const d=document.getElementById("h-diller").value.split("|"),f=d[0],c=d[1],s=document.getElementById("h-nomi").value.trim(),x=document.getElementById("h-modeli").value.trim(),y=Number(document.getElementById("h-soni").value),h=Number(document.getElementById("h-narxi").value),z=document.getElementById("h-sana").value,b=Number(document.getElementById("h-tolov").value),w=document.getElementById("h-izoh").value.trim();if(s&&x&&y>0&&h>0&&z){const e=y*h,t=b>=e?"toliq":b>0?"qisman":"kutilmoqda";o.addDillerHisob({diller_id:f,diller_ismi:c,mebel_nomi:s,modeli:x,soni:y,birlik_narxi:h,jami_narx:e,kelgan_sana:z,to_lov_holati:t,tolangan_summa:Math.min(b,e),izoh:w||void 0}),p("✅ Hisob-kitob muvaffaqiyatli qo'shildi!"),u()}else p("Iltimos, barcha majburiy maydonlarni to'ldiring!","error")})}export{u as renderDillerlar};
