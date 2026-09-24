import { useEffect, useState } from 'react'
import './Chat.css'

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [threadId, setThreadId] = useState(() => localStorage.getItem('chat_thread_id'))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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
    } catch (error) {
      console.error(error)
      setError('Не вдалося отримати відповідь. Перевірте з’єднання з API.')
    } finally {
      setLoading(false)
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
