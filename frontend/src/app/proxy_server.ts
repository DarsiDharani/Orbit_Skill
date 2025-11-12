/**
 * Express Reverse Proxy Server
 * 
 * Purpose: Development proxy server to route requests between Angular frontend and FastAPI backend
 * Features:
 * - Routes /api/* requests to FastAPI backend (port 8000)
 * - Routes all other requests to Angular development server (port 4200)
 * - Enables CORS-free development by proxying requests
 * 
 * Usage:
 * Run this server to access both frontend and backend through a single port (3000)
 * Useful for development when frontend and backend run on different ports
 * 
 * Routes:
 * - /api/* → FastAPI backend (http://127.0.0.1:8000)
 * - /* → Angular dev server (http://127.0.0.1:4200)
 * 
 * @author Orbit Skill Development Team
 * @date 2025
 */

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();

// Target URLs for proxying
const fastapiTarget = 'http://127.0.0.1:8000';  // FastAPI backend
const angularTarget = 'http://127.0.0.1:4200';  // Angular development server

// Proxy API and Swagger docs to FastAPI backend
// All requests to /api/* are forwarded to the FastAPI server
app.use('/api', createProxyMiddleware({
    target: fastapiTarget,
    changeOrigin: true,  // Change origin header to match target
}));

// Proxy all other requests to Angular development server
// This handles all frontend routes and static assets
app.use('/', createProxyMiddleware({
    target: angularTarget,
    changeOrigin: true,  // Change origin header to match target
}));

// Start proxy server on port 3000
// Listen on all interfaces (0.0.0.0) to allow external access
app.listen(3000, '0.0.0.0', () => {
    console.log('Reverse proxy running at http://127.0.0.1:3000');
});