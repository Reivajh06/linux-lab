import React, { useEffect, useId, useRef, useState } from 'react';
import { X } from 'lucide-react';

const focusable = 'a[href],button:not(:disabled),input:not(:disabled):not([type=hidden]):not([hidden]),select:not(:disabled),textarea:not(:disabled),iframe,[tabindex]:not([tabindex="-1"])';

/** A modal dialog named by its heading: keeps Tab inside, closes on Escape, and returns focus to the control that opened it.
 *  Initial focus goes to an `autoFocus` child when there is one, otherwise to the dialog itself. */
export default function Modal({ title, onClose, className = '', closeLabel = 'Close dialog', description, children }: { title: React.ReactNode; onClose?: () => void; className?: string; closeLabel?: string; description?: React.ReactNode; children?: React.ReactNode }) {
  const dialog = useRef<HTMLElement>(null);
  const close = useRef(onClose); close.current = onClose;
  const [opener] = useState(() => document.activeElement as HTMLElement | null);
  const id = useId();
  useEffect(() => {
    const node = dialog.current!;
    if (!node.contains(document.activeElement)) node.focus();
    const keydown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && close.current) { e.stopPropagation(); close.current(); return; }
      if (e.key !== 'Tab') return;
      const items = Array.from(node.querySelectorAll<HTMLElement>(focusable));
      if (!items.length) { e.preventDefault(); return; }
      const first = items[0], last = items[items.length - 1];
      if (e.shiftKey && (document.activeElement === first || document.activeElement === node)) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    };
    node.addEventListener('keydown', keydown);
    return () => { node.removeEventListener('keydown', keydown); if (opener?.isConnected) opener.focus(); };
  }, [opener]);
  return <div className="modal-backdrop">
    <section ref={dialog} tabIndex={-1} className={'modal ' + className} role="dialog" aria-modal="true" aria-labelledby={id + '-title'} aria-describedby={description ? id + '-description' : undefined}>
      {onClose && <button className="modal-close" aria-label={closeLabel} onClick={onClose}><X size={20}/></button>}
      <h2 id={id + '-title'}>{title}</h2>
      {description && <p id={id + '-description'}>{description}</p>}
      {children}
    </section>
  </div>;
}
