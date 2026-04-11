// ElevenLabs STT → Gemini → TTS

import { useState, useCallback } from 'react'

export default function useVoiceQuery() {
  const [isListening, setIsListening] = useState(false)
  const [response, setResponse] = useState(null)
  const apiUrl = import.meta.env.VITE_API_URL

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
        const formData = new FormData()
        formData.append('audio', blob)

        const res = await fetch(`${apiUrl}/api/query`, {
          method: 'POST',
          body: formData
        })
        const data = await res.json()
        setResponse(data.text)

        if (data.audio_url) {
          const audio = new Audio(data.audio_url)
          audio.play()
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
      setIsListening(false)
    }
  }, [apiUrl])

  const stopListening = useCallback(() => {
    setIsListening(false)
  }, [])

  return { isListening, response, startListening, stopListening }
}
