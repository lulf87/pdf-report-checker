/**
 * ParticleBackground - 粒子背景组件
 * 科技感数据大屏设计系统
 *
 * 使用 tsparticles 创建动态粒子背景效果
 * - 蓝色/青色半透明粒子
 * - 粒子连线效果
 * - 鼠标交互
 */

import { useCallback, useMemo } from 'react';
import Particles from '@tsparticles/react';
import { loadSlim } from '@tsparticles/slim';

/**
 * 粒子背景组件
 * @param {Object} props
 * @param {string} props.id - 粒子容器 ID
 * @param {number} props.particleCount - 粒子数量，默认 50
 * @param {number} props.linkDistance - 连线距离，默认 150
 * @param {boolean} props.enableMouseInteraction - 是否启用鼠标交互，默认 true
 */
export default function ParticleBackground({
  id = 'tsparticles',
  particleCount = 50,
  linkDistance = 150,
  enableMouseInteraction = true,
}) {
  // 初始化 particles 引擎
  const particlesInit = useCallback(async (engine) => {
    await loadSlim(engine);
  }, []);

  // 粒子配置
  const options = useMemo(
    () => ({
      fullScreen: {
        enable: true,
        zIndex: -1,
      },
      background: {
        color: {
          value: 'transparent',
        },
      },
      fpsLimit: 60,
      interactivity: {
        events: {
          onClick: {
            enable: true,
            mode: 'push',
          },
          onHover: enableMouseInteraction
            ? {
                enable: true,
                mode: 'grab',
              }
            : false,
          resize: true,
        },
        modes: {
          push: {
            quantity: 2,
          },
          grab: {
            distance: 140,
            links: {
              opacity: 0.5,
            },
          },
        },
      },
      particles: {
        color: {
          value: ['#3b82f6', '#06b6d4', '#8b5cf6'],
        },
        links: {
          color: '#3b82f6',
          distance: linkDistance,
          enable: true,
          opacity: 0.2,
          width: 1,
        },
        move: {
          direction: 'none',
          enable: true,
          outModes: {
            default: 'bounce',
          },
          random: true,
          speed: 0.5,
          straight: false,
        },
        number: {
          density: {
            enable: true,
            area: 800,
          },
          value: particleCount,
        },
        opacity: {
          value: {
            min: 0.1,
            max: 0.4,
          },
          animation: {
            enable: true,
            speed: 1,
            sync: false,
          },
        },
        shape: {
          type: 'circle',
        },
        size: {
          value: {
            min: 1,
            max: 3,
          },
        },
      },
      detectRetina: true,
    }),
    [particleCount, linkDistance, enableMouseInteraction]
  );

  return <Particles id={id} init={particlesInit} options={options} />;
}

/**
 * 轻量版粒子背景 - 用于性能敏感场景
 */
export function LightParticleBackground({ id = 'tsparticles-light' }) {
  const particlesInit = useCallback(async (engine) => {
    await loadSlim(engine);
  }, []);

  const options = useMemo(
    () => ({
      fullScreen: {
        enable: true,
        zIndex: -1,
      },
      background: {
        color: {
          value: 'transparent',
        },
      },
      fpsLimit: 30,
      particles: {
        color: {
          value: '#3b82f6',
        },
        move: {
          enable: true,
          speed: 0.3,
          direction: 'none',
          outModes: 'bounce',
        },
        number: {
          value: 20,
        },
        opacity: {
          value: 0.2,
        },
        shape: {
          type: 'circle',
        },
        size: {
          value: 2,
        },
      },
      detectRetina: false,
    }),
    []
  );

  return <Particles id={id} init={particlesInit} options={options} />;
}
