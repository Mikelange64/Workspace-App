import { Component } from 'react'
import './ErrorBoundary.css'

// React has no hooks-based error boundary API — getDerivedStateFromError
// and componentDidCatch only exist on class components. This is the one
// intentional exception to the functional-components-only pattern.
class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Unhandled error in component tree:', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary">
          <p className="error-boundary__title">Something went wrong.</p>
          <p className="error-boundary__detail">{this.state.error.message}</p>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
