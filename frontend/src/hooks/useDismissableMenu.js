import { useEffect, useRef, useState } from 'react'

/** Returns [isOpen, setIsOpen, containerRef] for a menu that closes on
 * outside click or Escape. Attach containerRef to the element wrapping
 * both the trigger button and the menu popup. */
function useDismissableMenu() {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return

    function handleOutsideClick(event) {
      if (!containerRef.current?.contains(event.target)) {
        setIsOpen(false)
      }
    }

    function handleEscape(event) {
      if (event.key === 'Escape') setIsOpen(false)
    }

    document.addEventListener('mousedown', handleOutsideClick)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  return [isOpen, setIsOpen, containerRef]
}

export default useDismissableMenu
