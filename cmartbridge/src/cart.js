// Shared cart context — cart state is owned by useCartState() in App.jsx and read
// here by any component, mirroring how fx.js shares the live FX rate.
import { createContext, useContext } from 'react'

export const CartContext = createContext({
  items: [],
  add: () => {},
  setQty: () => {},
  remove: () => {},
  clear: () => {},
  count: 0,
})

export const useCart = () => useContext(CartContext)
