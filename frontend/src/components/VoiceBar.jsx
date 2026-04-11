// ElevenLabs mic + spoken answer

import { useState } from 'react'
import useVoiceQuery from '../hooks/useVoiceQuery'

export default function VoiceBar() {
  const { isListening, response, startListening, stopListening } = useVoiceQuery()

  const handleMicClick = () => {
    if (isListening) {
      stopListening()
    } else {
      startListening()
    }
  }

  return (
    <div className="voice-bar">
      <button
        className={`mic-btn ${isListening ? 'active' : ''}`}
        onClick={handleMicClick}
      >
        {isListening ? 'Stop' : 'Ask'}
      </button>
      {response && (
        <div className="response">
          <p>{response}</p>
        </div>
      )}
    </div>
  )
}
