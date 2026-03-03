import { motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import { SPRING_GENTLE } from '../../constants/motion';
import { Button } from '../ui/Button';

interface HeaderProps {
  title: string;
  onBack?: () => void;
  showBack?: boolean;
}

/**
 * Header - Top navigation bar with back button
 *
 * Features:
 * - Glassmorphism effect
 * - Optional back button with spring animation
 * - Responsive title display
 */
export function Header({ title, onBack, showBack = true }: HeaderProps) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={SPRING_GENTLE}
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        padding: '1rem 2rem',
        background: 'rgba(15, 17, 23, 0.8)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        borderBottom: '1px solid var(--glass-border)',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
      }}
    >
      {showBack && onBack && (
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          style={{ padding: '0.5rem', display: 'flex', alignItems: 'center' }}
        >
          <ArrowLeft size={20} />
        </Button>
      )}

      <motion.h1
        style={{
          fontSize: '1.5rem',
          fontWeight: 600,
          letterSpacing: '0.02em',
          color: 'var(--text-primary)',
        }}
      >
        {title}
      </motion.h1>
    </motion.header>
  );
}
