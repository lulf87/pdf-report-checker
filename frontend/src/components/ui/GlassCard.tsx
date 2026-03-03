import { motion, type HTMLMotionProps } from 'framer-motion';
import { SPRING_GENTLE } from '../../constants/motion';

interface GlassCardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  hover?: boolean;
  glow?: boolean;
}

/**
 * GlassCard - Glassmorphism container component
 *
 * Visual attributes:
 * - Semi-transparent background (rgba(255, 255, 255, 0.03))
 * - Backdrop filter blur (20px) with saturation
 * - Border with highlight on top/left edges
 * - Multi-layer box shadow for depth
 *
 * @param hover - Enable scale effect on hover (default: true)
 * @param glow - Enable subtle glow effect on hover (default: false)
 */
export function GlassCard({ children, hover = true, glow = false, className = '', ...props }: GlassCardProps) {
  const baseShadow = '0 4px 24px rgba(0, 0, 0, 0.25), 0 1px 2px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.04)';
  const glowShadow = '0 4px 24px rgba(0, 0, 0, 0.25), 0 1px 2px rgba(0, 0, 0, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.04), 0 0 40px rgba(139, 126, 200, 0.1)';
  const glowShadowHover = '0 8px 32px rgba(0, 0, 0, 0.3), 0 2px 4px rgba(0, 0, 0, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 0 60px rgba(139, 126, 200, 0.2)';

  const boxShadow = glow ? glowShadow : baseShadow;

  return (
    <motion.div
      className={`glass-card ${className}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={SPRING_GENTLE}
      whileHover={hover ? { scale: 1.02 } : glow ? { boxShadow: glowShadowHover } : undefined}
      style={{
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(20px) saturate(1.2)',
        WebkitBackdropFilter: 'blur(20px) saturate(1.2)',
        border: '1px solid var(--glass-border)',
        borderTopColor: 'var(--glass-highlight)',
        borderLeftColor: 'var(--glass-highlight)',
        boxShadow,
        borderRadius: 'var(--radius-lg)',
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
