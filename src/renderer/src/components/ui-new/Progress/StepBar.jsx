import React from 'react'
import PropTypes from 'prop-types'
import classNames from 'classnames'
import { Check, Loader2 } from 'lucide-react'
import styles from './StepBar.module.css'

/**
 * StepBar - 步骤条组件
 * @param {Object} props
 * @param {Array} props.steps - 步骤数组 [{ key, title, description }]
 * @param {number} props.current - 当前步骤索引
 * @param {'horizontal'|'vertical'} [props.direction] - 方向
 * @param {'blue'|'cyan'|'purple'|'success'} [props.color] - 颜色
 * @param {string} [props.className] - 额外的类名
 */
function StepBar({
  steps,
  current,
  direction = 'horizontal',
  color = 'blue',
  className,
  ...rest
}) {
  const stepBarClasses = classNames(
    styles.stepBar,
    styles[`stepBar--${direction}`],
    className
  )

  const getStepStatus = (index) => {
    if (index < current) return 'completed'
    if (index === current) return 'current'
    return 'pending'
  }

  return (
    <div className={stepBarClasses} {...rest}>
      {steps.map((step, index) => {
        const status = getStepStatus(index)
        const stepClasses = classNames(
          styles.stepBar__step,
          styles[`stepBar__step--${status}`],
          styles[`stepBar__step--${color}`]
        )

        return (
          <div key={step.key || index} className={stepClasses}>
            <div className={styles.stepBar__indicator}>
              {status === 'completed' ? (
                <Check size={16} />
              ) : status === 'current' ? (
                <Loader2 size={16} className={styles.stepBar__spinner} />
              ) : (
                <span className={styles.stepBar__number}>{index + 1}</span>
              )}
            </div>
            <div className={styles.stepBar__content}>
              <div className={styles.stepBar__title}>{step.title}</div>
              {step.description && (
                <div className={styles.stepBar__description}>{step.description}</div>
              )}
            </div>
            {index < steps.length - 1 && (
              <div
                className={classNames(styles.stepBar__line, {
                  [styles['stepBar__line--completed']]: index < current,
                })}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

StepBar.propTypes = {
  steps: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string,
      title: PropTypes.node.isRequired,
      description: PropTypes.node,
    })
  ).isRequired,
  current: PropTypes.number.isRequired,
  direction: PropTypes.oneOf(['horizontal', 'vertical']),
  color: PropTypes.oneOf(['blue', 'cyan', 'purple', 'success']),
  className: PropTypes.string,
}

export default StepBar
