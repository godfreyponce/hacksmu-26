import { useState, useCallback } from 'react'
import { buildApiUrl } from '../lib/api'

export default function useVoiceQuery() {
  const [isListening, setIsListening] = useState(false)
  const [response, setResponse] = useState(null)
  const elevenKey = import.meta.env.VITE_ELEVENLABS_API_KEY
  const elevenVoiceId = import.meta.env.VITE_ELEVENLABS_VOICE_ID || 'JBFqnCBsd6RMkjVDRZzb'
  const authToken = import.meta.env.VITE_AUTH0_M2M_TOKEN

  const transcribeWithElevenLabs = async (blob) => {
    const formData = new FormData()
    formData.append('file', blob, 'query.webm')
    formData.append('model_id', 'scribe_v1')

    const res = await fetch('https://api.elevenlabs.io/v1/speech-to-text', {
      method: 'POST',
      headers: { 'xi-api-key': elevenKey },
      body: formData
    })
    if (!res.ok) throw new Error('STT failed')
    const data = await res.json()
    return data.text || ''
  }

  const speakWithElevenLabs = async (text) => {
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${elevenVoiceId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'xi-api-key': elevenKey
      },
      body: JSON.stringify({
        text,
        model_id: 'eleven_turbo_v2_5'
      })
    })
    if (!res.ok) return

    const audioBlob = await res.blob()
    const url = URL.createObjectURL(audioBlob)
    const audio = new Audio(url)
    audio.play().finally(() => URL.revokeObjectURL(url))
  }

  const startListening = useCallback(async () => {
    setIsListening(true)
    setResponse(null)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      const chunks = []

      mediaRecorder.ondataavailable = (e) => chunks.push(e.data)

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        const text = await transcribeWithElevenLabs(blob)

        const res = await fetch(buildApiUrl('/query'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(authToken ? { Authorization: `Bearer ${authToken}` } : {})
          },
          body: JSON.stringify({ text })
        })

        const data = await res.json()
        const answer = data.answer || 'No answer received.'
        setResponse(answer)

        if (elevenKey) {
          speakWithElevenLabs(answer).catch((e) => console.error('TTS failed:', e))
        }

        stream.getTracks().forEach(track => track.stop())
        setIsListening(false)
      }

      mediaRecorder.start()

      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          mediaRecorder.stop()
        }
      }, 10000)

    } catch (err) {
      console.error('Voice query error:', err)
      setResponse('Voice query failed. Check API keys and auth token.')
      setIsListening(false)
    }
  }, [authToken, elevenKey])

  const stopListening = useCallback(() => {
    setIsListening(false)
  }, [])

  return { isListening, response, startListening, stopListening }
}
