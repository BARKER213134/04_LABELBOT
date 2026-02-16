import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Admin credentials - stored in sessionStorage after login
let adminAuth = null;

export const setAdminAuth = (username, password) => {
  adminAuth = btoa(`${username}:${password}`);
  sessionStorage.setItem('adminAuth', adminAuth);
};

export const getAdminAuth = () => {
  if (!adminAuth) {
    adminAuth = sessionStorage.getItem('adminAuth');
  }
  return adminAuth;
};

export const clearAdminAuth = () => {
  adminAuth = null;
  sessionStorage.removeItem('adminAuth');
};

export const isAdminLoggedIn = () => {
  return !!getAdminAuth();
};

// Create axios instance for admin requests
const adminAxios = axios.create();
adminAxios.interceptors.request.use((config) => {
  const auth = getAdminAuth();
  if (auth) {
    config.headers.Authorization = `Basic ${auth}`;
  }
  return config;
});

adminAxios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAdminAuth();
      window.location.reload();
    }
    return Promise.reject(error);
  }
);

export const ordersAPI = {
  createOrder: async (orderData) => {
    const response = await axios.post(`${API}/orders/create`, orderData);
    return response.data;
  },
  
  getOrders: async (params = {}) => {
    const response = await axios.get(`${API}/orders/`, { params });
    return response.data;
  },
  
  getOrder: async (orderId) => {
    const response = await axios.get(`${API}/orders/${orderId}`);
    return response.data;
  },
  
  // Admin protected endpoints
  getAdminOrders: async (params = {}) => {
    const response = await adminAxios.get(`${API}/orders/admin/list`, { params });
    return response.data;
  },
  
  getStatistics: async () => {
    const response = await adminAxios.get(`${API}/orders/admin/statistics`);
    return response.data;
  },
};

export const adminAPI = {
  login: async (username, password) => {
    setAdminAuth(username, password);
    try {
      const response = await adminAxios.get(`${API}/admin/api-config`);
      return response.data;
    } catch (error) {
      clearAdminAuth();
      throw error;
    }
  },
  
  getConfig: async () => {
    const response = await adminAxios.get(`${API}/admin/api-config`);
    return response.data;
  },
  
  updateConfig: async (config) => {
    const response = await adminAxios.post(`${API}/admin/api-config`, config);
    return response.data;
  },
  
  // Maintenance mode
  getMaintenanceStatus: async () => {
    const response = await adminAxios.get(`${API}/admin/maintenance`);
    return response.data;
  },
  
  enableMaintenance: async () => {
    const response = await adminAxios.post(`${API}/admin/maintenance/enable`);
    return response.data;
  },
  
  disableMaintenance: async () => {
    const response = await adminAxios.post(`${API}/admin/maintenance/disable`);
    return response.data;
  },
};

export const statisticsAPI = {
  getStatistics: async () => {
    const response = await axios.get(`${API}/statistics/`);
    return response.data;
  },
};

export default {
  orders: ordersAPI,
  admin: adminAPI,
  statistics: statisticsAPI,
};
