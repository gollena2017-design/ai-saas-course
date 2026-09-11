import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [transactions, setTransactions] = useState([])
  const [summary, setSummary] = useState(null)
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
  }, [])

  useEffect(() => {
    // refetch when filter changes
    setLoading(true)
    setError('')
    ;(async () => {
      try {
        const resp = await fetch(`/api/transactions?type=${filter}`)
        if (!resp.ok) throw new Error('API error')
        const data = await resp.json()
        setTransactions(data)
      } catch (err) {
        console.error(err)
        setError('Не вдалося завантажити операції.')
      } finally {
        setLoading(false)
      }
    })()
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
      </section>

      <section>
        <h2>Операції</h2>

        <table>
          <thead>
            <tr>
              <th>Дата</th>
              <th>Тип</th>
              <th>Сума</th>
              <th>Категорія</th>
              <th>Опис</th>
              <th>Дія</th>
            </tr>
          </thead>

          <tbody>
            {transactions.map((transaction, index) => (
              <tr key={index}>
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