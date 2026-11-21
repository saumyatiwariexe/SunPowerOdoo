import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import PublicFrame from './PublicFrame'
import AppIcon from '../../app/AppIcon'
export default function ThankYouPage() {
  const reference = useLocation().state?.reference
  return (
    <PublicFrame>
      <section className="paper narrow">
        <div className="confirmation-icon"><AppIcon name={reference ? 'calendar' : 'survey'} size={36} /></div>
        <h1>{reference ? 'Enquiry received.' : 'Your solar enquiry'}</h1>
        {reference && (
          <>
            <p>Keep this reference for your conversation with our solar team.</p>
            <dl className="reference">
              <dt>Enquiry reference</dt>
              <dd>{reference}</dd>
            </dl>
          </>
        )}
        <p>Our agent will discuss your enquiry and invite you to My solar when your customer account is ready.</p>
        <div className="actions">
          <Link className="button primary" to="/customer">Open My solar</Link>
          <Link className="button" to="/">
            Back to home
          </Link>
          <Link className="button" to="/enquiry">
            New enquiry
          </Link>
        </div>
      </section>
    </PublicFrame>
  )
}
