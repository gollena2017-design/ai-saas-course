import { useEffect, useState } from 'react'
import './App.css'

function App() {
  const [transactions, setTransactions] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadData() {
      try {
        const [transactionsResponse, summaryResponse] = await Promise.all([
          fetch('/api/transactions'),
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
        <h2>Операції</h2>

        <table>
          <thead>
            <tr>
              <th>Дата</th>
              <th>Тип</th>
              <th>Сума</th>
              <th>Категорія</th>
              <th>Опис</th>
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
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}

export default App