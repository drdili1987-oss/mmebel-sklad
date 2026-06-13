import{s as o,r as l}from"./index-DakUwRTP.js";const s=()=>{var t;const a=document.createElement("aside");a.className="glass",a.style.cssText=`
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: var(--sidebar-width);
    padding: 2rem 1.5rem;
    display: flex;
    flex-direction: column;
    z-index: 100;
  `;const e=[{label:"Asosiy",route:"/dashboard",icon:"M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"},{label:"Sklad",route:"/sklad",icon:"M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"},{label:"Buyurtmalar",route:"/buyurtmalar",icon:"M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 0h6"},{label:"Dillerlar",route:"/dillerlar",icon:"M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"},{label:"Statistika",route:"/statistika",icon:"M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"}],n=window.location.hash.slice(1)||"/dashboard";return a.innerHTML=`
    <div style="margin-bottom: 3rem;">
      <h2 style="font-size: 1.5rem; color: var(--primary); font-weight: 700;">MMEBEL</h2>
    </div>
    
    <nav style="flex: 1;">
      <ul style="display: flex; flex-direction: column; gap: 0.5rem;">
        ${e.map(r=>`
          <li>
            <a href="#${r.route}" class="nav-link ${n===r.route?"active":""}" style="
              display: flex;
              align-items: center;
              gap: 1rem;
              padding: 0.8rem 1rem;
              border-radius: var(--radius);
              color: ${n===r.route?"white":"var(--text-muted)"};
              background: ${n===r.route?"var(--primary)":"transparent"};
              transition: all 0.2s ease;
            ">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="${r.icon}"></path>
              </svg>
              <span>${r.label}</span>
            </a>
          </li>
        `).join("")}
      </ul>
    </nav>
    
    <button id="logout-btn" style="
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.8rem 1rem;
      border-radius: var(--radius);
      color: var(--danger);
      background: transparent;
      margin-top: auto;
      width: 100%;
      text-align: left;
    ">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
      </svg>
      <span>Chiqish</span>
    </button>
  `,(t=a.querySelector("#logout-btn"))==null||t.addEventListener("click",()=>{o.logout(),l.navigate("/login")}),a},m=(a,e)=>e==="USD"?new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(a):new Intl.NumberFormat("uz-UZ",{style:"currency",currency:"UZS",maximumFractionDigits:0}).format(a),c=a=>new Date(a).toLocaleDateString("uz-UZ",{day:"numeric",month:"long",year:"numeric"}),d=(a,e,n)=>{const t=document.createElement(a);return e&&(t.className=e),t};export{c as a,d as c,m as f,s as r};
