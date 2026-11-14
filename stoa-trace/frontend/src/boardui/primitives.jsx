// Adapted from BoardUI's free MIT Button and Divider components.
// Copyright (c) 2026 Mertcan Dundar Esmergul (BoardUI). See LICENSE.
// Tailwind token classes are expressed in local CSS for Trace's existing stack.
import React from 'react';
import './primitives.css';

export function Button({ variant = 'primary', size = 'medium', iconOnly = false, leadingIcon: Leading,
  trailingIcon: Trailing, children, className = '', type = 'button', ref, ...props }) {
  return <button ref={ref} type={type} className={`board-button board-button-${variant} board-button-${size} ${iconOnly ? 'board-button-icon' : ''} ${className}`} {...props}>
    {Leading && <Leading className="board-button-glyph" aria-hidden />}
    {!iconOnly && children != null && <span className="board-button-label">{children}</span>}
    {!iconOnly && Trailing && <Trailing className="board-button-glyph" aria-hidden />}
  </button>;
}

export function Divider({ variant = 'single', align = 'center', children, contentClassName = '', className = '', ref, ...props }) {
  const hasContent = children !== undefined && children !== null;
  if (!hasContent) return <div ref={ref} role="separator" aria-orientation="horizontal" data-variant={variant} className={`board-divider board-divider-${variant} ${className}`} {...props} />;
  return <div ref={ref} data-variant={variant} data-align={align} className={`board-divider board-divider-content board-divider-${variant} ${className}`} {...props}>
    {variant === 'single' && align !== 'start' && <span className="board-divider-line" aria-hidden />}
    <div className={`board-divider-label ${contentClassName}`}>{children}</div>
    {variant === 'single' && align !== 'end' && <span className="board-divider-line" aria-hidden />}
  </div>;
}
