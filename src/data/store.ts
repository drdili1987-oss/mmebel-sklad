// Mebel Sklad - Local Store (Mock Data)

export interface Mebel {
  id: string;
  nomi: string;
  modeli: string;
  narxi: number;
  valyuta: 'UZS' | 'USD';
  soni: number;
  status: 'sotuvda' | 'tugagan' | 'kam_qoldi';
  yaratilgan: string;
}

export interface Buyurtma {
  id: string;
  mijoz_ismi: string;
  mijoz_telefon: string;
  mahsulot_id: string;
  mahsulot_nomi: string;
  miqdori: number;
  jami_narx: number;
  sana: string;
  tayyor_sana: string;
  status: 'tayyorlanmoqda' | 'tayyor' | 'yetkazildi';
  chegirma?: number;       // Chegirma summasi (dollar)
  ozi_olib_ketdi?: boolean; // Mijoz ozi olib ketdimi
}

class Store {
  private static instance: Store;
  
  mebellar: Mebel[] = [
    { id: '1', nomi: 'Jackson', modeli: 'Oshxona to\'plami', narxi: 1200, valyuta: 'USD', soni: 5, status: 'sotuvda', yaratilgan: new Date().toISOString() },
    { id: '2', nomi: 'Afrosiyob', modeli: 'Spalniy', narxi: 15000000, valyuta: 'UZS', soni: 2, status: 'kam_qoldi', yaratilgan: new Date().toISOString() },
    { id: '3', nomi: 'Comfort', modeli: 'Divan', narxi: 800, valyuta: 'USD', soni: 0, status: 'tugagan', yaratilgan: new Date().toISOString() },
  ];

  buyurtmalar: Buyurtma[] = [
    { id: 'b1', mijoz_ismi: 'Ali Valiyev', mijoz_telefon: '+998 90 123 45 67', mahsulot_id: '1', mahsulot_nomi: 'Jackson', miqdori: 1, jami_narx: 1200, sana: new Date().toISOString(), tayyor_sana: '2026-04-25', status: 'tayyorlanmoqda' },
  ];

  user: { isLoggedIn: boolean; role: string } | null = null;

  constructor() {
    this.loadFromStorage();
  }

  static getInstance(): Store {
    if (!Store.instance) {
      Store.instance = new Store();
    }
    return Store.instance;
  }

  private loadFromStorage() {
    const savedMebellar = localStorage.getItem('mmebel_mebellar');
    const savedBuyurtmalar = localStorage.getItem('mmebel_buyurtmalar');
    const savedUser = localStorage.getItem('mmebel_user');

    if (savedMebellar) this.mebellar = JSON.parse(savedMebellar);
    if (savedBuyurtmalar) this.buyurtmalar = JSON.parse(savedBuyurtmalar);
    if (savedUser) this.user = JSON.parse(savedUser);
  }

  private saveToStorage() {
    localStorage.setItem('mmebel_mebellar', JSON.stringify(this.mebellar));
    localStorage.setItem('mmebel_buyurtmalar', JSON.stringify(this.buyurtmalar));
    localStorage.setItem('mmebel_user', JSON.stringify(this.user));
  }

  // Auth
  login(user: { role: string }) {
    this.user = { isLoggedIn: true, role: user.role };
    this.saveToStorage();
  }

  logout() {
    this.user = null;
    this.saveToStorage();
  }

  // Mebellar CRUD
  addMebel(mebel: Omit<Mebel, 'id' | 'yaratilgan'>) {
    const newMebel: Mebel = {
      ...mebel,
      id: Math.random().toString(36).substr(2, 9),
      yaratilgan: new Date().toISOString(),
    };
    this.mebellar.push(newMebel);
    this.saveToStorage();
    return newMebel;
  }

  updateMebel(id: string, updates: Partial<Mebel>) {
    const index = this.mebellar.findIndex(m => m.id === id);
    if (index !== -1) {
      this.mebellar[index] = { ...this.mebellar[index], ...updates };
      this.saveToStorage();
    }
  }

  // Buyurtmalar CRUD
  addBuyurtma(zakaz: Omit<Buyurtma, 'id' | 'sana'>) {
    const newZakaz: Buyurtma = {
      ...zakaz,
      id: Math.random().toString(36).substr(2, 9),
      sana: new Date().toISOString(),
    };
    this.buyurtmalar.push(newZakaz);
    
    // Skladni yangilash
    const mebel = this.mebellar.find(m => m.id === zakaz.mahsulot_id);
    if (mebel) {
      const yangiSoni = mebel.soni - zakaz.miqdori;
      this.updateMebel(mebel.id, { 
        soni: yangiSoni, 
        status: yangiSoni <= 0 ? 'tugagan' : (yangiSoni <= 3 ? 'kam_qoldi' : 'sotuvda')
      });
    }

    this.saveToStorage();
    return newZakaz;
  }
}

export const store = Store.getInstance();
