import { motion, useMotionValue, useSpring } from 'framer-motion';
import { useEffect, useState } from 'react';
import { useMousePosition } from '../../hooks/useMousePosition';
import { SPRING_CURSOR } from '../../constants/motion';

/**
 * MouseFollower - Custom cursor with following ring
 *
 * Features:
 * - Main cursor: 12px solid circle, uses color-accent, mix-blend-mode: difference
 * - Following ring: 36px hollow circle, 80ms delay spring physics
 * - Hover state: Following ring scales to 56px on clickable elements
 */
export function MouseFollower() {
  const [isHovering, setIsHovering] = useState(false);
  const mousePosition = useMousePosition();

  // Main cursor position (instant follow)
  const cursorX = useMotionValue(mousePosition.x - 6);
  const cursorY = useMotionValue(mousePosition.y - 6);

  // Following ring position (delayed spring)
  const ringX = useSpring(mousePosition.x - 18, SPRING_CURSOR);
  const ringY = useSpring(mousePosition.y - 18, SPRING_CURSOR);

  // Hover scale for following ring
  const ringScale = useSpring(isHovering ? 56 : 36, SPRING_CURSOR);

  useEffect(() => {
    // Update cursor position on mouse move
    const handleMouseMove = (e: MouseEvent) => {
      cursorX.set(e.clientX - 6);
      cursorY.set(e.clientY - 6);
    };

    // Detect hoverable elements
    const handleMouseEnter = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'BUTTON' ||
        target.tagName === 'A' ||
        target.onclick !== null ||
        target.style.cursor === 'pointer' ||
        window.getComputedStyle(target).cursor === 'pointer'
      ) {
        setIsHovering(true);
      }
    };

    const handleMouseLeave = () => {
      setIsHovering(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseover', handleMouseEnter);
    window.addEventListener('mouseout', handleMouseLeave);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseover', handleMouseEnter);
      window.removeEventListener('mouseout', handleMouseLeave);
    };
  }, [cursorX, cursorY]);

  return (
    <>
      {/* Hide default cursor */}
      <style>{`
        body {
          cursor: none;
        }
        * {
          cursor: none !important;
        }
      `}</style>

      {/* Main Cursor */}
      <motion.div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: 12,
          height: 12,
          borderRadius: '50%',
          background: 'var(--color-accent)',
          mixBlendMode: 'difference',
          pointerEvents: 'none',
          zIndex: 9999,
          x: cursorX,
          y: cursorY,
        }}
      />

      {/* Following Ring */}
      <motion.div
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: ringScale,
          height: ringScale,
          borderRadius: '50%',
          border: '1px solid var(--color-accent)',
          pointerEvents: 'none',
          zIndex: 9998,
          x: ringX,
          y: ringY,
        }}
      />
    </>
  );
}
