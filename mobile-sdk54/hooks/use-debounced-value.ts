import { useEffect, useState } from 'react';

/**
 * Delays a value until it stops changing for `delayMs`.
 *
 * Typing "chicken" fires seven renders; without this it would fire seven search
 * requests, and the responses can arrive out of order so the list flickers
 * through results for "chick" and "chicke".
 */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}
