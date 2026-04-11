import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'

mapboxgl.accessToken = import.meta.env.VITE_MAPBOX_TOKEN

function pseudoCoord(seed) {
  const n = Number(seed) || 0
  return [36.7 + (n % 12) * 0.08, -1.35 + (n % 9) * 0.06]
}

export default function CallMap({ calls = [], selectedId }) {
  const mapContainer = useRef(null)
  const map = useRef(null)

  useEffect(() => {
    if (map.current) return

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [36.8, -1.3],
      zoom: 6
    })

    map.current.on('load', () => {
      map.current.addSource('calls', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      })

      map.current.addLayer({
        id: 'calls-heat',
        type: 'heatmap',
        source: 'calls',
        paint: {
          'heatmap-weight': 1,
          'heatmap-intensity': 0.8,
          'heatmap-radius': 20,
          'heatmap-color': [
            'interpolate', ['linear'], ['heatmap-density'],
            0, 'rgba(0,0,0,0)',
            0.2, '#2c7bb6',
            0.4, '#abd9e9',
            0.6, '#ffffbf',
            0.8, '#fdae61',
            1, '#d7191c'
          ]
        }
      })
    })

    return () => map.current?.remove()
  }, [])

  useEffect(() => {
    if (!map.current) return

    const features = calls.map((call, idx) => {
      const [lng, lat] = pseudoCoord(call.id || idx + 1)
      return {
        type: 'Feature',
        properties: {
          id: call.id,
          selected: call.id === selectedId ? 1 : 0
        },
        geometry: {
          type: 'Point',
          coordinates: [lng, lat]
        }
      }
    })

    const source = map.current.getSource('calls')
    if (source) {
      source.setData({ type: 'FeatureCollection', features })
    }
  }, [calls, selectedId])

  return <div ref={mapContainer} className="call-map" />
}
