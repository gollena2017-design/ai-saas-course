import { useEffect, useState } from 'react'
import './Chat.css'

export default function Chat({ onTransactionChanged }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [threadId, setThreadId] = useState(() => localStorage.getItem('chat_thread_id'))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [pendingAction, setPendingAction] = useState(null)
  const [actionLoading, setActionLoading] = useState(false)

  useEffect(() => {
    // Restore the whole conversation, not merely its latest pair of messages.
    (async () => {
      if (!threadId) return
      try {
        const resp = await fetch(`/api/ai/thread/${threadId}`)
        if (!resp.ok) return
        const data = await resp.json()
        setMessages((data.messages || []).map((message) => ({
          role: message.role,
          text: message.content,
        })))
      } catch (error) {
        console.error(error)
      }
    })()
  }, [threadId])

  const append = (role, text) => setMessages(m => [...m, { role, text }])

  const send = async () => {
    if (!input.trim()) return
    const userText = input.trim()
    append('user', userText)
    setInput('')
    setLoading(true)
    setError('')

    try {
      const resp = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userText, thread_id: threadId ? Number(threadId) : null }),
      })

      if (!resp.ok) throw new Error('Chat API error')

      const data = await resp.json()
      if (data.thread_id) {
        localStorage.setItem('chat_thread_id', String(data.thread_id))
        setThreadId(String(data.thread_id))
      }

      let answer = data.answer || ''
      // try parse JSON reply
      try {
        const parsed = JSON.parse(answer)
        if (parsed.reply) answer = parsed.reply
      } catch {
        // not JSON
      }

      append('assistant', answer)
      if (data.pending_action) setPendingAction(data.pending_action)
    } catch (error) {
      console.error(error)
      setError('Не вдалося отримати відповідь. Перевірте з’єднання з API.')
    } finally {
      setLoading(false)
    }
  }

  const resolveAction = async (operation) => {
    if (!pendingAction || actionLoading) return
    setActionLoading(true)
    setError('')
    try {
      const response = await fetch(`/api/ai/actions/${pendingAction.action_id}/${operation}`, {
        method: 'POST',
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Помилка виконання дії')
      setPendingAction(data.action)
      if (operation === 'confirm') {
        append('assistant', 'Дію підтверджено: операцію додано до фінансових даних.')
        onTransactionChanged?.()
      } else {
        append('assistant', 'Запропоновану дію скасовано.')
      }
    } catch (actionError) {
      console.error(actionError)
      setError(actionError.message || 'Не вдалося виконати дію.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="chat">
      <h3>AI Chat</h3>
      <div className="chat-window" aria-live="polite">
        {messages.length === 0 && <div className="muted">Напишіть повідомлення, щоб почати розмову</div>}
        {messages.map((m,i)=>(
          <div key={i} className={`msg ${m.role}`}>
            <div className="role">{m.role}</div>
            <div className="text">{m.text}</div>
          </div>
        ))}
      </div>

      {pendingAction && (
        <section className="pending-action" aria-live="polite">
          <h4>Запропонована дія</h4>
          <p><strong>Тип:</strong> {pendingAction.payload.type === 'expense' ? 'створити витрату' : 'створити дохід'}</p>
          <p><strong>Сума:</strong> {pendingAction.payload.amount} грн</p>
          <p><strong>Категорія:</strong> {pendingAction.payload.category}</p>
          <p><strong>Дата:</strong> {pendingAction.payload.date}</p>
          {pendingAction.payload.description && <p><strong>Опис:</strong> {pendingAction.payload.description}</p>}
          {pendingAction.status === 'pending' ? (
            <div className="action-controls">
              <button onClick={() => resolveAction('confirm')} disabled={actionLoading}>
                {actionLoading ? 'Обробка...' : 'Підтвердити'}
              </button>
              <button onClick={() => resolveAction('cancel')} disabled={actionLoading}>
                Скасувати
              </button>
            </div>
          ) : <p className="muted">Статус: {pendingAction.status}</p>}
        </section>
      )}

      <div className="chat-input">
        <textarea value={input} disabled={loading} onChange={(e)=>setInput(e.target.value)} onKeyDown={handleKey} placeholder="Напишіть повідомлення..." />
        <div className="controls">
          <button onClick={send} disabled={loading}>{loading ? 'Відповідає...' : 'Відправити'}</button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}
    </div>
  )
}
