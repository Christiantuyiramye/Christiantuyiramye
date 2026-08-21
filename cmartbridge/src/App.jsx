import { useState } from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { LangContext } from './i18n.js'
import { FxContext } from './fx.js'
import { CartContext } from './cart.js'
import { useFxRate } from './hooks/useFxRate.js'
import { useCartState } from './hooks/useCartState.js'
import { useScrollToTop } from './hooks/useScrollToTop.js'
import Header from './components/Header.jsx'
import Footer from './components/Footer.jsx'
import Home from './pages/Home.jsx'
import ProductPage from './pages/ProductPage.jsx'
import CartPage from './pages/CartPage.jsx'
import CheckoutPage from './pages/CheckoutPage.jsx'
import OrderConfirmationPage from './pages/OrderConfirmationPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'

function Shell() {
  useScrollToTop()

  return (
    <>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/product/:id" element={<ProductPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/order-confirmation" element={<OrderConfirmationPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
      <Footer />
    </>
  )
}

export default function App() {
  const [lang, setLang] = useState('en')
  const fx = useFxRate()
  const cart = useCartState()

  return (
    <BrowserRouter>
      <FxContext.Provider value={fx}>
        <LangContext.Provider value={{ lang, setLang }}>
          <CartContext.Provider value={cart}>
            <Shell />
          </CartContext.Provider>
        </LangContext.Provider>
      </FxContext.Provider>
    </BrowserRouter>
  )
}
