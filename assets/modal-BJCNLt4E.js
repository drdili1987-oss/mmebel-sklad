import{c as n}from"./helpers-DZ8h-Pb2.js";const m=(d,i,l)=>{var a,o;const e=n("div","modal-overlay");e.style.cssText=`
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  `;const t=n("div","card glass");t.style.cssText=`
    width: 90%;
    max-width: 500px;
    padding: 2rem;
    position: relative;
    animation: modalAppear 0.3s ease;
  `,t.innerHTML=`
    <h2 style="margin-bottom: 1.5rem; font-size: 1.3rem;">${d}</h2>
    <div id="modal-body">${i}</div>
    <div style="display: flex; justify-content: flex-end; gap: 1rem; margin-top: 2rem;">
      <button id="modal-cancel" style="padding: 0.6rem 1.2rem; background: var(--surface-light); color: var(--text);">Bekor qilish</button>
      <button id="modal-confirm" class="btn-primary" style="padding: 0.6rem 1.2rem;">Saqlash</button>
    </div>
  `,e.appendChild(t),document.body.appendChild(e);const r=document.createElement("style");return r.innerHTML=`
    @keyframes modalAppear {
      from { opacity: 0; transform: translateY(20px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `,document.head.appendChild(r),(a=e.querySelector("#modal-cancel"))==null||a.addEventListener("click",()=>e.remove()),(o=e.querySelector("#modal-confirm"))==null||o.addEventListener("click",()=>{l(),e.remove()}),e};export{m as r};
