import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

import { ThemeProvider } from '@mui/material/styles';
import theme from './theme/theme';
import { registerSW } from 'virtual:pwa-register';

// 서비스 워커 등록
registerSW({ immediate: true });

registerSW({
  onNeedRefresh() {
    console.log('새 버전이 있습니다. 새로고침하면 적용됩니다.')
  },
  onOfflineReady() {
    console.log('Care-full 앱이 오프라인 사용 준비를 마쳤습니다.')
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>
);
