import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import {NextUIProvider} from '@nextui-org/react'

import './index.css'
import App from './App.jsx'

import React from "react";
import ReactDOM from "react-dom";
import { BrowserRouter } from "react-router-dom";

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
    <NextUIProvider>
    
    <App />
    
    </NextUIProvider>
    </BrowserRouter>
  </StrictMode>,
)
