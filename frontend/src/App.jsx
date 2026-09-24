import { useEffect, useState } from 'react'
import './App.css'
import Chat from './Chat'

function App() {
  const [transactions, setTransactions] = useState([])
  const [summary, setSummary] = useState({ total_income: 0, total_expense: 0, balance: 0 })
  const [filter, setFilter] = useState('all')
  const [form, setForm] = useState({
    type: 'expense',
    amount: '',
    category: '',
    description: '',
    date: new Date().toISOString().slice(0, 10),
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [sortBy, setSortBy] = useState('date')
  const [sortDir, setSortDir] = useState('desc')
  const [query, setQuery] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState('')
  const [aiResult, setAiResult] = useState(null)

  useEffect(() => {
    async function loadData() {
      try {
        const [transactionsResponse, summaryResponse] = await Promise.all([
          fetch(`/api/transactions?type=${filter}`),
          fetch('/api/summary'),
        ])

        if (!transactionsResponse.ok || !summaryResponse.ok) {
          throw new Error('API недоступний')
        }

        const transactionsData = await transactionsResponse.json()
        const summaryData = await summaryResponse.json()

        setTransactions(transactionsData)
        setSummary(summaryData)
      } catch (err) {
        console.error(err)
        setError('Не вдалося завантажити дані. Перевірте backend API.')
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [filter])

  async function refreshAll() {
    setLoading(true)
    try {
      const [transactionsResponse, summaryResponse] = await Promise.all([
        fetch(`/api/transactions?type=${filter}`),
        fetch('/api/summary'),
      ])

      const transactionsData = await transactionsResponse.json()
      const summaryData = await summaryResponse.json()

      setTransactions(transactionsData)
      setSummary(summaryData)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  async function runAiAnalysis() {
    setAiLoading(true)
    setAiError('')
    try {
      const resp = await fetch('/api/ai/analyze-transactions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ limit: 200 }) })
      if (!resp.ok) throw new Error('AI endpoint error')
      const data = await resp.json()
      if (!data.ok) throw new Error('AI returned error')
      // Defensive handling: prefer validated parsed object, otherwise show raw text
      if (data.llm && data.llm.parsed) {
        setAiResult(data.llm.parsed)
      } else if (data.llm && data.llm.raw) {
        // try to parse raw JSON if present
        try {
          const parsed = JSON.parse(data.llm.raw)
          setAiResult(parsed)
        } catch {
          setAiResult({ summary: data.llm.raw, categories: [], risks: [], recommendations: [] })
        }
      } else {
        setAiResult({ summary: 'No analysis available', categories: [], risks: [], recommendations: [] })
      }
    } catch (err) {
      console.error(err)
      setAiError(String(err))
    } finally {
      setAiLoading(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()

    try {
      const payload = {
        type: form.type,
        amount: parseFloat(form.amount),
        category: form.category,
        description: form.description,
        date: form.date,
      }

      const resp = await fetch('/api/transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!resp.ok) {
        const err = await resp.json()
        throw new Error(err.detail || 'Помилка створення')
      }

      setForm({ type: 'expense', amount: '', category: '', description: '', date: new Date().toISOString().slice(0,10) })
      await refreshAll()
    } catch (err) {
      console.error(err)
      setError(String(err))
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Ви впевнені, що хочете видалити операцію?')) return

    try {
      const resp = await fetch(`/api/transactions/${id}`, { method: 'DELETE' })
      if (!resp.ok) throw new Error('Не вдалося видалити')
      await refreshAll()
    } catch (err) {
      console.error(err)
      setError('Не вдалося видалити операцію.')
    }
  }

  if (loading) {
    return <div className="container">Завантаження...</div>
  }

  if (error) {
    return <div className="container error">{error}</div>
  }

  const filtered = transactions.filter(t => {
    if (!query) return true
    const q = query.toLowerCase()
    return (t.description || '').toLowerCase().includes(q) || (t.category || '').toLowerCase().includes(q)
  })

  const sorted = [...filtered].sort((a, b) => {
    const dir = sortDir === 'asc' ? 1 : -1

    if (sortBy === 'date') {
      return (new Date(a.date) - new Date(b.date)) * dir
    }

    if (sortBy === 'amount') {
      return (Number(a.amount) - Number(b.amount)) * dir
    }

    if (sortBy === 'type') {
      return a.type.localeCompare(b.type) * dir
    }

    if (sortBy === 'category') {
      const ca = (a.category || '').toLowerCase()
      const cb = (b.category || '').toLowerCase()
      return ca.localeCompare(cb) * dir
    }

    return 0
  })

  const handleSort = (key) => {
    if (sortBy === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortBy(key)
      setSortDir('asc')
    }
  }

  return (
    <main className="container">
      <h1>Фінансовий dashboard</h1>

      <section className="cards">
        <div className="card">
          <h2>Доходи</h2>
          <p>{summary.total_income} грн</p>
        </div>

        <div className="card">
          <h2>Витрати</h2>
          <p>{summary.total_expense} грн</p>
        </div>

        <div className="card">
          <h2>Баланс</h2>
          <p>{summary.balance} грн</p>
        </div>
      </section>

      <section>
        <Chat />
      </section>

      <section>
        <h2>AI Аналіз транзакцій</h2>
        <div>
          <button onClick={runAiAnalysis} disabled={aiLoading}>{aiLoading ? 'Аналіз...' : 'Запустити AI-аналіз'}</button>
          {aiError && <div className="error">{aiError}</div>}
          {aiResult && (
            <div className="ai-result">
              <h3>Резюме</h3>
              <p>{aiResult.summary}</p>

              <h4>Категорії</h4>
              <ul>
                {(aiResult.categories || []).map((c,i)=>(<li key={i}>{c.name}: {c.total}</li>))}
              </ul>

              <h4>Ризики</h4>
              <ul>{(aiResult.risks||[]).map((r,i)=>(<li key={i}>{r}</li>))}</ul>

              <h4>Рекомендації</h4>
              <ul>{(aiResult.recommendations||[]).map((r,i)=>(<li key={i}>{r}</li>))}</ul>
            </div>
          )}
        </div>
      </section>

      <section>
        <h2>Додати операцію</h2>

        <form onSubmit={handleSubmit} className="transaction-form">
          <label>
            Тип:
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
              <option value="income">income</option>
              <option value="expense">expense</option>
            </select>
          </label>

          <label>
            Сума:
            <input type="number" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required />
          </label>

          <label>
            Категорія:
            <input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required />
          </label>

          <label>
            Опис:
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </label>

          <label>
            Дата:
            <input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} required />
          </label>

          <button type="submit">Додати</button>
        </form>
      </section>

      <section>
        <h2>Фільтри</h2>
        <div className="filters">
          <button onClick={() => setFilter('all')} className={filter === 'all' ? 'active' : ''}>Всі</button>
          <button onClick={() => setFilter('income')} className={filter === 'income' ? 'active' : ''}>Доходи</button>
          <button onClick={() => setFilter('expense')} className={filter === 'expense' ? 'active' : ''}>Витрати</button>
        </div>

        <div style={{marginTop:10}}>
          <label>Пошук: <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="опис або категорія" /></label>
        </div>
      </section>
      
      <section>
        <h2>Операції</h2>

        <table>
          <thead>
            <tr>
              <th onClick={() => handleSort('date')} style={{cursor:'pointer'}}>Дата {sortBy==='date'?(sortDir==='asc'?'↑':'↓'):''}</th>
              <th onClick={() => handleSort('type')} style={{cursor:'pointer'}}>Тип {sortBy==='type'?(sortDir==='asc'?'↑':'↓'):''}</th>
              <th onClick={() => handleSort('amount')} style={{cursor:'pointer'}}>Сума {sortBy==='amount'?(sortDir==='asc'?'↑':'↓'):''}</th>
              <th>Категорія</th>
              <th>Опис</th>
              <th>Дія</th>
            </tr>
          </thead>

          <tbody>
            {sorted.map((transaction, index) => (
              <tr key={transaction.id ?? index}>
                <td>{new Date(transaction.date).toLocaleString()}</td>
                <td>{transaction.type}</td>
                <td>{transaction.amount} грн</td>
                <td>{transaction.category}</td>
                <td>{transaction.description}</td>
                <td><button className="delete-btn" onClick={() => handleDelete(transaction.id)} aria-label="Видалити">Видалити</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}

export default App
