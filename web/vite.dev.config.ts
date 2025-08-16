import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001, // nginx経由でアクセスするため、内部的には3001を使用
    host: '0.0.0.0',
    strictPort: true, // ポートが使用中の場合はエラーにする
    // ホットリロードの設定
    hmr: {
      // Browser connects via nginx on 3000 (not 3001)
      clientPort: 3000,
      host: 'localhost',
    },
    // ファイル変更の監視設定
    watch: {
      usePolling: true, // ファイルシステムの監視にポーリングを使用（Docker環境で推奨）
      interval: 100,    // ポーリング間隔（ミリ秒）
    },
    // CORS設定（開発環境で必要な場合）
    cors: true,
    // nginx経由でのアクセスを考慮
    origin: 'http://localhost:3000',
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
