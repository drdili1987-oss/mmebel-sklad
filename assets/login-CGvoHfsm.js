import{s as a,r as d}from"./index-DakUwRTP.js";const s=()=>{const e=document.getElementById("app");e.innerHTML=`
    <div class="login-container" style="display: flex; align-items: center; justify-content: center; min-height: 100vh; background: var(--background);">
      <div class="card glass" style="width: 100%; max-width: 400px; padding: 2.5rem;">
        <div style="text-align: center; margin-bottom: 2rem;">
          <h1 style="font-size: 1.8rem; margin-bottom: 0.5rem; background: linear-gradient(to right, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">MMebel Sklad</h1>
          <p style="color: var(--text-muted);">Tizimga kirish</p>
        </div>
        
        <form id="login-form">
          <div style="margin-bottom: 1.5rem;">
            <label style="display: block; margin-bottom: 0.5rem; font-size: 0.9rem; color: var(--text-muted);">Login</label>
            <input type="text" id="username" value="admin" style="width: 100%; padding: 0.8rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text); outline: none;" required>
          </div>
          
          <div style="margin-bottom: 2rem;">
            <label style="display: block; margin-bottom: 0.5rem; font-size: 0.9rem; color: var(--text-muted);">Parol</label>
            <input type="password" id="password" value="admin123" style="width: 100%; padding: 0.8rem; border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface-light); color: var(--text); outline: none;" required>
          </div>
          
          <button type="submit" class="btn-primary" style="width: 100%;">Kirish</button>
        </form>
        
        <div id="login-error" style="color: var(--danger); font-size: 0.85rem; margin-top: 1rem; text-align: center; display: none;">
          Login yoki parol noto'g'ri!
        </div>
      </div>
    </div>
  `;const r=document.getElementById("login-form"),t=document.getElementById("login-error");r.onsubmit=o=>{o.preventDefault();const i=document.getElementById("username").value,n=document.getElementById("password").value;i==="admin"&&n==="admin123"?(a.login({role:"admin"}),d.navigate("/dashboard")):t.style.display="block"}};export{s as renderLogin};
