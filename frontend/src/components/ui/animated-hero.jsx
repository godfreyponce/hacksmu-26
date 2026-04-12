import { useEffect, useMemo, useState } from "react"
import { motion } from "framer-motion"
import { MoveRight, Headphones } from "lucide-react"
import { Button } from "@/components/ui/button"

function AnimatedHero({ onExplore, onDashboard }) {
  const [titleNumber, setTitleNumber] = useState(0)
  const titles = useMemo(
    () => ["decoded", "analyzed", "understood", "preserved", "revealed"],
    []
  )

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (titleNumber === titles.length - 1) {
        setTitleNumber(0)
      } else {
        setTitleNumber(titleNumber + 1)
      }
    }, 2000)
    return () => clearTimeout(timeoutId)
  }, [titleNumber, titles])

  return (
    <div style={{ width: '100%', padding: '60px 0 80px' }}>
      <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '0 24px' }}>
        <div style={{
          display: 'flex',
          gap: '32px',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <div>
            <Button variant="secondary" size="sm" style={{ gap: '12px', display: 'flex', alignItems: 'center' }}>
              212 calls processed with +5.7dB improvement <MoveRight style={{ width: '16px', height: '16px' }} />
            </Button>
          </div>

          <div style={{ display: 'flex', gap: '16px', flexDirection: 'column' }}>
            <h1 style={{
              fontFamily: 'Cormorant Garamond, Georgia, serif',
              fontSize: 'clamp(48px, 7vw, 84px)',
              maxWidth: '800px',
              letterSpacing: '-0.03em',
              textAlign: 'center',
              fontWeight: 400,
              lineHeight: 1,
              color: '#e8ede5'
            }}>
              <span style={{ display: 'block' }}>Every rumble</span>
              <span style={{
                position: 'relative',
                display: 'flex',
                width: '100%',
                justifyContent: 'center',
                overflow: 'hidden',
                height: 'clamp(58px, 8vw, 100px)',
                marginTop: '8px'
              }}>
                {titles.map((title, index) => (
                  <motion.span
                    key={index}
                    style={{
                      position: 'absolute',
                      fontWeight: 500,
                      fontStyle: 'italic',
                      color: '#7ec8a0'
                    }}
                    initial={{ opacity: 0, y: -100 }}
                    transition={{ type: "spring", stiffness: 50 }}
                    animate={
                      titleNumber === index
                        ? { y: 0, opacity: 1 }
                        : { y: titleNumber > index ? -150 : 150, opacity: 0 }
                    }
                  >
                    {title}
                  </motion.span>
                ))}
              </span>
            </h1>

            <p style={{
              fontFamily: 'DM Sans, Avenir Next, sans-serif',
              fontSize: 'clamp(16px, 2vw, 20px)',
              lineHeight: 1.6,
              letterSpacing: '-0.01em',
              color: 'rgba(232, 237, 229, 0.65)',
              maxWidth: '620px',
              textAlign: 'center',
              margin: '0 auto'
            }}>
              From noisy field recordings to crystal-clear elephant calls.
              Our AI pipeline removes generators, traffic, and wind — revealing
              the hidden communication beneath.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'row', gap: '12px', flexWrap: 'wrap', justifyContent: 'center' }}>
            <Button size="lg" variant="outline" onClick={onDashboard} style={{ gap: '12px', display: 'flex', alignItems: 'center' }}>
              Explore spectrograms <Headphones style={{ width: '18px', height: '18px' }} />
            </Button>
            <Button size="lg" onClick={onExplore} style={{ gap: '12px', display: 'flex', alignItems: 'center' }}>
              Try live demo <MoveRight style={{ width: '18px', height: '18px' }} />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export { AnimatedHero }
