import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

if (process.env.NODE_ENV === 'development') require('./mocks');

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
