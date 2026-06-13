import{s as l,r as s}from"./index-DK_9OF3L.js";const b=()=>{const m=document.getElementById("app");m.innerHTML=`
    <div style="display: flex; align-items: center; justify-content: center; min-height: 100vh; background: var(--background);">
      <div class="card glass" style="width: 100%; max-width: 420px; padding: 2.5rem; position: relative; overflow: hidden;">

        <!-- Dekorativ gradient -->
        <div style="position: absolute; top: -60px; right: -60px; width: 180px; height: 180px; background: radial-gradient(circle, rgba(99,102,241,0.15), transparent); border-radius: 50%; pointer-events: none;"></div>
        <div style="position: absolute; bottom: -40px; left: -40px; width: 130px; height: 130px; background: radial-gradient(circle, rgba(139,92,246,0.12), transparent); border-radius: 50%; pointer-events: none;"></div>

        <div style="text-align: center; margin-bottom: 2rem; position: relative;">
          <div style="font-size: 2.8rem; margin-bottom: 0.5rem;">🪑</div>
          <h1 style="font-size: 1.7rem; margin-bottom: 0.3rem; background: linear-gradient(to right, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">MMebel Sklad</h1>
          <p style="color: var(--text-muted); font-size: 0.88rem;">Tizimga kirish</p>
        </div>

        <!-- Rol tanlash tablar -->
        <div style="display: flex; gap: 0; background: var(--surface-light); border-radius: 10px; padding: 3px; margin-bottom: 1.5rem;">
          <button id="tab-admin" onclick="switchTab('admin')" style="flex: 1; padding: 0.6rem; border-radius: 8px; border: none; cursor: pointer; font-size: 0.88rem; font-weight: 600; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; transition: all 0.2s;">
            🛡️ Admin
          </button>
          <button id="tab-diller" onclick="switchTab('diller')" style="flex: 1; padding: 0.6rem; border-radius: 8px; border: none; cursor: pointer; font-size: 0.88rem; font-weight: 600; background: transparent; color: var(--text-muted); transition: all 0.2s;">
            👤 Diller
          </button>
        </div>

        <form id="login-form">
          <div style="margin-bottom: 1.2rem;">
            <label style="display: block; margin-bottom: 0.5rem; font-size: 0.88rem; color: var(--text-muted);">Login</label>
            <input type="text" id="username" value="admin" autocomplete="username"
              style="width: 100%; padding: 0.8rem 1rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text); outline: none; font-size: 0.95rem; transition: border-color 0.2s;"
              onfocus="this.style.borderColor='#6366f1'" onblur="this.style.borderColor='var(--border)'" required>
          </div>

          <div style="margin-bottom: 0.5rem;">
            <label style="display: block; margin-bottom: 0.5rem; font-size: 0.88rem; color: var(--text-muted);">Parol</label>
            <input type="password" id="password" value="admin123" autocomplete="current-password"
              style="width: 100%; padding: 0.8rem 1rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text); outline: none; font-size: 0.95rem; transition: border-color 0.2s;"
              onfocus="this.style.borderColor='#6366f1'" onblur="this.style.borderColor='var(--border)'" required>
          </div>

          <!-- Hint -->
          <div id="login-hint" style="margin-bottom: 1.5rem; font-size: 0.78rem; color: var(--text-muted); padding: 0.5rem 0.75rem; background: rgba(99,102,241,0.07); border-radius: 8px; border-left: 2px solid rgba(99,102,241,0.4);">
            Admin: <strong>admin</strong> / <strong>admin123</strong>
          </div>

          <button type="submit" class="btn-primary" style="width: 100%; padding: 0.85rem; font-size: 1rem; font-weight: 700; border-radius: 10px;">
            Kirish →
          </button>
        </form>

        <div id="login-error" style="color: #ef4444; font-size: 0.85rem; margin-top: 1rem; text-align: center; display: none; padding: 0.75rem; background: rgba(239,68,68,0.08); border-radius: 8px; border: 1px solid rgba(239,68,68,0.2);">
          ❌ Login yoki parol noto'g'ri!
        </div>
      </div>
    </div>
  `,window.switchTab=a=>{const r=document.getElementById("tab-admin"),t=document.getElementById("tab-diller"),i=document.getElementById("login-hint"),e=document.getElementById("username"),o=document.getElementById("password");a==="admin"?(r.style.cssText="flex: 1; padding: 0.6rem; border-radius: 8px; border: none; cursor: pointer; font-size: 0.88rem; font-weight: 600; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; transition: all 0.2s;",t.style.cssText="flex: 1; padding: 0.6rem; border-radius: 8px; border: none; cursor: pointer; font-size: 0.88rem; font-weight: 600; background: transparent; color: var(--text-muted); transition: all 0.2s;",i.innerHTML="Admin: <strong>admin</strong> / <strong>admin123</strong>",e.value="admin",o.value="admin123",document.getElementById("login-form").dataset.tab="admin"):(t.style.cssText="flex: 1; padding: 0.6rem; border-radius: 8px; border: none; cursor: pointer; font-size: 0.88rem; font-weight: 600; background: linear-gradient(135deg, #10b981, #059669); color: white; transition: all 0.2s;",r.style.cssText="flex: 1; padding: 0.6rem; border-radius: 8px; border: none; cursor: pointer; font-size: 0.88rem; font-weight: 600; background: transparent; color: var(--text-muted); transition: all 0.2s;",i.innerHTML="Diller logini va parolini kiriting (admin bergan)",e.value="",o.value="",e.focus(),document.getElementById("login-form").dataset.tab="diller"),document.getElementById("login-error").style.display="none"};const n=document.getElementById("login-form");n.dataset.tab="admin";const d=document.getElementById("login-error");n.onsubmit=a=>{a.preventDefault();const r=document.getElementById("username").value.trim(),t=document.getElementById("password").value.trim(),i=n.dataset.tab;if(d.style.display="none",i==="admin")r==="admin"&&t==="admin123"?(l.login({role:"admin"}),s.navigate("/dashboard")):d.style.display="block";else{const e=l.dillerlar.find(o=>o.login===r&&o.parol===t);e?(l.login({role:"diller",diller_id:e.id,diller_ismi:e.ismi}),s.navigate("/diller-panel")):d.style.display="block"}}};export{b as renderLogin};
