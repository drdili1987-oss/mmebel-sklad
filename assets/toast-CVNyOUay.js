import{c as a}from"./helpers-aSlk4OZi.js";const i=(e,t="success")=>{const s=a("div","toast glass"),r=t==="success"?"var(--success)":t==="error"?"var(--danger)":"var(--primary)";s.style.cssText=`
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    padding: 1rem 2rem;
    background: ${r};
    color: white;
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    z-index: 2000;
    transition: all 0.3s ease;
    transform: translateY(100px);
    opacity: 0;
  `,s.innerText=e,document.body.appendChild(s),setTimeout(()=>{s.style.transform="translateY(0)",s.style.opacity="1"},10),setTimeout(()=>{s.style.transform="translateY(100px)",s.style.opacity="0",setTimeout(()=>s.remove(),300)},3e3)};export{i as s};
