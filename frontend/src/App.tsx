import { useEffect, useState } from 'react'

function App() {
  const [health, setHealth] = useState<string>('checking...')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/health/', {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
          credentials: 'include',
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()
        console.log('Response data:', data)
        setHealth(data.status)
      } catch (error) {
        console.error('Error details:', error)
        setError(error instanceof Error ? error.message : 'Unknown error')
        setHealth('error')
      }
    }

    checkHealth()
  }, [])

  return (
    <div className="App" style={{ padding: '20px' }}>
      <h1>Hello World!</h1>
      <p>Backend status: {health}</p>
      {error && (
        <div style={{ color: 'red', marginTop: '20px' }}>
          <p>Error occurred:</p>
          <pre>{error}</pre>
        </div>
      )}
    </div>
  )
}

export default App 