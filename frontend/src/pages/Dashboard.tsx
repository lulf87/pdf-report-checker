import { motion, type Variants } from 'framer-motion';
import { FileText, CheckCircle } from 'lucide-react';
import { GlassCard } from '../components/ui/GlassCard';
import { SPRING_GENTLE, STAGGER_DELAY } from '../constants/motion';

interface ModuleCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  onClick: () => void;
}

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: STAGGER_DELAY,
      delayChildren: 0.2,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: SPRING_GENTLE,
  },
};

/**
 * ModuleCard - Individual module entry card
 */
function ModuleCard({ title, description, icon, onClick }: ModuleCardProps) {
  return (
    <motion.div
      variants={itemVariants}
      onClick={onClick}
      style={{ cursor: 'pointer', width: '100%', maxWidth: '400px' }}
    >
      <GlassCard hover glow>
        <div
          style={{
            padding: '2rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
            gap: '1.5rem',
          }}
        >
          <motion.div
            style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              background: 'var(--glass-bg)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--color-accent)',
            }}
            whileHover={{ scale: 1.1, rotate: 5 }}
            transition={SPRING_GENTLE}
          >
            {icon}
          </motion.div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <h2
              style={{
                fontSize: '1.5rem',
                fontWeight: 600,
                color: 'var(--text-primary)',
              }}
            >
              {title}
            </h2>
            <p
              style={{
                fontSize: '1rem',
                color: 'var(--text-secondary)',
                lineHeight: 1.6,
              }}
            >
              {description}
            </p>
          </div>
        </div>
      </GlassCard>
    </motion.div>
  );
}

/**
 * Dashboard - Main landing page with module selection
 *
 * Features:
 * - Two module entry cards (PTR Compare / Report Check)
 * - Staggered entrance animations
 * - Glassmorphism cards with hover effects
 */
export function Dashboard() {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        gap: '2rem',
      }}
    >
      {/* App Title */}
      <motion.h1
        variants={itemVariants}
        style={{
          fontSize: '3rem',
          fontWeight: 600,
          letterSpacing: '0.02em',
          background: 'linear-gradient(135deg, var(--text-primary) 0%, var(--color-accent) 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          textAlign: 'center',
          marginBottom: '2rem',
        }}
      >
        Report Checker Pro
      </motion.h1>

      {/* Module Cards Container */}
      <motion.div
        variants={containerVariants}
        style={{
          display: 'flex',
          flexDirection: 'row',
          gap: '2rem',
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        <ModuleCard
          title="PTR 条款核对"
          description="核对检验报告与产品技术要求之间的条款文本一致性"
          icon={<FileText size={40} />}
          onClick={() => (window.location.hash = '/ptr-compare')}
        />

        <ModuleCard
          title="报告自身核对"
          description="核对检验报告内部的字段一致性、照片覆盖性、标签匹配等"
          icon={<CheckCircle size={40} />}
          onClick={() => (window.location.hash = '/report-check')}
        />
      </motion.div>
    </motion.div>
  );
}
