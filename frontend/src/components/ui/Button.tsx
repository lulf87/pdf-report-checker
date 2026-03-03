import { motion, type HTMLMotionProps } from 'framer-motion';
import { SPRING_SNAPPY } from '../../constants/motion';

interface ButtonProps extends HTMLMotionProps<'button'> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
}

const sizeStyles = {
  sm: { padding: '0.5rem 1rem', fontSize: '0.875rem' },
  md: { padding: '0.75rem 1.5rem', fontSize: '1rem' },
  lg: { padding: '1rem 2rem', fontSize: '1.125rem' },
};

const variantStyles = {
  primary: {
    background: 'var(--color-accent)',
    color: '#ffffff',
  },
  secondary: {
    background: 'var(--glass-bg)',
    color: 'var(--text-primary)',
    border: '1px solid var(--glass-border)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--text-secondary)',
  },
};

/**
 * Button - Spring physics interactive button
 *
 * Motion effects:
 * - Hover: scale 1.03 with spring physics
 * - Tap: scale 0.97 with spring physics
 * - Disabled: reduced opacity, no interaction
 */
export function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <motion.button
      className={className}
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.03 }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      transition={SPRING_SNAPPY}
      style={{
        ...sizeStyles[size],
        ...variantStyles[variant],
        fontWeight: 500,
        borderRadius: 'var(--radius-md)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        border: variant !== 'primary' ? '1px solid var(--glass-border)' : 'none',
        transition: 'opacity 150ms ease',
      }}
      {...props}
    >
      {children}
    </motion.button>
  );
}
