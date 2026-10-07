import axios from 'axios';

export const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const api = axios.create({ baseURL: API_BASE, withCredentials: true, timeout: 120000 });
api.interceptors.request.use((config) => {
  const user = JSON.parse(localStorage.getItem('aidso-user') || 'null');
  if (user?.refreshToken) config.headers.Authorization = `Bearer ${user.refreshToken}`;
  return config;
});
export const errorMessage = (error) => {
  const detail = error.response?.data?.detail;
  return typeof detail === 'string' ? detail : error.message || 'Request failed';
};
export async function downloadFile(path, filename) {
  const response = await api.get(path, { responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export default api;
