import { motion, useSpring, useTransform } from 'framer-motion';
import { useEffect, useState } from 'react';
import { SPRING_COUNTER } from '../../constants/motion';

interface AnimatedCounterProps {
  value: number;
  className?: string;
  formatValue?: (value: number) => string;
}

/**
 * AnimatedCounter - Number counting animation
 *
 * Uses spring physics for smooth number transitions.
 * Optionally formats the displayed value (e.g., percentages, currency).
 */
export function AnimatedCounter({
  value,
  className = '',
  formatValue = (v) => v.toString(),
}: AnimatedCounterProps) {
  const [displayValue, setDisplayValue] = useState(0);

  // Spring-animated value
  const spring = useSpring(0, SPRING_COUNTER);

  // Transform spring value to display
  const animatedValue = useTransform(spring, (latest) => {
    return Math.round(latest);
  });

  // Update display when animated value changes
  useEffect(() => {
    const unsubscribe = animatedValue.on('change', (v) => {
      setDisplayValue(v);
    });
    return unsubscribe;
  }, [animatedValue]);

  // Animate to new value
  useEffect(() => {
    spring.set(value);
  }, [value, spring]);

  return (
    <motion.span
      className={className}
      style={{
        fontVariantNumeric: 'tabular-nums',
      }}
    >
      {formatValue(displayValue)}
    </motion.span>
  );
}
