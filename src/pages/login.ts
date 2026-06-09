import { store } from '../data/store';
import { router } from '../router';

export const renderLogin = () => {
  const app = document.getElementById('app')!;
  app.innerHTML = `
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
  `;

  const form = document.getElementById('login-form') as HTMLFormElement;
  const errorDiv = document.getElementById('login-error')!;

  form.onsubmit = (e) => {
    e.preventDefault();
    const user = (document.getElementById('username') as HTMLInputElement).value;
    const pass = (document.getElementById('password') as HTMLInputElement).value;

    if (user === 'admin' && pass === 'admin123') {
      store.login({ role: 'admin' });
      router.navigate('/dashboard');
    } else {
      errorDiv.style.display = 'block';
    }
  };
};
