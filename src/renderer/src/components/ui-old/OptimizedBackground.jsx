/**
 * OptimizedBackground - 轻量级高性能背景组件
 * 替代 ParticleBackground，使用纯 CSS 实现科技感背景
 */

import React from 'react';
import './OptimizedBackground.css';

/**
 * 优化背景组件
 * @param {Object} props
 * @param {string} [props.variant='default'] - 背景变体: 'default' | 'minimal' | 'grid-only'
 * @param {boolean} [props.showGlow=true] - 是否显示光晕效果
 */
export default function OptimizedBackground({ variant = 'default', showGlow = true }) {
  return (
    <div className={`optimized-background optimized-background--${variant}`}>
      {showGlow && <div className="optimized-background__glow" />}
      <div className="optimized-background__grid" />
    </div>
  );
}

/**
 * 极简背景 - 仅网格，无光晕
 */
export function MinimalBackground() {
  return (
    <div className="optimized-background optimized-background--minimal">
      <div className="optimized-background__grid" />
    </div>
  );
}

/**
 * 纯色背景 - 用于性能最敏感场景
 */
export function SolidBackground() {
  return <div className="optimized-background optimized-background--solid" />;
}
