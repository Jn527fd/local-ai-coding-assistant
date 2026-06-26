import { forwardRef } from "react";

function cx(...classes) {
  return classes.filter(Boolean).join(" ");
}

export function Button({
  children,
  className = "",
  size = "md",
  type = "button",
  variant = "secondary",
  ...props
}) {
  return (
    <button
      className={cx("ui-button", `ui-button--${variant}`, `ui-button--${size}`, className)}
      type={type}
      {...props}
    >
      {children}
    </button>
  );
}

export function IconButton({ children, className = "", label, type = "button", ...props }) {
  return (
    <button
      aria-label={label}
      className={cx("ui-icon-button", className)}
      type={type}
      {...props}
    >
      {children}
    </button>
  );
}

export function Badge({ children, className = "", dot = false, tone = "neutral", ...props }) {
  return (
    <span className={cx("ui-badge", `ui-badge--${tone}`, className)} {...props}>
      {dot && <span className="ui-badge__dot" aria-hidden="true" />}
      {children}
    </span>
  );
}

export function Tag({ children, className = "", tone = "neutral", ...props }) {
  return (
    <span className={cx("ui-tag", `ui-tag--${tone}`, className)} {...props}>
      {children}
    </span>
  );
}

export function StatusPill({
  children,
  className = "",
  dot = true,
  label,
  status = "neutral",
  ...props
}) {
  return (
    <span className={cx("ui-status-pill", `ui-status-pill--${status}`, className)} {...props}>
      {dot && <span className="ui-status-pill__dot" aria-hidden="true" />}
      <span className="sr-only">{label || status}</span>
      {children}
    </span>
  );
}

export function Surface({ as: Component = "div", children, className = "", level = "base", ...props }) {
  return (
    <Component className={cx("ui-surface", `ui-surface--${level}`, className)} {...props}>
      {children}
    </Component>
  );
}

export const Input = forwardRef(function Input({ className = "", ...props }, ref) {
  return <input className={cx("ui-input", className)} ref={ref} {...props} />;
});

export const Textarea = forwardRef(function Textarea({ className = "", ...props }, ref) {
  return <textarea className={cx("ui-textarea", className)} ref={ref} {...props} />;
});

export function Select({ children, className = "", ...props }) {
  return (
    <select className={cx("ui-select", className)} {...props}>
      {children}
    </select>
  );
}

export function Popover({ children, className = "", ...props }) {
  return (
    <div className={cx("ui-popover", className)} {...props}>
      {children}
    </div>
  );
}

export function Menu({ children, className = "", ...props }) {
  return (
    <div className={cx("ui-menu", className)} role="menu" {...props}>
      {children}
    </div>
  );
}

export function MenuItem({ children, className = "", type = "button", ...props }) {
  return (
    <button className={cx("ui-menu-item", className)} role="menuitem" type={type} {...props}>
      {children}
    </button>
  );
}

export function Tooltip({ children, className = "", content }) {
  return (
    <span className={cx("ui-tooltip", className)}>
      {children}
      <span className="ui-tooltip__content" role="tooltip">
        {content}
      </span>
    </span>
  );
}

export function Card({ as: Component = "section", children, className = "", ...props }) {
  return (
    <Component className={cx("ui-card", className)} {...props}>
      {children}
    </Component>
  );
}

export function Skeleton({ className = "", width, ...props }) {
  return (
    <span
      aria-hidden="true"
      className={cx("ui-skeleton", className)}
      style={width ? { width } : undefined}
      {...props}
    />
  );
}

export function Toast({ children, className = "", tone = "info", ...props }) {
  return (
    <div className={cx("ui-toast", `ui-toast--${tone}`, className)} {...props}>
      {children}
    </div>
  );
}

export function Drawer({
  as: Component = "aside",
  children,
  className = "",
  side = "right",
  ...props
}) {
  return (
    <Component className={cx("ui-drawer", `ui-drawer--${side}`, className)} {...props}>
      {children}
    </Component>
  );
}

export function Modal({
  children,
  className = "",
  overlayClassName = "",
  title,
  ...props
}) {
  return (
    <div className={cx("ui-modal-overlay", overlayClassName)} role="presentation">
      <section
        aria-label={title}
        aria-modal="true"
        className={cx("ui-modal", className)}
        role="dialog"
        {...props}
      >
        {children}
      </section>
    </div>
  );
}

export function CommandItem({ children, className = "", shortcut, ...props }) {
  return (
    <button className={cx("ui-command-item", className)} type="button" {...props}>
      <span>{children}</span>
      {shortcut && <ShortcutKey>{shortcut}</ShortcutKey>}
    </button>
  );
}

export function SourceChip({ children, className = "", type = "button", ...props }) {
  return (
    <button className={cx("ui-source-chip", className)} type={type} {...props}>
      {children}
    </button>
  );
}

export function FileReference({ as: Component = "code", children, className = "", ...props }) {
  return (
    <Component className={cx("ui-file-reference", className)} {...props}>
      {children}
    </Component>
  );
}

export function ShortcutKey({ children, className = "", ...props }) {
  return (
    <kbd className={cx("ui-shortcut-key", className)} {...props}>
      {children}
    </kbd>
  );
}
