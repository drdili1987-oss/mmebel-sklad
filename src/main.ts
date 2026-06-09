import './styles/index.css';
import './router';

// Service Worker (PWA) registration
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(reg => console.log('SW registratsiya qilindi:', reg))
      .catch(err => console.log('SW xatolik:', err));
  });
}

console.log('MMebel Sklad ilovasi ishga tushdi');
