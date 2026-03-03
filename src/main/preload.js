const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 文件操作
  selectFile: () => ipcRenderer.invoke('select-file'),

  // 应用信息
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),

  // 开发者工具
  openDevTools: () => ipcRenderer.invoke('open-devtools'),

  // 后端状态
  getBackendStatus: () => ipcRenderer.invoke('get-backend-status'),

  // 平台信息
  platform: process.platform,

  // 环境
  isDev: process.env.NODE_ENV === 'development'
});
