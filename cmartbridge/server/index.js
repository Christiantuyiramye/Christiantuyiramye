import 'dotenv/config'
import express from 'express'
import rateLimit from 'express-rate-limit'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import momoRoutes from './routes.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const distDir = path.join(__dirname, '..', 'dist')

const app = express()
app.disable('x-powered-by')
app.use(express.json({ limit: '10kb' }))

// requestToPay pushes a real payment prompt to someone's phone — must be rate limited.
const payLimiter = rateLimit({
  windowMs: 60 * 1000,
  limit: 5,
  standardHeaders: true,
  legacyHeaders: false,
})

app.use('/api/momo/pay', payLimiter)
app.use('/api', momoRoutes)

// Production: serve the built frontend from the same process (one deployable unit).
if (fs.existsSync(distDir)) {
  app.use(express.static(distDir))
  // Express 5 requires a named wildcard (path-to-regexp v6) — bare '*' throws.
  app.get('/*splat', (req, res) => {
    res.sendFile(path.join(distDir, 'index.html'))
  })
}

const PORT = process.env.PORT || 4000
app.listen(PORT, () => {
  console.log(`CmartBridge API listening on :${PORT}`)
})
