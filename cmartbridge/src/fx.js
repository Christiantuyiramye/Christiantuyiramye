// Shared live FX rate context — fetched once in App.jsx, read by Catalog and Estimator
// so every door price on the page uses the same KRW→RWF rate.
import { createContext, useContext } from 'react'

export const FxContext = createContext({
  rate: null,
  source: 'fallback',
  updatedAt: null,
  loading: true,
})

export const useFx = () => useContext(FxContext)
