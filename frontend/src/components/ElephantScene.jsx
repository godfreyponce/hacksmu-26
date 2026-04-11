// React Three Fiber version with advanced shaders
import { Canvas, useFrame, extend } from '@react-three/fiber'
import { useRef, useMemo, useState, useEffect } from 'react'
import * as THREE from 'three'
import { shaderMaterial } from '@react-three/drei'

const DECODED_MESSAGE = "Every rumble carries meaning"
const CRYPTIC_CHARS = "ᚠᚢᚦᚨᚱᚲᚷᚹᚺᚾᛁᛃᛈᛇᛉᛊᛏᛒᛖᛗᛚᛜᛞᛟ∿∾≋≈∻⊜⋈⌇⌁⏦"

// Custom shader material for sound wave particles
const WaveParticleMaterial = shaderMaterial(
  {
    uTime: 0,
    uColor: new THREE.Color(0.5, 0.78, 0.63),
  },
  // Vertex shader
  `
    uniform float uTime;
    attribute float aPhase;
    attribute float aSpeed;
    attribute float aSize;
    varying float vAlpha;
    varying vec3 vColor;

    void main() {
      float progress = mod(uTime * 0.3 + aPhase * 0.5, 1.0);
      float radius = progress * 5.0;

      vec3 pos = position;
      pos.x += cos(aPhase + progress * 6.28) * radius;
      pos.y += sin(uTime * 2.0 + aPhase) * 0.3 * progress;
      pos.z += sin(aPhase + progress * 6.28) * radius * 0.4;

      vAlpha = 1.0 - progress;
      vColor = vec3(0.5 + sin(aPhase) * 0.2, 0.78 + cos(aPhase * 0.5) * 0.1, 0.63);

      vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
      gl_PointSize = aSize * (300.0 / -mvPosition.z) * (1.0 - progress * 0.5);
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  // Fragment shader
  `
    varying float vAlpha;
    varying vec3 vColor;

    void main() {
      float dist = length(gl_PointCoord - vec2(0.5));
      if (dist > 0.5) discard;

      float alpha = smoothstep(0.5, 0.0, dist) * vAlpha;
      vec3 glow = vColor * 1.5;

      gl_FragColor = vec4(glow, alpha * 0.8);
    }
  `
)

extend({ WaveParticleMaterial })

function Elephant() {
  const groupRef = useRef()
  const trunkRef = useRef()
  const leftEarRef = useRef()
  const rightEarRef = useRef()

  useFrame((state) => {
    const t = state.clock.elapsedTime

    // Gentle body sway
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(t * 0.5) * 0.08 - 0.3
      groupRef.current.position.y = Math.sin(t * 0.8) * 0.03
    }

    // Trunk animation
    if (trunkRef.current) {
      trunkRef.current.rotation.x = -0.2 + Math.sin(t * 1.2) * 0.08
      trunkRef.current.rotation.z = Math.sin(t * 0.9) * 0.06
    }

    // Ear flapping
    if (leftEarRef.current) leftEarRef.current.rotation.y = 0.3 + Math.sin(t * 2) * 0.12
    if (rightEarRef.current) rightEarRef.current.rotation.y = -0.3 - Math.sin(t * 2) * 0.12
  })

  const bodyMaterial = useMemo(() => new THREE.MeshStandardMaterial({
    color: 0x8b9a8b,
    roughness: 0.7,
    metalness: 0.1,
  }), [])

  const accentMaterial = useMemo(() => new THREE.MeshStandardMaterial({
    color: 0x7ec8a0,
    roughness: 0.5,
    metalness: 0.2,
    emissive: 0x7ec8a0,
    emissiveIntensity: 0.15
  }), [])

  return (
    <group ref={groupRef} position={[-1.5, 0.5, 0]} rotation={[0, -0.3, 0]}>
      {/* Body */}
      <mesh material={bodyMaterial}>
        <sphereGeometry args={[1.8, 32, 24]} />
        <scale args={[1.2, 0.9, 0.85]} />
      </mesh>

      {/* Head */}
      <mesh position={[2.2, 0.8, 0]} material={bodyMaterial}>
        <sphereGeometry args={[1.1, 32, 24]} />
        <scale args={[0.9, 1, 0.85]} />
      </mesh>

      {/* Trunk */}
      <group ref={trunkRef} position={[3.1, 0.3, 0]} rotation={[-0.2, 0, 0]}>
        <Trunk bodyMaterial={bodyMaterial} accentMaterial={accentMaterial} />
      </group>

      {/* Ears */}
      <mesh ref={leftEarRef} position={[1.6, 1.2, 0.9]} rotation={[0, 0.3, 0.2]} material={bodyMaterial}>
        <sphereGeometry args={[0.9, 16, 16]} />
        <scale args={[0.15, 1, 0.8]} />
      </mesh>
      <mesh ref={rightEarRef} position={[1.6, 1.2, -0.9]} rotation={[0, -0.3, -0.2]} material={bodyMaterial}>
        <sphereGeometry args={[0.9, 16, 16]} />
        <scale args={[0.15, 1, 0.8]} />
      </mesh>

      {/* Eyes */}
      <mesh position={[2.8, 1.1, 0.5]}>
        <sphereGeometry args={[0.12, 16, 16]} />
        <meshStandardMaterial color={0x1a1a1a} />
      </mesh>
      <mesh position={[2.8, 1.1, -0.5]}>
        <sphereGeometry args={[0.12, 16, 16]} />
        <meshStandardMaterial color={0x1a1a1a} />
      </mesh>

      {/* Eye glints */}
      <mesh position={[2.88, 1.15, 0.54]}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshBasicMaterial color={0xffffff} />
      </mesh>
      <mesh position={[2.88, 1.15, -0.46]}>
        <sphereGeometry args={[0.04, 8, 8]} />
        <meshBasicMaterial color={0xffffff} />
      </mesh>

      {/* Legs */}
      {[[0.8, -1.5, 0.6], [0.8, -1.5, -0.6], [-0.9, -1.5, 0.6], [-0.9, -1.5, -0.6]].map((pos, i) => (
        <mesh key={i} position={pos} material={bodyMaterial}>
          <cylinderGeometry args={[0.35, 0.4, 1.8, 16]} />
        </mesh>
      ))}

      {/* Tusks */}
      <mesh position={[3, 0.1, 0.35]} rotation={[0, 0, -1.2]}>
        <coneGeometry args={[0.08, 0.8, 8]} />
        <meshStandardMaterial color={0xf5f5dc} roughness={0.3} />
      </mesh>
      <mesh position={[3, 0.1, -0.35]} rotation={[0, 0, -1.2]}>
        <coneGeometry args={[0.08, 0.8, 8]} />
        <meshStandardMaterial color={0xf5f5dc} roughness={0.3} />
      </mesh>
    </group>
  )
}

function Trunk({ bodyMaterial, accentMaterial }) {
  const curve = useMemo(() => new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0, 0),
    new THREE.Vector3(0.4, -0.2, 0),
    new THREE.Vector3(0.8, -0.1, 0),
    new THREE.Vector3(1.1, 0.2, 0),
    new THREE.Vector3(1.3, 0.6, 0),
    new THREE.Vector3(1.2, 1.0, 0),
    new THREE.Vector3(1.0, 1.3, 0),
  ]), [])

  return (
    <group>
      <mesh material={bodyMaterial}>
        <tubeGeometry args={[curve, 32, 0.22, 16, false]} />
      </mesh>
      {/* Glowing tip */}
      <mesh position={[1.0, 1.3, 0]} material={accentMaterial}>
        <sphereGeometry args={[0.15, 16, 16]} />
      </mesh>
    </group>
  )
}

function SoundWaves() {
  const materialRef = useRef()
  const particleCount = 300

  const { positions, phases, speeds, sizes } = useMemo(() => {
    const positions = new Float32Array(particleCount * 3)
    const phases = new Float32Array(particleCount)
    const speeds = new Float32Array(particleCount)
    const sizes = new Float32Array(particleCount)

    for (let i = 0; i < particleCount; i++) {
      positions[i * 3] = 0
      positions[i * 3 + 1] = 0
      positions[i * 3 + 2] = 0

      phases[i] = Math.random() * Math.PI * 2
      speeds[i] = 0.5 + Math.random() * 0.5
      sizes[i] = 0.5 + Math.random() * 1.5
    }

    return { positions, phases, speeds, sizes }
  }, [])

  useFrame((state) => {
    if (materialRef.current) {
      materialRef.current.uTime = state.clock.elapsedTime
    }
  })

  return (
    <points position={[0.8, 3.0, 0]}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={particleCount} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-aPhase" count={particleCount} array={phases} itemSize={1} />
        <bufferAttribute attach="attributes-aSpeed" count={particleCount} array={speeds} itemSize={1} />
        <bufferAttribute attach="attributes-aSize" count={particleCount} array={sizes} itemSize={1} />
      </bufferGeometry>
      <waveParticleMaterial ref={materialRef} transparent depthWrite={false} blending={THREE.AdditiveBlending} />
    </points>
  )
}

function FloatingGlyphs() {
  const groupRef = useRef()
  const glyphsRef = useRef([])

  const glyphs = useMemo(() => {
    return Array.from({ length: 15 }, (_, i) => ({
      char: CRYPTIC_CHARS[Math.floor(Math.random() * CRYPTIC_CHARS.length)],
      position: [
        3 + (i % 5) * 0.7,
        2 + Math.floor(i / 5) * 0.5,
        (Math.random() - 0.5) * 0.6
      ],
      phase: Math.random() * Math.PI * 2,
      speed: 0.3 + Math.random() * 0.4
    }))
  }, [])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    glyphsRef.current.forEach((sprite, i) => {
      if (sprite) {
        const glyph = glyphs[i]
        sprite.position.x = glyph.position[0] + Math.sin(t * glyph.speed + glyph.phase) * 0.15
        sprite.position.y = glyph.position[1] + Math.cos(t * glyph.speed * 0.7 + glyph.phase) * 0.1
        sprite.material.opacity = 0.3 + Math.sin(t * 2 + i) * 0.25
      }
    })
  })

  return (
    <group ref={groupRef}>
      {glyphs.map((glyph, i) => (
        <GlyphSprite
          key={i}
          ref={(el) => (glyphsRef.current[i] = el)}
          char={glyph.char}
          position={glyph.position}
        />
      ))}
    </group>
  )
}

const GlyphSprite = ({ char, position, ...props }) => {
  const texture = useMemo(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 64
    canvas.height = 64
    const ctx = canvas.getContext('2d')
    ctx.fillStyle = '#7ec8a0'
    ctx.font = '48px serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(char, 32, 32)
    return new THREE.CanvasTexture(canvas)
  }, [char])

  return (
    <sprite {...props} position={position} scale={[0.4, 0.4, 1]}>
      <spriteMaterial map={texture} transparent opacity={0.6} blending={THREE.AdditiveBlending} />
    </sprite>
  )
}

function Scene() {
  return (
    <>
      <ambientLight intensity={0.4} color={0x7ec8a0} />
      <directionalLight position={[5, 10, 7]} intensity={1} />
      <directionalLight position={[-5, 3, -5]} intensity={0.6} color={0x7ec8a0} />

      <Elephant />
      <SoundWaves />
      <FloatingGlyphs />
    </>
  )
}

function DecodingText() {
  const [text, setText] = useState('')
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(true)
      animateDecode(setText)
    }, 1500)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className={`decode-text ${isVisible ? 'visible' : ''}`}>
      <span className="decode-content">{text}</span>
    </div>
  )
}

function animateDecode(setText) {
  const message = DECODED_MESSAGE
  const duration = 3500
  const startTime = Date.now()

  const animate = () => {
    const elapsed = Date.now() - startTime
    const progress = Math.min(elapsed / duration, 1)

    let displayText = ''
    for (let i = 0; i < message.length; i++) {
      const charProgress = (progress * message.length * 1.5 - i) / 3

      if (charProgress >= 1) {
        displayText += message[i]
      } else if (charProgress > 0 && message[i] !== ' ') {
        // Scrambling phase - cycle through cryptic chars
        const scrambleSpeed = 4
        const scrambleIndex = Math.floor((elapsed / 50 + i * 3) % CRYPTIC_CHARS.length)
        displayText += CRYPTIC_CHARS[scrambleIndex]
      } else {
        displayText += message[i] === ' ' ? ' ' : CRYPTIC_CHARS[Math.floor(Math.random() * CRYPTIC_CHARS.length)]
      }
    }

    setText(displayText)

    if (progress < 1) {
      requestAnimationFrame(animate)
    } else {
      setText(message)
    }
  }

  animate()
}

export default function ElephantScene() {
  return (
    <div className="elephant-hero">
      <div className="elephant-canvas">
        <Canvas camera={{ position: [0, 2, 12], fov: 45 }}>
          <Scene />
        </Canvas>
      </div>
      <DecodingText />
    </div>
  )
}
