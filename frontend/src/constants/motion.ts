/**
 * Spring Physics Animation Constants
 * All animations must use spring physics by default.
 * Only exceptions (with explicit comments): spinners, pulse loops, AnimatePresence exit transitions.
 */

import type { Transition } from 'framer-motion';

/**
 * Gentle spring - for general entrance animations
 * Smooth, subtle motion with low damping
 */
export const SPRING_GENTLE: Transition = {
  type: 'spring',
  stiffness: 120,
  damping: 20,
  mass: 1,
};

/**
 * Snappy spring - for button interactions, micro-interactions
 * Fast, responsive feel with higher stiffness
 */
export const SPRING_SNAPPY: Transition = {
  type: 'spring',
  stiffness: 400,
  damping: 25,
  mass: 0.8,
};

/**
 * Smooth spring - for layout changes, card expansions
 * Balanced motion for size transitions
 */
export const SPRING_SMOOTH: Transition = {
  type: 'spring',
  stiffness: 200,
  damping: 30,
  mass: 1.2,
};

/**
 * Page spring - for page transitions, large container animations
 * Slower, more cinematic motion
 */
export const SPRING_PAGE: Transition = {
  type: 'spring',
  stiffness: 80,
  damping: 20,
  mass: 1.5,
};

/**
 * Stagger delay for list children animations
 * Use with staggerChildren in variants
 */
export const STAGGER_DELAY = 0.04;

/**
 * Exit transition for AnimatePresence (must use tween, not spring)
 * Framer Motion requires tween for exit animations
 */
export const EXIT_TRANSITION: Transition = {
  duration: 0.2,
  ease: 'easeOut',
};

/**
 * Spinner transition exception.
 * Allowed by design rules for continuous loading rotations.
 */
export const SPINNER_LINEAR: Transition = {
  duration: 1,
  repeat: Infinity,
  ease: 'linear',
};

/**
 * Pulse transition exception.
 * Allowed by design rules for looped status emphasis.
 */
export const PULSE_LOOP: Transition = {
  duration: 2,
  repeat: Infinity,
  ease: 'easeInOut',
};

/**
 * Fast pulse for drag-drop affordance in upload area.
 */
export const PULSE_FAST: Transition = {
  duration: 0.6,
  repeat: Infinity,
  ease: 'easeInOut',
};

/**
 * Spring options for cursor follower (useSpring)
 */
export const SPRING_CURSOR = {
  stiffness: 150,
  damping: 20,
  mass: 0.8,
};

/**
 * Spring options for numeric counter (useSpring)
 */
export const SPRING_COUNTER = {
  stiffness: 100,
  damping: 20,
  mass: 1,
};
