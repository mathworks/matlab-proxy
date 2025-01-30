// Copyright 2025 The MathWorks, Inc.

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    base: './', // To allow the app to be hostable at any endpoint
    build: {
    // Mimicking the structure produced by CRA to avoid changes to matlab-proxy's source code.
        outDir: 'build',
        assetsDir: 'static',
        rollupOptions: {
            output: {
                entryFileNames: 'static/js/[name].[hash].js',
                chunkFileNames: 'static/js/[name].[hash].js',
                assetFileNames: (assetInfo) => {
                    const info = assetInfo.name.split('.');
                    let extType = info[info.length - 1];
                    if (/png|jpe?g|svg|gif|tiff|bmp|ico|woff|woff2|ttf|eot/i.test(extType)) {
                        extType = 'media';
                    }
                    return `static/${extType}/[name].[hash][extname]`;
                },
            },
        },
    },
    plugins: [react()],
    test: {
        globals: true, 
        environment: 'jsdom',
        setupFiles: './src/setupTests.js',
        reporters: 'vitest-teamcity-reporter',
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html', 'lcov', 'teamcity'],
            reportsDirectory: './coverage'
        }
    },
    css: {
        devSourcemap: false
    },
    server: {
        proxy: {
            '/': {
                target: 'http://localhost:8888',
                changeOrigin: true, 
            }
        }
    }
});
