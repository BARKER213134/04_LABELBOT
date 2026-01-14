import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const ordersAPI = {
  createOrder: async (orderData) => {
    const response = await axios.post(`${API}/orders/create`, orderData);
    return response.data;
  },
  
  getOrders: async (params = {}) => {
    const response = await axios.get(`${API}/orders`, { params });
    return response.data;
  },
  
  getOrder: async (orderId) => {
    const response = await axios.get(`${API}/orders/${orderId}`);
    return response.data;
  },
};

export const adminAPI = {
  getConfig: async () => {
    const response = await axios.get(`${API}/admin/api-config`);
    return response.data;
  },
  
  updateConfig: async (config) => {
    const response = await axios.post(`${API}/admin/api-config`, config);
    return response.data;
  },
};

export const statisticsAPI = {
  getStatistics: async () => {
    const response = await axios.get(`${API}/statistics`);
    return response.data;
  },
};

export default {
  orders: ordersAPI,
  admin: adminAPI,
  statistics: statisticsAPI,
};