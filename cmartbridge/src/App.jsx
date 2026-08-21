import { useState } from 'react'
import { LangContext } from './i18n.js'
import Header from './components/Header.jsx'
import Hero from './components/Hero.jsx'
import Why from './components/Why.jsx'
import HowItWorks from './components/HowItWorks.jsx'
import Catalog from './components/Catalog.jsx'
import Estimator from './components/Estimator.jsx'
import RequestForm from './components/RequestForm.jsx'
import Prohibited from './components/Prohibited.jsx'
import Terms from './components/Terms.jsx'
import Footer from './components/Footer.jsx'

export default function App() {
  const [lang, setLang] = useState('en')

  return (
    <LangContext.Provider value={{ lang, setLang }}>
      <Header />
      <main>
        <Hero />
        <Why />
        <HowItWorks />
        <Catalog />
        <Estimator />
        <RequestForm />
        <Prohibited />
        <Terms />
      </main>
      <Footer />
    </LangContext.Provider>
  )
}
