import { store } from './data/store';

export type Route = '/login' | '/dashboard' | '/sklad' | '/buyurtmalar' | '/statistika';

class Router {
  private routes: Record<Route, () => void> = {
    '/login': () => import('./pages/login').then(m => m.renderLogin()),
    '/dashboard': () => import('./pages/dashboard').then(m => m.renderDashboard()),
    '/sklad': () => import('./pages/sklad').then(m => m.renderSklad()),
    '/buyurtmalar': () => import('./pages/buyurtmalar').then(m => m.renderBuyurtmalar()),
    '/statistika': () => import('./pages/statistika').then(m => m.renderStatistika()),
  };

  constructor() {
    window.addEventListener('hashchange', () => this.handleRoute());
    window.addEventListener('load', () => this.handleRoute());
  }

  private handleRoute() {
    let hash = window.location.hash.slice(1) as Route;
    if (!hash) hash = '/dashboard';

    // Auth check
    if (!store.user?.isLoggedIn && hash !== '/login') {
      window.location.hash = '/login';
      return;
    }

    if (store.user?.isLoggedIn && hash === '/login') {
      window.location.hash = '/dashboard';
      return;
    }

    const render = this.routes[hash];
    if (render) {
      render();
    } else {
      window.location.hash = '/dashboard';
    }
  }

  public navigate(route: Route) {
    window.location.hash = route;
  }
}

export const router = new Router();
