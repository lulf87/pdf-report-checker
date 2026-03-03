const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

// 保持全局引用，防止垃圾回收
let mainWindow;
let pythonProcess = null;

// Python后端路径
const isDev = process.env.NODE_ENV === 'development';
const PYTHON_BACKEND_PATH = isDev
  ? path.join(__dirname, '../../python_backend')
  : path.join(process.resourcesPath, 'python_backend');

// 启动Python后端服务
function startPythonBackend() {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const scriptPath = path.join(PYTHON_BACKEND_PATH, 'main.py');

  console.log('Starting Python backend...');
  console.log('Script path:', scriptPath);

  pythonProcess = spawn(pythonCmd, ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000'], {
    cwd: PYTHON_BACKEND_PATH,
    stdio: 'pipe'
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python] ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python Error] ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
    pythonProcess = null;
  });

  pythonProcess.on('error', (err) => {
    console.error('Failed to start Python process:', err);
  });
}

// 停止Python后端服务
function stopPythonBackend() {
  if (pythonProcess) {
    console.log('Stopping Python backend...');
    if (process.platform === 'win32') {
      spawn('taskkill', ['/pid', pythonProcess.pid, '/f', '/t']);
    } else {
      pythonProcess.kill('SIGTERM');
    }
    pythonProcess = null;
  }
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    title: '报告审核工具',
    show: true
  });

  // 加载页面
  if (isDev) {
    // 开发模式：等待React开发服务器
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // 生产模式：加载打包后的文件
    mainWindow.loadFile(path.join(__dirname, '../renderer/dist/index.html'));
  }

  // 确保窗口显示并聚焦
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
    if (process.platform === 'darwin') {
      app.focus({ steal: true });
    }
  });

  // 窗口加载完成后确保在前台
  mainWindow.webContents.on('did-finish-load', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// 应用就绪
app.whenReady().then(() => {
  // 开发模式下启动Python后端
  if (isDev) {
    // Python后端由npm脚本启动，这里不重复启动
  } else {
    startPythonBackend();
  }

  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 应用退出前清理
app.on('before-quit', () => {
  stopPythonBackend();
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC通信处理

// 选择文件
ipcMain.handle('select-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: '报告文件', extensions: ['pdf', 'docx'] },
      { name: 'PDF文件', extensions: ['pdf'] },
      { name: 'Word文档', extensions: ['docx'] },
      { name: '所有文件', extensions: ['*'] }
    ]
  });
  return result;
});

// 获取应用版本
ipcMain.handle('get-app-version', () => {
  return app.getVersion();
});

// 打开开发者工具
ipcMain.handle('open-devtools', () => {
  if (mainWindow) {
    mainWindow.webContents.openDevTools();
  }
});

// 获取Python后端状态
ipcMain.handle('get-backend-status', async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/health');
    return { running: response.ok };
  } catch (error) {
    return { running: false, error: error.message };
  }
});
