import { motionValue, useTransform } from 'framer-motion';
import { useEffect } from 'react';

interface ParallaxOptions {
  /**
   * Horizontal movement range in pixels (±amount)
   * @default 10
   */
  x?: number;
  /**
   * Vertical movement range in pixels (±amount)
   * @default 10
   */
  y?: number;
  /**
   * Smoothing factor (0-1), lower = smoother/slower
   * @default 0.08
   */
  smoothness?: number;
}

/**
 * Hook for parallax effect on elements based on mouse position
 *
 * Creates motion values that respond to mouse movement with
 * configurable range and smoothing. Ideal for background elements,
 * floating shapes, and decorative components.
 *
 * @param options - Parallax configuration
 * @returns Motion values for x and y transforms
 */
export function useParallax(options: ParallaxOptions = {}) {
  const { x: rangeX = 10, y: rangeY = 10, smoothness = 0.08 } = options;

  const mouseX = motionValue(0);
  const mouseY = motionValue(0);

  const x = useTransform(
    mouseX,
    (val) => (val - window.innerWidth / 2) * smoothness * (rangeX / 10)
  );

  const y = useTransform(
    mouseY,
    (val) => (val - window.innerHeight / 2) * smoothness * (rangeY / 10)
  );

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      mouseX.set(event.clientX);
      mouseY.set(event.clientY);
    };

    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, [mouseX, mouseY]);

  return { x, y };
}
