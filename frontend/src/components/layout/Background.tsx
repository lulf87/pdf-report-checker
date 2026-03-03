import { motion } from 'framer-motion';
import { useParallax } from '../../hooks/useParallax';

/**
 * Background - Deep gradient background with parallax light spots
 *
 * Features:
 * - Deep gradient background (#0f1117 → #1a1d2e → #151822)
 * - 3 large blurred light spots with parallax movement
 * - Each spot responds differently to mouse position
 */
export function Background() {
  // Different parallax settings for each spot for depth effect
  const spot1 = useParallax({ x: 15, y: 15, smoothness: 0.05 });
  const spot2 = useParallax({ x: 20, y: 20, smoothness: 0.08 });
  const spot3 = useParallax({ x: 12, y: 12, smoothness: 0.06 });

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'var(--bg-gradient)',
        zIndex: -1,
        overflow: 'hidden',
      }}
    >
      {/* Light Spot 1 - Purple Accent */}
      <motion.div
        style={{
          position: 'absolute',
          width: '400px',
          height: '400px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(139, 126, 200, 0.15) 0%, transparent 70%)',
          filter: 'blur(80px)',
          x: spot1.x,
          y: spot1.y,
          top: '10%',
          left: '20%',
        }}
      />

      {/* Light Spot 2 - Blue Info */}
      <motion.div
        style={{
          position: 'absolute',
          width: '350px',
          height: '350px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(122, 143, 181, 0.12) 0%, transparent 70%)',
          filter: 'blur(60px)',
          x: spot2.x,
          y: spot2.y,
          top: '60%',
          right: '15%',
        }}
      />

      {/* Light Spot 3 - Green Success */}
      <motion.div
        style={{
          position: 'absolute',
          width: '300px',
          height: '300px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(107, 158, 138, 0.1) 0%, transparent 70%)',
          filter: 'blur(70px)',
          x: spot3.x,
          y: spot3.y,
          bottom: '20%',
          left: '40%',
        }}
      />
    </div>
  );
}
