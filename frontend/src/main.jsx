import React from 'react'
import ReactDOM from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
    <Toaster
      position="bottom-right"
      toastOptions={{
        style: {
          background: '#11111c',
          color: '#e8e8f0',
          border: '1px solid #1e1e2e',
          fontFamily: 'DM Sans, sans-serif',
          fontSize: '13px',
        },
      }}
    />
  </React.StrictMode>
)
