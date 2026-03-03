import { motion } from 'framer-motion';
import { SPRING_GENTLE, STAGGER_DELAY } from '../../constants/motion';
import { ClauseCard } from './ClauseCard';
import type { Clause } from '../../types/ptr';

interface ClauseListProps {
  clauses: Clause[];
  filter: 'all' | 'mismatched';
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: STAGGER_DELAY,
    },
  },
};

/**
 * ClauseList - Staggered list of clause cards
 *
 * Features:
 * - Filters clauses by match status
 * - Staggered entrance animation
 * - Empty state handling
 */
export function ClauseList({ clauses, filter }: ClauseListProps) {
  const filteredClauses =
    filter === 'all' ? clauses : clauses.filter((c) => !c.is_match);

  if (filteredClauses.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={SPRING_GENTLE}
        style={{
          textAlign: 'center',
          padding: '3rem 1rem',
          color: 'var(--text-muted)',
        }}
      >
        <p style={{ fontSize: '1.125rem', marginBottom: '0.5rem' }}>
          {filter === 'all' ? '暂无条款数据' : '没有不一致的条款'}
        </p>
        <p style={{ fontSize: '0.875rem' }}>
          {filter === 'mismatched' ? '所有条款都已核对一致' : ''}
        </p>
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={{ display: 'flex', flexDirection: 'column' }}
    >
      {filteredClauses.map((clause, index) => (
        <ClauseCard key={clause.id} clause={clause} index={index} />
      ))}
    </motion.div>
  );
}
