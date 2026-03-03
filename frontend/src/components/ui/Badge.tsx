import { motion } from 'framer-motion';
import { PULSE_LOOP, SPRING_GENTLE } from '../../constants/motion';

type BadgeVariant = 'success' | 'danger' | 'info' | 'warn' | 'accent';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  pulse?: boolean;
  className?: string;
}

const variantColors: Record<BadgeVariant, string> = {
  success: 'var(--color-success)',
  danger: 'var(--color-danger)',
  info: 'var(--color-info)',
  warn: 'var(--color-warn)',
  accent: 'var(--color-accent)',
};

/**
 * Badge - Status label with optional pulse animation
 *
 * Visual features:
 * - Colored dot indicator
 * - Low saturation Morandi colors
 * - Optional gentle pulse effect for attention
 */
export function Badge({ children, variant = 'info', pulse = false, className = '' }: BadgeProps) {
  const color = variantColors[variant];

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={SPRING_GENTLE}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.375rem 0.75rem',
        borderRadius: 'var(--radius-full)',
        background: 'var(--glass-bg)',
        border: `1px solid ${color}`,
        fontSize: '0.875rem',
        fontWeight: 500,
        color: 'var(--text-primary)',
      }}
    >
      <motion.span
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: color,
        }}
        animate={pulse ? {
          scale: [1, 1.2, 1],
          opacity: [1, 0.7, 1],
        } : {}}
        transition={pulse ? PULSE_LOOP : {}}
      />
      <span>{children}</span>
    </motion.div>
  );
}
